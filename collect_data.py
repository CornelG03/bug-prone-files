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
