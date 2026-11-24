"""
features.py - reads the git history of one project and turns it into numbers.

Used by collect_data.py (to build the training data) and by predict.py
(to score the files of any project).
"""
import re
import subprocess
from datetime import datetime, timezone

DAY = 86400  # seconds in one day

# A commit counts as a bug fix when its first line contains one of these words...
BUGFIX_WORDS = re.compile(r"\b(fix|fixes|fixed|bug|bugfix|crash|regression)\b", re.IGNORECASE)
# ...unless it is clearly about text, not behaviour ("fix typo", "DOC: fix link").
NOT_A_BUG = re.compile(r"\b(typo|typos|doc|docs|docstring|docstrings|comment)\b", re.IGNORECASE)

# The numbers the model gets for every file.
FEATURES = [
    "loc",                # lines in the file
    "commits",            # how many commits changed the file
    "authors",            # how many different people changed it
    "churn",              # lines added + lines deleted, all commits together
    "bugfixes",           # how many of those commits were bug fixes
    "age_days",           # days since the file was created
    "days_since_change",  # days since the file was last changed
    "recent_commits",     # commits in the last 365 days
    "recent_bugfixes",    # bug-fix commits in the last 365 days
]


def to_timestamp(date):
    """'2025-11-01' -> seconds since 1970 (the form git uses for dates)."""
    return int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def git(repo_dir, *args):
    """Run one git command on a repository and return what it prints."""
    result = subprocess.run(["git", "--git-dir", repo_dir, *args], capture_output=True,
                            encoding="utf-8", errors="replace", check=True)
    return result.stdout


def read_commits(repo_dir):
    """Read every commit: when, who, is it a bug fix, which .py files it changed."""
    log = git(repo_dir, "log", "--no-merges", "--no-renames", "--numstat",
              "--format=@@@%ct|%ae|%s", "--", "*.py")
    commits = []
    for line in log.splitlines():
        if line.startswith("@@@"):                      # first line of a commit
            time, author, subject = line[3:].split("|", 2)
            is_fix = bool(BUGFIX_WORDS.search(subject)) and not NOT_A_BUG.search(subject)
            commits.append({"time": int(time), "author": author, "is_fix": is_fix, "files": []})
        elif line.strip():                              # one changed file: added, deleted, path
            added, deleted, path = line.split("\t")
            if added != "-":                            # "-" means a binary file
                commits[-1]["files"].append((path, int(added) + int(deleted)))
    return commits


# Folders that hold tests, documentation or examples instead of the product itself.
SKIP_FOLDERS = {"test", "tests", "testing", "doc", "docs", "examples", "benchmarks", "asv_bench"}


def is_source_file(path):
    """Keep normal source code; skip tests, documentation and examples."""
    *folders, name = path.lower().split("/")
    if SKIP_FOLDERS & set(folders):
        return False
    return not (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")


def file_sizes(repo_dir, when):
    """Lines in every .py source file, as the project looked at the moment `when`."""
    snapshot = git(repo_dir, "rev-list", "-1", "--first-parent", f"--before={when}", "HEAD").strip()
    sizes = {}
    # "git grep -c ''" counts the lines of each file in that snapshot.
    # Each output line looks like:  <snapshot>:<path>:<number of lines>
    for line in git(repo_dir, "grep", "-c", "", snapshot, "--", "*.py").splitlines():
        _, path, count = line.split(":", 2)
        if is_source_file(path):
            sizes[path] = int(count)
    return sizes


def build_features(commits, sizes, when):
    """One row of numbers per file, using only commits made before `when`."""
    rows = {}
    for path, loc in sizes.items():
        rows[path] = {"file": path, "loc": loc, "commits": 0, "authors": set(), "churn": 0,
                      "bugfixes": 0, "first": when, "last": 0,
                      "recent_commits": 0, "recent_bugfixes": 0}

    for commit in commits:
        if commit["time"] >= when:
            continue                                    # the future is not allowed
        recent = commit["time"] >= when - 365 * DAY
        for path, changed_lines in commit["files"]:
            row = rows.get(path)
            if row is None:
                continue                                # file did not exist at `when`
            row["commits"] += 1
            row["authors"].add(commit["author"])
            row["churn"] += changed_lines
            row["bugfixes"] += commit["is_fix"]
            row["first"] = min(row["first"], commit["time"])
            row["last"] = max(row["last"], commit["time"])
            row["recent_commits"] += recent
            row["recent_bugfixes"] += recent and commit["is_fix"]

    result = []
    for row in rows.values():
        if row["commits"] == 0:
            continue                                    # no history found for this file
        row["authors"] = len(row["authors"])
        row["age_days"] = (when - row.pop("first")) // DAY
        row["days_since_change"] = (when - row.pop("last")) // DAY
        result.append(row)
    return result


def files_fixed_between(commits, start, end):
    """Set of files touched by at least one bug-fix commit between two moments."""
    fixed = set()
    for commit in commits:
        if commit["is_fix"] and start <= commit["time"] < end:
            fixed.update(path for path, _ in commit["files"])
    return fixed
