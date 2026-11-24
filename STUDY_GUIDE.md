# Study guide: rebuild the project yourself and understand every line

This guide is for one working day without any help. You will do the data
collection by hand, type the four scripts again in an empty folder, check every
step against a known answer, and then go through the model, the results and the
questions you may be asked.

Every output shown here is real. It comes from the run of 24 November 2026.

## Plan for the day (about 6 hours)

| Part | What you do | Time |
|---|---|---|
| 0 | Set up the laptop | 20 min |
| 1 | Read the whole project on one page | 15 min |
| 2 | Collect the data by hand for one project, with git commands only | 60 min |
| 3 | Type the four scripts again, one function at a time, with a check after each | 2 h 15 min |
| 4 | Understand the model and the measures, with one calculation by hand | 45 min |
| 5 | Run the "what if" experiments | 30 min |
| 6 | Questions and answers | 45 min |
| 7 | The demo and the one-minute summary | 10 min |

If you run out of time, skip typing `predict.py` in Part 3 and only read it.
Do not skip Parts 2, 4 and 6.

---

## Part 0: Set up the laptop

You need **git** and **Python 3.9 or newer**.

**On Windows, use "Git Bash"** (it is installed together with Git for Windows).
All commands in this guide are written for it and for Linux/WSL. In Git Bash:

- write `python` where this guide says `python3`;
- activate the environment with `source .venv/Scripts/activate` instead of `source .venv/bin/activate`.

```
git clone <the address of your GitHub repository>
cd <the folder it created>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Check that everything works. This uses the dataset that is already in the repository:

```
python3 train_model.py
```

It should print the same tables as `expected_output.txt`, in about 20 seconds.

Now create the empty folder where you will rebuild everything. It is ignored by git.

```
mkdir rebuild
cd rebuild
mkdir repos data
```

**For the rest of the day you work inside `rebuild/`.** The original files are
one level up (`../features.py` and so on) if you want to compare.

---

## Part 1: The whole project on one page

**The question.** For every source file of a project: will this file need a bug
fix in the next 12 months?

**Why anyone wants that.** A team cannot review and test everything. A list of
the riskiest files tells them where to look first.

**The pipeline.**

```
GitHub address
    |  git clone --bare                       (collect_data.py)
    v
git history of the project
    |  git log --numstat                      (features.py: read_commits)
    v
list of commits: date, author, is it a bug fix, files changed
    |  count per file, only commits before 1 Nov 2025   (features.py: build_features)
    v
one row per file with 9 numbers  +  label "buggy" from the year AFTER 1 Nov 2025
    |  saved as data/dataset.csv              (collect_data.py)
    v
numbers replaced by positions inside the project (0 to 1)   (train_model.py)
    |  train on 11 projects, test on the 12th, repeat 12 times
    v
tables with precision, recall, F1, AUC, top 20%  +  model.joblib
    |                                         (predict.py)
    v
