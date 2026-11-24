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