for any project: every file with a risk between 0 and 1, sorted
```

**The four files.**

| File | Lines | Job |
|---|---|---|
| `features.py` | about 130 | talks to git and computes the 9 numbers |
| `collect_data.py` | about 75 | runs `features.py` on 12 projects, adds the label, saves the dataset |
| `train_model.py` | about 150 | preprocessing, 3 models, evaluation, saves the best model |
| `predict.py` | about 55 | applies the saved model to any project |

**The key idea that makes it honest.** Pick a date in the past (1 November 2025).
The model may only see what happened before that date. What happened in the
year after is the answer. So the test is the same as real life: predict
today, check in a year.

---

## Part 2: Collect the data by hand for one project

You will do with plain git commands what `features.py` does in Python, for the
project Poetry (a small download, about 27 MB). At the end you will have
computed one row of the dataset yourself.

You are in the `rebuild` folder.

### 2.1 Download the history

```
git clone --bare --single-branch --no-tags https://github.com/python-poetry/poetry repos/python-poetry__poetry.git
R=repos/python-poetry__poetry.git
```

The second line stores the path in a variable called `R`, so the commands below
are shorter. **If you open a new terminal, type that line again.**

| Piece | Meaning |
|---|---|
| `git clone <address> <folder>` | download a repository into a folder |
| `--bare` | only the history database, no folder with the source files. We never open the files in an editor, we only ask git questions. |
| `--single-branch` | only the main line of development, not every side branch |
| `--no-tags` | skip the version markers (v1.0, v1.1, ...), we do not need them |

```
du -sh $R
git --git-dir $R rev-list --count HEAD
```

Expected: about `27M`, and `3928` commits or a few more (the project gets new
commits every day). `--git-dir $R` tells git which repository to use. `HEAD` is
the newest commit of the main branch.

### 2.2 Look at commits

```
git --git-dir $R log -3 --before=1761955200 --format='%h | %cs | %s'
```

Expected:

```
477b54b2 | 2025-10-31 | tests: make test forward compatible with poetry-core#893 (#10605)
6f31f56c | 2025-10-26 | fix error of removing packages if nested groups (include-group) are used in pep735 style (#10587)
b7792968 | 2025-10-25 | tests: check that config command is in sync with config class (#10597)
```

| Piece | Meaning |
|---|---|
| `log -3` | print 3 commits, newest first |
| `--before=1761955200` | only commits before this moment. Git counts time in seconds since 1 January 1970. `1761955200` is 1 November 2025, 00:00 UTC. This is our cutoff date. |
| `--format='...'` | what to print for each commit |
| `%h` | short hash, the id of the commit |
| `%cs` | commit date as year-month-day |
| `%s` | subject: the first line of the commit message |
| `%ct` | commit time in seconds since 1970 (used by the code) |
| `%ae` | e-mail of the author (used by the code to count different people) |

Check the number yourself:

```
python3 -c "from datetime import datetime, timezone; print(datetime.fromtimestamp(1761955200, timezone.utc))"
```

Expected: `2025-11-01 00:00:00+00:00`

### 2.3 Which files did a commit change?

```
git --git-dir $R log -1 --before=1761955200 --no-merges --numstat --format='@@@%ct|%an|%s' -- '*.py'
```

Expected (with the real name of the author in the middle):

```
@@@1761887708|AUTHOR NAME|tests: make test forward compatible with poetry-core#893 (#10605)

4	4	tests/repositories/test_repository.py
```

| Piece | Meaning |
|---|---|
| `--numstat` | after each commit, one line per changed file: lines added, lines deleted, path |
| `--no-merges` | skip merge commits. A merge only joins two branches; the real changes are in the normal commits. |
| `-- '*.py'` | only commits that touch Python files, and only show those files |
| `@@@` | a marker we chose ourselves, so the code can recognise the first line of a commit |

This is **exactly the text that `read_commits()` reads**: one line starting with
`@@@`, then one line per file. This commit added 4 and deleted 4 lines in one
test file.

### 2.4 Which commits are bug fixes?

Rule: the subject contains one of the words *fix, fixes, fixed, bug, bugfix,
crash, regression*.

```
git --git-dir $R log --no-merges --before=1761955200 --format=%s -- '*.py' | grep -iE '\b(fix|fixes|fixed|bug|bugfix|crash|regression)\b' | head -4
```

Expected:

```
fix error of removing packages if nested groups (include-group) are used in pep735 style (#10587)
fix: allow to set `data-dir` and `python-installation-dir` (#10595)
fix `poetry self show` (#10560)
tests: fix deprecation warning (#10545)
```

`|` sends the output of one command into the next. `grep -iE '...'` keeps only
the lines that match the pattern; `-i` ignores upper and lower case; `\b` means
"word boundary", so `fix` matches but `prefix` does not. `head -4` shows the
first 4.

Count them (replace `| head -4` by `| wc -l`): **753** of **2345** commits
before the cutoff.

Look at the fourth line: "tests: fix deprecation warning" is not really a bug
in the product. The keyword rule makes mistakes like this. That is the first
limitation in the report. (When such a commit changes only test files it does no harm,
because test files are not in the dataset.)

### 2.5 Which files existed on the cutoff date, and how long were they?

```
git --git-dir $R rev-list -1 --first-parent --before=1761955200 HEAD
```

Expected: `477b54b26167933f636d54142d2e5cc91284ee8d`

This is the last commit on the main line before the cutoff: the state of the
project on 1 November 2025. `--first-parent` means "stay on the main line, do
not wander into a side branch that was merged later".

```
git --git-dir $R grep -c '' 477b54b26167933f636d54142d2e5cc91284ee8d -- '*.py' | head -3
```

Expected:

```
477b54b26167933f636d54142d2e5cc91284ee8d:src/poetry/__main__.py:9
477b54b26167933f636d54142d2e5cc91284ee8d:src/poetry/__version__.py:6
477b54b26167933f636d54142d2e5cc91284ee8d:src/poetry/config/config.py:435
```

`git grep -c ''` counts, for every file in that snapshot, the lines that match
"nothing", which is every line. So the last number is the length of the file.
With `| wc -l` instead of `| head -3` you get **344** Python files. After
removing tests and documentation, **171** remain.

### 2.6 Compute the 9 numbers for one file by hand

The file: `src/poetry/installation/executor.py`

```
F=src/poetry/installation/executor.py
```

**loc** (lines on the cutoff date):

```
git --git-dir $R grep -c '' 477b54b26167933f636d54142d2e5cc91284ee8d -- $F
```
Expected: ends with `:942`

**commits** (how many commits changed it before the cutoff):

```
git --git-dir $R log --no-merges --no-renames --before=1761955200 --format=%H -- $F | wc -l
```
Expected: `91`

**authors** (different e-mail addresses):

```
git --git-dir $R log --no-merges --no-renames --before=1761955200 --format=%ae -- $F | sort -u | wc -l
```
Expected: `35`. `sort -u` sorts and removes duplicates.

**churn** (lines added + deleted, over all commits):

```
git --git-dir $R log --no-merges --no-renames --before=1761955200 --numstat --format= -- $F | awk '{s+=$1+$2} END {print s}'
```
Expected: `2620`. `awk` adds column 1 and column 2 of every line.

**bugfixes** (commits whose subject matches the bug-fix words):

```
git --git-dir $R log --no-merges --no-renames --before=1761955200 --format=%s -- $F | grep -ciE '\b(fix|fixes|fixed|bug|bugfix|crash|regression)\b'
```
Expected: `17`. `-c` counts the matching lines.

**age_days** and **days_since_change** (oldest and newest commit time):

```
git --git-dir $R log --no-merges --no-renames --before=1761955200 --format=%ct -- $F | sort -n | sed -n '1p;$p'
```
Expected: `1636937508` (oldest) and `1749270682` (newest).

```
echo $(( (1761955200 - 1636937508) / 86400 ))
echo $(( (1761955200 - 1749270682) / 86400 ))
```
Expected: `1446` and `146`. 86400 is the number of seconds in a day.

**recent_commits** and **recent_bugfixes** (the last 365 days before the cutoff;
1761955200 minus 365 days is 1730419200):

```
git --git-dir $R log --no-merges --no-renames --since=1730419200 --before=1761955200 --format=%s -- $F | wc -l
git --git-dir $R log --no-merges --no-renames --since=1730419200 --before=1761955200 --format=%s -- $F | grep -ciE '\b(fix|fixes|fixed|bug|bugfix|crash|regression)\b'
```
Expected: `6` and `2`.

**Now compare with the dataset:**

```
grep 'installation/executor.py' ../data/dataset.csv
```

Expected:

```
python-poetry/poetry,src/poetry/installation/executor.py,942,91,35,2620,17,1446,146,6,2,1
```

The columns are `repo, file, loc, commits, authors, churn, bugfixes, age_days,
days_since_change, recent_commits, recent_bugfixes, buggy`. Your nine numbers
are the same. You have just computed one row of the dataset by hand.

### 2.7 The label by hand

The last column, `buggy`, is the only thing that comes from **after** the
cutoff: was the file changed by a bug-fix commit between 1 November 2025
(1761955200) and 1 November 2026 (1793491200)?

```
git --git-dir $R log --no-merges --no-renames --since=1761955200 --before=1793491200 --format='%cs %s' -- $F | grep -iE '\b(fix|fixes|fixed|bug|bugfix|crash|regression)\b'
```

Expected:

```
2026-03-31 fix: wrap string config setting values in list before iterating (#10804)
2026-02-21 Fix _remove to catch EnvCommandError instead of CalledProcessError (#10740)
```

Two bug fixes, so `buggy = 1`.

Do the same for another file (`F=src/poetry/factory.py`): no line is printed,
so `buggy = 0`. In the dataset its row ends with `,0`.

**What you should be able to say now:** "Each row is one file. Nine numbers
come from the history before 1 November 2025. The label says whether a bug-fix
commit touched the file in the year after."

---

## Part 3: Type the four scripts again

Rules for this part:

- Type the code, do not copy and paste. Typing is slower, but you read every line.
- After each function, read the explanation, then run the check. Go on only when the check gives the expected output.
- Python cares about spaces at the start of a line. Use 4 spaces per level.

### 3.1 `features.py`

Create the file `features.py` in the `rebuild` folder and start with this:

```python
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
```

- `re` is for patterns in text, `subprocess` is for running other programs (git), `datetime` is for dates.
- `re.compile(r"\b(fix|...)\b", re.IGNORECASE)` prepares a pattern. `\b` is a word boundary, `|` means "or", `re.IGNORECASE` makes `Fix` and `fix` the same. It is the same pattern you used with `grep` in Part 2.
- `NOT_A_BUG` removes commits like "fix typo" or "DOC: fix link".
- `FEATURES` is the list of column names. The other scripts import it, so the names exist in one place only.

```python
def to_timestamp(date):
    """'2025-11-01' -> seconds since 1970 (the form git uses for dates)."""
    return int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
```

- `strptime` reads the text `'2025-11-01'` as a date.
- `.replace(tzinfo=timezone.utc)` says: this is midnight in UTC, not in the time zone of the laptop. Without it you would get a different number in Romania than on a server.
- `.timestamp()` gives seconds since 1970, `int()` removes the decimals.

Check:
```
python3 -c "from features import to_timestamp; print(to_timestamp('2025-11-01'))"
```
Expected: `1761955200`

```python
def git(repo_dir, *args):
    """Run one git command on a repository and return what it prints."""
    result = subprocess.run(["git", "--git-dir", repo_dir, *args], capture_output=True,
                            encoding="utf-8", errors="replace", check=True)
    return result.stdout
```

- `*args` means "any number of extra arguments". `git(repo, "log", "-3")` runs `git --git-dir repo log -3`.
- `subprocess.run([...])` runs the command, the same as typing it in the terminal.
- `capture_output=True` catches what the command prints instead of showing it.
- `encoding="utf-8", errors="replace"` turns the bytes into text; a strange character in an old commit message becomes `?` instead of crashing the program.
- `check=True` stops the program with an error if git fails.
- `result.stdout` is the printed text.

Check:
```
python3 -c "from features import git; print(git('repos/python-poetry__poetry.git', 'rev-list', '--count', 'HEAD'))"
```
Expected: `3928` or a few more, the same number as in 2.1.

```python
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
```

This is the command from 2.3, for all commits at once, and then the text is read line by line.

- `log.splitlines()` cuts the text into lines.
- A line that starts with `@@@` opens a new commit. `line[3:]` drops the three `@`. `.split("|", 2)` cuts at the first two `|` only, so a `|` inside the commit message does no harm.
- `is_fix` is `True` when the subject has a bug-fix word and no "not a bug" word.
- Each commit becomes a dictionary: `{"time": ..., "author": ..., "is_fix": ..., "files": []}`.
- Any other non-empty line is a changed file: `added<TAB>deleted<TAB>path`. `commits[-1]` is the commit opened last, and the file is added to its list as a pair `(path, added + deleted)`.
- For binary files git prints `-` instead of numbers; those are skipped.

Check:
```
python3 -c "from features import read_commits; c = read_commits('repos/python-poetry__poetry.git'); print(len(c)); print(c[-1]['time'], c[-1]['is_fix'], c[-1]['files'][:3])"
```
Expected (`2541` or a few more; the second line is the oldest commit and does not change):
```
2541
1519163262 False [('poetry/__init__.py', 2), ('poetry/semver/__init__.py', 62), ('poetry/semver/comparison.py', 88)]
```

Why 2541 and not 3928? `--no-merges` and `-- '*.py'` leave out merge commits and commits that touch no Python file.

```python
# Folders that hold tests, documentation or examples instead of the product itself.
SKIP_FOLDERS = {"test", "tests", "testing", "doc", "docs", "examples", "benchmarks", "asv_bench"}


def is_source_file(path):
    """Keep normal source code; skip tests, documentation and examples."""
    *folders, name = path.lower().split("/")
    if SKIP_FOLDERS & set(folders):
        return False
    return not (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")
```

- `path.lower().split("/")` cuts `src/poetry/factory.py` into `['src', 'poetry', 'factory.py']`.
- `*folders, name = ...` puts the last piece in `name` and all the others in `folders`.
- `SKIP_FOLDERS & set(folders)` is the overlap of two sets. If any folder of the path is in the skip list, the overlap is not empty and the file is skipped.
- The last line also skips files named like `test_x.py`, `x_test.py` and `conftest.py`.
- Why whole folder names and not "contains the word test"? Because pytest keeps its real source in a folder called `_pytest`, and that would be thrown away.

Check:
```
python3 -c "from features import is_source_file as f; print(f('src/poetry/factory.py'), f('tests/test_factory.py'), f('docs/conf.py'), f('src/_pytest/main.py'))"
```
Expected: `True False False True`

```python
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
```

These are the two commands from 2.5.

- `f"--before={when}"` puts the value of `when` into the text (an "f-string").
- `.strip()` removes the line break at the end of the hash.
- `line.split(":", 2)` cuts `hash:path:count` into three pieces. `_` is a name for "I do not need this one".
- The result is a dictionary `{path: number of lines}`.

Check:
```
python3 -c "from features import *; s = file_sizes('repos/python-poetry__poetry.git', to_timestamp('2025-11-01')); print(len(s), s['src/poetry/installation/executor.py'])"
```
Expected: `171 942`

```python
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
```

This is the heart of the project. It does for every file what you did by hand in 2.6.

- First loop: one empty row per file that existed on the date. `authors` starts as an empty `set()` (a set keeps each value once, so the same person is not counted twice). `first` starts at `when` and `last` at 0, so the first real commit replaces them.
- Second loop: go through all commits.
  - `if commit["time"] >= when: continue` skips every commit made on or after the date. **This one line is what prevents the model from seeing the future.**
  - `recent` is `True` if the commit is at most 365 days older than the date.
  - `rows.get(path)` returns the row of the file, or `None` if the file did not exist on the date (deleted or renamed files, and tests).
  - Then the counters go up. `row["bugfixes"] += commit["is_fix"]` works because in Python `True` counts as 1 and `False` as 0.
  - `min` and `max` keep the oldest and the newest commit time.
- Third loop: finish each row. A file with 0 commits is dropped. The set of authors becomes a number with `len`. The two times become days: `//` is division that rounds down. `row.pop("first")` takes the value out of the row and removes the key, so the helper columns disappear.

```python
def files_fixed_between(commits, start, end):
    """Set of files touched by at least one bug-fix commit between two moments."""
    fixed = set()
    for commit in commits:
        if commit["is_fix"] and start <= commit["time"] < end:
            fixed.update(path for path, _ in commit["files"])
    return fixed
```

- Used for the label. It collects every file touched by a bug-fix commit in a time window.
- `fixed.update(...)` adds all the paths of that commit to the set.

Check for both functions. Create a file `try_it.py`:

```python
from features import *

R = "repos/python-poetry__poetry.git"
when = to_timestamp("2025-11-01")
commits = read_commits(R)
rows = build_features(commits, file_sizes(R, when), when)
print(len(rows))
print([r for r in rows if r["file"] == "src/poetry/installation/executor.py"][0])
fixed = files_fixed_between(commits, when, to_timestamp("2026-11-01"))
print("src/poetry/installation/executor.py" in fixed, "src/poetry/factory.py" in fixed)
print(sum(r["file"] in fixed for r in rows))
```

```
python3 try_it.py
```

Expected:

```
171
{'file': 'src/poetry/installation/executor.py', 'loc': 942, 'commits': 91, 'authors': 35, 'churn': 2620, 'bugfixes': 17, 'recent_commits': 6, 'recent_bugfixes': 2, 'age_days': 1446, 'days_since_change': 146}
True False
53
```

The second line has the same numbers you computed by hand in 2.6. The last
line says 53 of the 171 Poetry files are buggy.

### 3.2 `collect_data.py`

```python
"""
collect_data.py - step 1: download the projects and build the dataset.

For every project:
  1. clone it from GitHub (history only, no working folder)
  2. read all commits with "git log"
  3. describe every .py file with numbers, using ONLY history before CUTOFF
  4. label the file 1 (buggy) if a bug-fix commit changed it between CUTOFF and END

Result: data/dataset.csv, one row per file.
Run:    python3 collect_data.py
"""
import os
import subprocess

import pandas as pd

from features import (FEATURES, build_features, file_sizes, files_fixed_between,
                      read_commits, to_timestamp)

REPOS = [
    "scikit-learn/scikit-learn",
    "pandas-dev/pandas",
    "pytest-dev/pytest",
    "scrapy/scrapy",
    "celery/celery",
    "sqlalchemy/sqlalchemy",
    "python/mypy",
    "sphinx-doc/sphinx",
    "networkx/networkx",
    "python-poetry/poetry",
    "pydantic/pydantic",
    "pydata/xarray",
]

CUTOFF = "2025-11-01"   # the model may only look at history before this date
END = "2026-11-01"      # bug fixes between CUTOFF and END decide the label


def main():
    os.makedirs("repos", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    cutoff, end = to_timestamp(CUTOFF), to_timestamp(END)
    all_rows, total_commits = [], 0

    for repo in REPOS:
        repo_dir = "repos/" + repo.replace("/", "__") + ".git"
        if not os.path.exists(repo_dir):
            print("cloning", repo, "...")
            subprocess.run(["git", "clone", "--quiet", "--bare", "--single-branch", "--no-tags",
                            "https://github.com/" + repo, repo_dir], check=True)

        commits = read_commits(repo_dir)
        sizes = file_sizes(repo_dir, cutoff)
        rows = build_features(commits, sizes, cutoff)
        fixed_later = files_fixed_between(commits, cutoff, end)

        for row in rows:
            row["repo"] = repo
            row["buggy"] = int(row["file"] in fixed_later)
        all_rows += rows

        total_commits += len(commits)
        buggy = sum(row["buggy"] for row in rows)
        print(f"{repo:28s} {len(commits):6d} commits  {len(rows):5d} files  {buggy:4d} buggy")

    data = pd.DataFrame(all_rows)[["repo", "file"] + FEATURES + ["buggy"]]
    data.to_csv("data/dataset.csv", index=False)
    print(f"\nRead {total_commits} commits from {len(REPOS)} projects.")
    print(f"Saved data/dataset.csv: {len(data)} files, {data.buggy.mean():.1%} buggy")


if __name__ == "__main__":
    main()
```

- `REPOS` is the list of projects. `CUTOFF` and `END` are the two dates.
- `os.makedirs(..., exist_ok=True)` creates a folder and does not complain if it exists.
- `repo.replace("/", "__")` turns `python-poetry/poetry` into `python-poetry__poetry`, because a folder name cannot contain `/`.
- `if not os.path.exists(repo_dir)`: a project that is already downloaded is not downloaded again. That is why your Poetry clone from Part 2 is reused.
- Then four calls to `features.py`: read the commits, get the file sizes, build the rows, find the files fixed later.
- `row["buggy"] = int(row["file"] in fixed_later)` is the label: 1 if the file is in the set, otherwise 0.
- `pd.DataFrame(all_rows)` turns the list of dictionaries into a table; `[["repo", "file"] + FEATURES + ["buggy"]]` puts the columns in a fixed order; `to_csv` saves it.
- `if __name__ == "__main__": main()` means: run `main()` when the file is started as a program, but not when another file imports it.

**Quick check with one project.** Put a `#` in front of every line of `REPOS`
except `"python-poetry/poetry",` and run:

```
python3 collect_data.py
```

Expected (the number of commits can be a few higher):

```
python-poetry/poetry           2541 commits    171 files    53 buggy

Read 2541 commits from 1 projects.
Saved data/dataset.csv: 171 files, 31.0% buggy
```

**Full run.** Remove the `#` signs again and run the same command. It downloads
the other 11 projects (about 1.3 GB, a few minutes) and should end with:

```
Read 129357 commits from 12 projects.
Saved data/dataset.csv: 2492 files, 30.5% buggy
```

Then compare your dataset with the original:

```
python3 -c "import pandas as pd; a = pd.read_csv('data/dataset.csv'); b = pd.read_csv('../data/dataset.csv'); print(a.equals(b))"
```

Expected: `True`. If it prints `False`, a few labels may have changed because
of commits that were merged after 24 November 2026; a difference of a handful
of rows is normal.

**If the download is not possible at work**, copy the original and continue:
`cp ../data/dataset.csv data/dataset.csv`

### 3.3 `train_model.py`

```python
"""
train_model.py - step 2: train the models and measure how good they are.

Test method ("leave one project out"): take one project away, train on the
other projects, predict the files of the project that was taken away, compare
with what really happened. Repeat for every project. So a model is always
tested on a project it has never seen.

Run:    python3 train_model.py
Result: tables on screen and in results/, the final model in model.joblib
"""
import os

import joblib
import matplotlib
matplotlib.use("Agg")                     # draw to a file, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from features import FEATURES

FINAL_MODEL = "Logistic regression"       # the winner of the comparison below
EXAMPLE_PROJECT = "scrapy/scrapy"         # its top-10 list is saved as a real example
```

- `matplotlib.use("Agg")` lets the chart be saved to a file on a computer without a screen.
- From scikit-learn come the three models, the four measures, and two helpers (`make_pipeline`, `StandardScaler`).
- `FINAL_MODEL` is the name of the model that is saved at the end. It was chosen after looking at the comparison table.

```python
def make_models():
    """The three models that are compared. class_weight='balanced' makes a model
    pay equal attention to buggy and clean files, although buggy ones are fewer."""
    return {
        "Logistic regression": make_pipeline(
            StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)),
        "Decision tree": DecisionTreeClassifier(
            max_depth=5, class_weight="balanced", random_state=42),
        "Random forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=42),
    }
```

- A function that returns three fresh, untrained models. It is called again for every test project, so nothing learned in one round leaks into the next.
- `make_pipeline(StandardScaler(), LogisticRegression(...))` glues two steps together: first put every column on the same scale (mean 0, spread 1), then the logistic regression. Calling `.fit` or `.predict_proba` on the pipeline runs both steps.
- `class_weight="balanced"`: only 30% of the files are buggy, so mistakes on buggy files get a higher weight. Otherwise a model can look good by saying "clean" most of the time.
- `max_iter=1000`: logistic regression is trained in small steps; this allows up to 1000 steps so that it surely finishes.
- `max_depth=5`: the tree may ask at most 5 questions in a row. A deeper tree memorises the training files.
- `n_estimators=300`: the forest has 300 trees. `min_samples_leaf=5`: every final group of a tree must hold at least 5 files, which also limits memorising.
- `random_state=42`: trees use random choices; a fixed number makes every run give the same result.

Check:
```
python3 -c "from train_model import make_models; print(list(make_models()))"
```
Expected: `['Logistic regression', 'Decision tree', 'Random forest']`

```python
def found_in_top20(truth, risk):
    """If we inspect only the 20% of files with the highest risk,
    what share of all buggy files do we find?"""
    truth, risk = np.asarray(truth), np.asarray(risk)
    top = np.argsort(-risk, kind="stable")[: round(0.2 * len(risk))]
    return truth[top].sum() / truth.sum()
```

- `np.argsort(-risk)` gives the positions of the files from the highest risk to the lowest (the minus turns the order around).
- `[: round(0.2 * len(risk))]` keeps the first 20% of them.
- `truth[top].sum()` counts the buggy files among those; dividing by `truth.sum()` gives the share of all buggy files.

Check with a toy example: 10 files, 3 are buggy (positions 1, 3 and 10), and the risks happen to be sorted from high to low. The top 20% are the first 2 files, and they contain 1 of the 3 buggy files.
```
python3 -c "from train_model import found_in_top20; print(found_in_top20([1,0,1,0,0,0,0,0,0,1], [9,8,7,6,5,4,3,2,1,0]))"
```
Expected: `0.3333333333333333`

```python
def evaluate(data):
    """Leave one project out. Returns one row of scores per method and project."""
    rows = []
    for test_project in sorted(data.repo.unique()):
        train = data[data.repo != test_project]
        test = data[data.repo == test_project]

        # The three machine learning models
        for name, model in make_models().items():
            model.fit(train[FEATURES], train.buggy)
            risk = model.predict_proba(test[FEATURES])[:, 1]      # between 0 and 1
            flagged = risk >= 0.5                                 # the model says "buggy"
            rows.append({"method": name, "project": test_project,
                         "precision": precision_score(test.buggy, flagged, zero_division=0),
                         "recall": recall_score(test.buggy, flagged),
                         "f1": f1_score(test.buggy, flagged),
                         "auc": roc_auc_score(test.buggy, risk),
                         "top20": found_in_top20(test.buggy, risk)})

        # Two simple rules without machine learning, to compare against
        for name, column in [("Rule: largest files", "loc"), ("Rule: most changed files", "commits")]:
            rows.append({"method": name, "project": test_project,
                         "auc": roc_auc_score(test.buggy, test[column]),
                         "top20": found_in_top20(test.buggy, test[column])})
    return pd.DataFrame(rows)
```

This is "leave one project out".

- The outer loop takes each project in turn as the test project.
- `train = data[data.repo != test_project]` is every row of the other 11 projects; `test` is the rows of this one.
- `model.fit(train[FEATURES], train.buggy)`: learn from the 9 columns and the label.
- `model.predict_proba(test[FEATURES])` gives two columns per file: the chance of "clean" and the chance of "buggy". `[:, 1]` takes the second column. That is the risk.
- `flagged = risk >= 0.5`: the yes/no answer of the model.
- Precision, recall and F1 compare `flagged` with the truth. AUC and top20 use the risk itself.
- The second inner loop does the same for the two simple rules. A rule has no yes/no answer, only an order, so it gets only AUC and top20. The "risk" of the rule is simply the column `loc` or `commits`.
- The result is one table with a row per method and project: 5 methods times 12 projects = 60 rows.

Check (uses the raw numbers, without preprocessing):
```
python3 -c "import pandas as pd; from train_model import evaluate; print(evaluate(pd.read_csv('data/dataset.csv')).head(5).round(3).to_string())"
```
Expected:
```
                     method        project  precision  recall     f1    auc  top20
0       Logistic regression  celery/celery      0.913   0.296  0.447  0.765  0.437
1             Decision tree  celery/celery      0.698   0.423  0.526  0.718  0.352
2             Random forest  celery/celery      0.957   0.310  0.468  0.824  0.437
3       Rule: largest files  celery/celery        NaN     NaN    NaN  0.823  0.394
4  Rule: most changed files  celery/celery        NaN     NaN    NaN  0.727  0.366
```

Now `main()`, in five pieces. Type them one after the other; they are all inside `def main():`.

```python
def main():
    os.makedirs("results", exist_ok=True)
    raw = pd.read_csv("data/dataset.csv")

    # ---- the dataset ---------------------------------------------------------
    summary = raw.groupby("repo").agg(files=("buggy", "size"), buggy=("buggy", "sum"))
    summary.loc["TOTAL"] = summary.sum()
    summary["buggy_share"] = summary.buggy / summary.files
    print("DATASET\n" + summary.round(3).to_string() + "\n")
    summary.round(3).to_csv("results/dataset_summary.csv")
```

- `groupby("repo").agg(...)`: per project, count the rows (`size`) and add up the `buggy` column (`sum`).
- A `TOTAL` row is added, then the share is computed.

```python
    # ---- preprocessing ---------------------------------------------------------
    # Replace every number by its position inside its own project, from 0 to 1
    # (1.0 = the highest value in that project). A 500-line file is big in one
    # project and ordinary in another; the position is comparable between projects.
    data = raw.copy()
    data[FEATURES] = raw.groupby("repo")[FEATURES].rank(pct=True)
```

**The only preprocessing step.** `raw.groupby("repo")[FEATURES].rank(pct=True)`:
inside each project, every column is replaced by the rank of the value, as a
share between 0 and 1. The largest file of a project gets `loc = 1.0`, the
median file about 0.5. The label column is not touched.

```python
    # ---- evaluation ------------------------------------------------------------
    columns = ["precision", "recall", "f1", "auc", "top20"]
    order = list(make_models()) + ["Rule: largest files", "Rule: most changed files"]

    before = evaluate(raw).groupby("method")[columns].mean().loc[order]
    print("AVERAGE OVER THE PROJECTS - raw numbers (no preprocessing)")
    print(before.round(3).to_string(na_rep="-") + "\n")

    scores = evaluate(data)
    after = scores.groupby("method")[columns].mean().loc[order]
    print("AVERAGE OVER THE PROJECTS - with preprocessing (used from here on)")
    print(after.round(3).to_string(na_rep="-") + "\n")

    per_project = scores[scores.method == FINAL_MODEL].set_index("project")[columns]
    print(FINAL_MODEL.upper() + ", project by project")
    print(per_project.round(3).to_string() + "\n")

    before.round(3).to_csv("results/methods_raw.csv")
    after.round(3).to_csv("results/methods.csv")
    per_project.round(3).to_csv("results/final_model_per_project.csv")
```

- `evaluate(raw)` runs everything on the raw numbers, `evaluate(data)` on the preprocessed ones. Printing both shows what the preprocessing is worth.
- `.groupby("method")[columns].mean()` averages the 12 projects for each method. `.loc[order]` puts the rows in a fixed order.
- `per_project` is the detail table for the final model.
- `na_rep="-"` prints a dash where a rule has no precision.

```python
    # ---- a real example: what the model said about one unseen project -------------
    model = make_models()[FINAL_MODEL].fit(data[data.repo != EXAMPLE_PROJECT][FEATURES],
                                           data[data.repo != EXAMPLE_PROJECT].buggy)
    example = raw[raw.repo == EXAMPLE_PROJECT].copy()
    example["risk"] = model.predict_proba(data.loc[example.index, FEATURES])[:, 1].round(2)
    example = example.sort_values("risk", ascending=False).head(10)
    example = example[["file", "risk", "loc", "commits", "recent_bugfixes", "buggy"]]
    print(f"EXAMPLE: the 10 riskiest files of {EXAMPLE_PROJECT} (buggy = what really happened)")
    print(example.to_string(index=False) + "\n")
    example.to_csv("results/example_top10.csv", index=False)
```

- Trains the final model type on all projects except Scrapy and predicts Scrapy.
- `raw[...]` is used for showing readable numbers (727 lines), `data.loc[example.index, FEATURES]` gives the model the preprocessed numbers of the same rows.
- Sorted by risk, the first 10 are saved. The column `buggy` shows what really happened.

```python
    # ---- final model, trained on all projects ----------------------------------
    final = make_models()[FINAL_MODEL].fit(data[FEATURES], data.buggy)
    joblib.dump(final, "model.joblib")

    # Weights of the logistic regression: above 0 = raises the risk, below 0 = lowers it
    weights = pd.Series(final[-1].coef_[0], index=FEATURES).sort_values()
    print("WEIGHT OF EACH FEATURE IN THE FINAL MODEL")
    print(weights.sort_values(ascending=False).round(2).to_string())
    weights.round(3).to_csv("results/feature_weights.csv", header=["weight"])
    weights.plot.barh(figsize=(6, 3.5), color=["#b5483a" if w < 0 else "#3b6ea5" for w in weights])
    plt.axvline(0, color="black", linewidth=0.8)
    plt.xlabel("weight in the model (right = more risk, left = less risk)")
    plt.tight_layout()
    plt.savefig("results/feature_weights.png", dpi=200)
    print("\nSaved model.joblib and the tables in results/")


if __name__ == "__main__":
    main()
```

- The final model is trained on all 12 projects and saved with `joblib.dump`. `predict.py` loads this file.
- `final[-1]` is the last step of the pipeline, the logistic regression. `.coef_[0]` are its 9 weights.
- The rest draws the bar chart: blue for weights above 0 (more risk), red for below 0 (less risk).

Check:
```
python3 train_model.py > my_output.txt
diff --strip-trailing-cr my_output.txt ../expected_output.txt && echo SAME
```
Expected: `SAME`. If lines are printed, look at them: differences in the third
decimal are fine (another version of scikit-learn), anything bigger is a typing
mistake.

### 3.4 `predict.py`

```python
"""
predict.py - step 3: use the trained model on any project.

Give it a GitHub address or a folder that is a git repository. It prints the
files most likely to need a bug fix in the coming year, as of today.

Run:    python3 predict.py https://github.com/pallets/flask
        python3 predict.py /path/to/my/project
        python3 predict.py /path/to/my/project 25      (show 25 files)
"""
import os
import subprocess
import sys
import tempfile
import time

import joblib
import pandas as pd

from features import FEATURES, build_features, file_sizes, read_commits


def main():
    target = sys.argv[1]
    how_many = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    if target.startswith("http"):                       # a GitHub address: download it
        repo_dir = os.path.join(tempfile.mkdtemp(), "repo.git")
        subprocess.run(["git", "clone", "--quiet", "--bare", "--single-branch", "--no-tags",
                        target, repo_dir], check=True)
    elif os.path.isdir(os.path.join(target, ".git")):   # a normal project folder
        repo_dir = os.path.join(target, ".git")
    else:                                               # a bare clone
        repo_dir = target

    now = int(time.time())
    rows = build_features(read_commits(repo_dir), file_sizes(repo_dir, now), now)
    files = pd.DataFrame(rows)

    # Same preprocessing as in training: position of each number inside the project
    ranked = files[FEATURES].rank(pct=True)

    model = joblib.load("model.joblib")
    files["risk"] = model.predict_proba(ranked)[:, 1].round(2)
    files = files.sort_values("risk", ascending=False)

    print(f"{len(files)} source files scored. The {how_many} with the highest risk:\n")
    print(files[["risk", "file", "loc", "commits", "authors", "recent_bugfixes"]]
          .head(how_many).to_string(index=False))


if __name__ == "__main__":
    main()
```

- `sys.argv` is what you typed after the name of the script. `sys.argv[1]` is the project, `sys.argv[2]` the optional number of files to show.
- Three cases: a web address is cloned into a temporary folder; a normal project folder has its history in the hidden `.git` folder; anything else is treated as a bare clone.
- `now = int(time.time())`: the "cutoff" is this moment. The same `build_features` is used as in training, so the numbers mean the same thing.
- There is no label here. Nobody knows yet what will happen next year.
- `files[FEATURES].rank(pct=True)`: the same preprocessing as in training, inside this one project.
- The model gives the risk, the table is sorted, the top rows are printed.

Check:
```
python3 predict.py repos/python-poetry__poetry.git 5
```
Expected on 24 November 2026 (it changes a little as the project changes):
```
174 source files scored. The 5 with the highest risk:

 risk                                       file  loc  commits  authors  recent_bugfixes
 0.93 src/poetry/repositories/http_repository.py  603       38       14                3
 0.93        src/poetry/installation/executor.py  986      101       39                3
 0.93        src/poetry/utils/env/env_manager.py  647       27       13                3
 0.92              src/poetry/packages/locker.py  652       73       23                3
 0.91          src/poetry/utils/authenticator.py  505       55       20                6
```

You have now rebuilt the whole project. Go back up one folder for the rest:

```
cd ..
```

---

## Part 4: The model and the measures

Run this now and keep the output open. Parts 4 and 5 walk through it.

```
python3 extra_checks.py
```

(The same output is saved in `expected_extra_checks.txt`.)

### 4.1 Why positions instead of raw numbers

Raw numbers of two projects do not mean the same thing. 500 lines is a large
file in Poetry and an ordinary one in pandas. After the preprocessing, `loc =
0.95` means "larger than 95% of the files in its own project", in every project.

It costs one line of code and it needs no labels, so it can be done for a new
project too. Effect, from the two tables that `train_model.py` prints:

| Logistic regression | F1 | AUC |
|---|---|---|
| raw numbers | 0.541 | 0.805 |
| positions | 0.610 | 0.837 |

### 4.2 Logistic regression, with one prediction by hand

The model has one weight per feature and one extra number, the intercept.
For one file:

1. take the 9 positions;
2. standardise each one: `(position - mean) / spread` (this is what `StandardScaler` does; mean and spread were measured on the training data);
3. multiply each by its weight and add everything up, plus the intercept;
4. squeeze the sum into the range 0 to 1 with `risk = 1 / (1 + e^(-sum))`.

Check 1 in `extra_checks.py` prints exactly this for `scrapy/extensions/feedexport.py`:

```
                   raw value  position  standardised  weight  contribution
loc                      727     0.988         1.683   0.722         1.215
commits                  146     0.970         1.622   0.395         0.641
authors                   48     0.994         1.706   0.113         0.193
churn                   3027     0.982         1.662  -0.095        -0.158
bugfixes                  24     1.000         1.753   0.255         0.446
age_days                3837     0.293        -0.735  -0.333         0.245
days_since_change          4     0.118        -1.340  -0.241         0.324
recent_commits            18     0.982         1.720   0.029         0.050
recent_bugfixes            3     1.000         2.292   0.106         0.242

sum of contributions 3.197 + intercept -0.323 = 2.874
risk = 1 / (1 + e^-2.874) = 0.947
the model itself says:           0.947
```

Read it like this:

- `loc`: 727 lines is larger than 98.8% of Scrapy's files. Standardised 1.683, times the weight 0.722, gives +1.215. Size is the biggest push towards "risky".
- `age_days` has a negative weight (old files are safer). But this file is young for Scrapy (position 0.293, standardised -0.735), and minus times minus gives plus: +0.245.
- `days_since_change`: changed 4 days before the cutoff, so a very low position, and again minus times minus: +0.324.
- The sum is 2.874, and `1 / (1 + e^-2.874)` = 0.947.

**Training** means: find the 9 weights and the intercept that make these risks
agree as well as possible with the labels of the training files. The computer
does it by trying small changes of the weights many times (that is the
`max_iter`).

The weights of the final model:

| Feature | Weight | Meaning |
|---|---|---|
| loc | 0.72 | larger file, more risk |
| commits | 0.40 | changed more often, more risk |
| bugfixes | 0.25 | more bug fixes in the past, more risk |
| authors | 0.11 | more people, a little more risk |
| recent_bugfixes | 0.11 | bug fixes in the last year, a little more risk |
| recent_commits | 0.03 | almost nothing |
| churn | -0.10 | almost nothing (it repeats what loc and commits already say) |
| days_since_change | -0.24 | not touched for long, less risk |
| age_days | -0.33 | older file, less risk |

### 4.3 Decision tree and random forest

- **Decision tree:** a chain of yes/no questions learned from the data, for example "is `loc` above 0.6?", then "is `bugfixes` above 0.8?". At the end of each path is a share of buggy files, and that is the risk. `max_depth=5` allows 5 questions in a row.
- **Random forest:** 300 trees. Each tree sees a random sample of the files and a random choice of features, so the trees differ. The risk is the average of the 300 answers. It is usually more stable than one tree.

### 4.4 Leave one project out

12 rounds. In each round one project is the exam and the other 11 are the
lessons. Each project is the exam once. The reported number is the average of
the 12 exams, so each project counts the same, whether it has 81 files or 331.

### 4.5 The measures, by hand

Check 2 prints the numbers for Scrapy as the test project:

```
files 169, really buggy 51, flagged by the model 70
TP 37   FP 33   FN 14   TN 85
precision = TP / (TP + FP) = 37 / 70 = 0.529
recall    = TP / (TP + FN) = 37 / 51 = 0.725
F1        = 2 * P * R / (P + R) = 0.612
accuracy  = (TP + TN) / all = 0.722   (saying 'clean' for every file: 0.698)
top 20%   = the 34 riskiest files contain 24 of the 51 buggy files = 0.471
AUC       = 0.788
```

| | Model says buggy (70) | Model says clean (99) |
|---|---|---|
| **Really buggy (51)** | TP = 37 (caught) | FN = 14 (missed) |
| **Really clean (118)** | FP = 33 (false alarm) | TN = 85 (correctly left alone) |

- **Precision** 37/70 = 0.529: of the 70 files the model flagged, 37 really were buggy.
- **Recall** 37/51 = 0.725: of the 51 buggy files, the model caught 37.
- **F1** 0.612: one number for both. It is high only when both are high.
- **Accuracy** 0.722: the share of all answers that are right. **It is not used in the report**, and you can see why: a "model" that says "clean" for every file gets 0.698 and finds no bug at all.
- **Top 20%** 24/51 = 0.471: review the 34 riskiest files (20% of 169) and you have looked at 24 of the 51 buggy ones.
- **AUC** 0.788: take one buggy and one clean file at random; in 78.8% of such pairs the buggy file has the higher risk. 0.5 would be coin flipping, 1.0 perfect. AUC does not depend on the 0.5 threshold; it judges only the order.

---

## Part 5: "What if" experiments

These are checks 3 to 7 of `extra_checks.py`. Each answers a question you may be asked.

### 5.1 What if the threshold is not 0.5?

```
threshold 0.3: precision 0.462  recall 0.897  F1 0.580  files flagged 61%
threshold 0.5: precision 0.558  recall 0.758  F1 0.610  files flagged 42%
threshold 0.7: precision 0.676  recall 0.534  F1 0.562  files flagged 24%
```

A lower threshold flags more files: more bugs caught (recall up), more false
alarms (precision down). A higher one does the opposite. There is no "right"
value; it depends on how much review time the team has. 0.5 gives the best F1
of the three.

### 5.2 Which features matter?

```
all 9 features         0.837
without loc            0.828
only loc               0.827
only commits           0.777
only loc + bugfixes    0.833
```

- Size alone reaches 0.827.
- The 8 history features **without** size reach 0.828. So history is as good as size.
- Together they reach 0.837, only a little more, because they overlap: large files are also the files that are changed often.
- Two features (`loc` and `bugfixes`) already give 0.833.

### 5.3 What if a random 80/20 split is used?

```
Logistic regression  random split AUC 0.830   leave-one-project-out AUC 0.837
Decision tree        random split AUC 0.790   leave-one-project-out AUC 0.786
Random forest        random split AUC 0.821   leave-one-project-out AUC 0.821
```

Here the two ways give almost the same numbers. Leave-one-project-out is still
the right choice, because the question is "does it work on a project it has
never seen", and a random split cannot answer that: files of the test project
are also in the training part.

### 5.4 Is the model overfitting?

Overfitting means: the model memorises the training data and is much worse on
new data.

```
Logistic regression  on data it was trained on 0.841   on unseen projects 0.837
Decision tree        on data it was trained on 0.852   on unseen projects 0.786
Random forest        on data it was trained on 0.981   on unseen projects 0.821
```

- Logistic regression: 0.841 against 0.837. No gap, no overfitting. It has only 10 numbers to learn, so it cannot memorise 2,492 files.
- Random forest: 0.981 against 0.821. A big gap: it memorises the training files, and that does not carry over to new projects.
- This is a second reason for choosing logistic regression.

### 5.5 Does the model really beat "largest files first"?

```
The model has the higher AUC in 8 of 12 projects.
```

On average 0.837 against 0.827. It wins in 8 projects and loses in 4 (networkx,
pytest, poetry, scrapy). That is a small advantage, not a clear win, and no
statistical test was done. Say it this way.

---

## Part 6: Questions and answers

### About the problem

**What does the project do, in one sentence?**
It predicts, for every source file of a project, whether the file will need a
bug fix in the next 12 months, using only the git history.

**Which software engineering activity does it support?**
Deciding where to spend code review and testing effort.

**Does it find bugs?**
No. It does not read the code. It says where bugs are likely, so that people
look there first.

**Is this a new idea?**
No. It is called defect prediction and has been studied for more than twenty years
(the report cites eight papers). What is mine is the data, collected from
scratch, and the evaluation.

### About the data

**Where does the data come from?**
From the git history of 12 open-source Python projects on GitHub: 129,357
commits, 2,492 source files. I collected it with `git clone` and `git log`.

**Why these 12 projects?**
They are well known, active, and from different areas. That is a choice by
hand, and it is a limitation: all are popular, well-maintained libraries.

**How do you know which commit is a bug fix?**
By words in the first line of the message: fix, fixes, fixed, bug, bugfix,
crash, regression, and not typo, doc, docstring, comment.

**Is that reliable?**
Not fully. "Fix deprecation warning" is counted, and a real fix described as
"handle empty input" is missed. It is the standard method in this research
area and the first limitation in my report. Better: use the issue tracker.

**What is one row of the dataset?**
One file of one project, as it was on 1 November 2025: 9 numbers and a label.

**Where does the label come from?**
`buggy = 1` if at least one bug-fix commit changed the file between 1 November
2025 and 1 November 2026.

**Can the model see the answer (data leakage)?**
No. Features use only commits before the cutoff, the label only commits after
it. In `build_features` the line `if commit["time"] >= when: continue` skips
everything from the cutoff on.

**Why 1 November 2025?**
It is the latest date that still leaves a full year of history after it to
check against.

**Why 12 months?**
Long enough for bugs to be found and fixed. A shorter window gives very few
buggy files.

**Why are tests and documentation removed?**
A "fix" in a test or in the documentation is not a defect of the product.

**Why only Python files?**
To keep the dataset consistent. Nothing in the method depends on Python; the
pattern `'*.py'` could be changed.

**Why skip merge commits?**
A merge only joins branches. The real changes are in the normal commits, which
are counted.

**What happens with renamed files?**
With `--no-renames` a rename looks like "old file deleted, new file created".
The new name starts with an empty history. It is a limitation.

**What about files created after the cutoff, or deleted before it?**
They are not in the dataset. Only files that existed on the cutoff date are.

**Do you store personal data?**
No. Author e-mails are used only in memory to count different people. The
dataset contains only the count.

**Is the same person counted twice?**
If they used two e-mail addresses, yes. It is a small inaccuracy.

**Is the dataset balanced?**
No, 30.5% of the files are buggy, and it varies from 8.7% (sphinx) to 57.1%
(pandas). That is why `class_weight="balanced"` is used and accuracy is not.

### About the preprocessing and the model

**What preprocessing do you do?**
Each feature is replaced by its rank inside its own project, between 0 and 1.
For logistic regression the values are then standardised.

**Why?**
Projects differ in size. 500 lines is large in one project and normal in
another. With ranks, F1 goes from 0.541 to 0.610 and AUC from 0.805 to 0.837.

**Does the ranking use information from the test project? Is that leakage?**
It uses the feature values of the test project, not its labels. These values
are known at the moment of prediction, so it is allowed. `predict.py` does the
same for a new project.

**Why standardise if the ranks are already between 0 and 1?**
The effect is small. It is kept so that the same pipeline also works on the raw
numbers, which is needed for the comparison with and without preprocessing.

**What type of machine learning is this?**
Supervised learning, binary classification.

**Why these three models?**
They are the standard models for a small table of numbers. Logistic regression
is the simplest, a tree can ask yes/no questions, a forest combines many trees.

**Why is logistic regression the final model?**
It has the best recall, F1, AUC and top-20% of the three, it does not overfit
(0.841 on training data, 0.837 on unseen projects), and each feature has one
weight that can be explained.

**How does logistic regression compute a prediction?**
Weighted sum of the standardised features plus an intercept, then
`1 / (1 + e^(-sum))`. (Part 4.2 has the example: sum 2.874 gives risk 0.947.)

**Is a risk of 0.95 a 95% probability?**
No. Because of the balanced class weights the risks are pushed up: about 42% of
the files get 0.5 or more, while 30% are buggy. Use it as a score for ordering
the files, not as a probability.

**Did you tune the hyperparameters?**
No. I used fixed, common settings. Tuning would need a third part of the data
(a validation set), otherwise I would be tuning on the test data and the
results would look better than they are. It is a possible improvement.

**Why `random_state=42`?**
Trees use random choices. A fixed number makes the run repeatable. 42 has no
special meaning.

**Why not deep learning?**
2,492 rows and 9 numbers per row. Simple models are the usual choice for such
data, and the simplest one already wins here.

### About the evaluation and the results

**How did you test the model?**
Leave one project out: train on 11 projects, test on the 12th, 12 times. The
numbers are averages over the 12 test projects.

**Why not a random 80/20 split?**
Then files of the same project are in both parts, and the test does not show
whether the model works on a new project. (I tried it: the AUC is about the
same, 0.830 against 0.837, but it answers a different question.)

**Why not accuracy?**
With 30% buggy files, saying "clean" for everything gives about 70% accuracy
and finds nothing. Precision, recall and AUC show what accuracy hides.

**What are your main results?**
On unseen projects: AUC 0.837, recall 0.758, precision 0.558, F1 0.610. The
riskiest 20% of files contain 48% of the buggy files; a random choice gives 20%.

**Explain precision 0.558 and recall 0.758.**
Of the files the model flags, 56% really get a bug fix. Of the files that get a
bug fix, the model flags 76%.

**Explain AUC 0.837.**
Take one buggy and one clean file at random: in 84% of the cases the model
gives the buggy file the higher risk.

**Why is precision so low for sphinx (0.173)?**
Only 8.7% of the sphinx files are buggy, but the model flags about 40% of the
files in every project. So most flagged files there are clean. The ranking is
still good (AUC 0.836). A threshold per project would fix it.

**Why is the top-20% value low for pandas (0.343) although the model is good there?**
In pandas 57% of the files are buggy. The top 20% are 60 files, and there are
172 buggy files, so the maximum possible is 60/172 = 0.35.

**The rule "largest files first" has AUC 0.827. Your model has 0.837. So what is the point?**
For ordering the files the gain is small, and I say so in the report. The model
wins in 8 of 12 projects, and no statistical test was done, so it is close to a
tie. What the model adds: a yes/no answer with known precision and recall, and
it still works when size is taken away (history alone gives 0.828). The honest
conclusion is that size carries most of the signal.

**Why is size so strong?**
A larger file has more code that can be wrong, and it is also more likely to be
touched by any commit, including a bug fix. Part of it is real and part is an
effect of how the label is made.

**The other projects' labels come from the same year you are predicting. In real life you would not have them yet. Is that a problem?**
Yes, that is a simplification of the test. In real use the model is trained on
an older period and applied today, which is what `predict.py` does: the saved
model learned from 2025-2026 and scores the files as they are now. The test
assumes that the link between history and bugs is the same from one year to the
next. A stricter test would train on an earlier cutoff.

**How was it validated with real examples?**
Three ways. (1) Every prediction is compared with what really happened in the
following year, on projects the model did not see. (2) A concrete case: 7 of
the 10 riskiest Scrapy files got a bug fix; in Scrapy as a whole 30%. (3) Feedback from
people on a project they know (section 5.5 of the report; fill this in).

**What are the limitations?**
Noisy labels from keywords; the size effect; renamed files lose their history;
only Python, 12 projects and one year; one fixed threshold for all projects.

**What would you improve?**
Labels from the issue tracker; predict bugs per line so that size is not
favoured; features from the code itself (complexity); more projects and several
cutoff dates; a threshold per project; a bot that warns on a pull request.

### About the code

**What does `--bare` do?** Downloads only the history, no working files.

**What does `--numstat` do?** Prints, for each commit, the lines added and deleted per file.

**What does `-- '*.py'` do?** Limits the log to Python files.

**What does `--first-parent` do?** Stays on the main line of the history when looking for the snapshot at the cutoff.

**What is `predict_proba(...)[:, 1]`?** The model gives two columns, the chance of class 0 and of class 1. This takes the second.

**What is `groupby("repo")[FEATURES].rank(pct=True)`?** Per project, replace each value by its rank as a share between 0 and 1.

**What is `model.joblib`?** The trained final model saved to a file, so `predict.py` can use it without training again.

---

## Part 7: The demo and the summary

### A live demo in four commands

```
python3 -c "import pandas as pd; d = pd.read_csv('data/dataset.csv'); print(len(d)); print(d.sample(5, random_state=1).to_string())"
python3 train_model.py
python3 extra_checks.py
python3 predict.py https://github.com/pallets/flask 10
```

1. the dataset: number of rows and five example rows;
2. training and the result tables (20 seconds);
3. one prediction by hand and the experiments;
4. the model applied to a project it has never seen.

If there is no internet in the room, clone Flask before and give the folder
instead of the address.

### The one-minute summary

"Teams cannot review and test every file. I built a model that ranks the files
of a project by the risk of needing a bug fix in the next year. I collected the
data myself from the git history of 12 open-source Python projects: 129
thousand commits, about 2,500 files. Each file is described by nine numbers
from its history before 1 November 2025, and the label says whether a bug-fix
commit touched it in the year after. I compared three models by always testing
on a project left out of training. Logistic regression was best: AUC 0.84, it
catches 76% of the buggy files, and the riskiest 20% of files contain 48% of
them. I also compared with a simple rule, largest files first, which is almost
as good. So the main finding is that the model works on unseen projects, but
that file size explains most of it."

### Numbers to know by heart

| What | Value |
|---|---|
| Projects / commits / files | 12 / 129,357 / 2,492 |
| Buggy files | 761 (30.5%) |
| Cutoff / end of the label window | 1 Nov 2025 / 1 Nov 2026 |
| Features | 9 |
| Final model | logistic regression |
| AUC / F1 / precision / recall | 0.837 / 0.610 / 0.558 / 0.758 |
| Buggy files found in the riskiest 20% | 48.2% (random: 20%) |
| Rule "largest files first", AUC | 0.827 |
| Effect of preprocessing on F1 | 0.541 to 0.610 |
| Scrapy example | 7 of the top 10 were fixed |
