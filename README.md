# Predicting bug-prone files from git history

## The idea in four sentences

A team never has time to review and test every file equally.
This project looks at the git history of a project and gives every file a
risk score: how likely is it that this file will need a bug fix in the next year?
The team can then review and test the riskiest files first.
The model learns this from 12 open-source Python projects, where we can see
what really happened.

## How to run it

Python 3.9+ and git are needed. About 1.3 GB of free disk space (the downloaded projects).

```
pip install -r requirements.txt
python3 collect_data.py        # 3-8 minutes, mostly downloading
python3 train_model.py         # about 20 seconds
python3 predict.py https://github.com/pallets/flask
```

`expected_output.txt` is what `train_model.py` printed when the report was
written. Your numbers should be the same or differ only in the last digit.

`data/dataset.csv` is included, so `train_model.py` also works without running
`collect_data.py` first.

To learn the project in depth, follow `STUDY_GUIDE.md`. It rebuilds everything
step by step with a check after each step. `extra_checks.py` holds the small
experiments the guide uses (one prediction by hand, other thresholds, which
features matter, overfitting).

## The files

| File | What it does |
|---|---|
| `features.py` | Reads the git history of one project and turns it into numbers per file. The other scripts use it. |
| `collect_data.py` | Step 1. Downloads the 12 projects and builds `data/dataset.csv`, one row per file. |
| `train_model.py` | Step 2. Trains three models, tests them, prints the tables, saves the best model as `model.joblib`. |
| `predict.py` | Step 3. Uses the saved model on any project and prints its riskiest files. |

## Step 1: where the data comes from

For each project, `collect_data.py` does this:

1. **Download.** `git clone --bare` downloads the full history of the project.
   `--bare` means only the history, without a folder of source files.
2. **Read the commits.** `git log --numstat` prints every commit with its date,
   author, message, and for every changed file the lines added and deleted.
3. **Decide which commits are bug fixes.** A commit is a bug fix when the first
   line of its message contains *fix, fixes, fixed, bug, bugfix, crash* or
   *regression*, and is not about text (*typo, doc, docstring, comment*).
4. **Pick a date in the past: 1 November 2025.** Everything before this date is
   what the model is allowed to see. Everything in the year after it is the
   answer we check against.
5. **Describe every file with 9 numbers**, using only commits before that date.
6. **Label every file.** `buggy = 1` if at least one bug-fix commit changed the
   file between 1 November 2025 and 1 November 2026, otherwise `0`.

Only `.py` files are used. Tests, documentation and examples are skipped.

The 9 numbers (features):

| Name | Meaning |
|---|---|
| `loc` | lines in the file on 1 November 2025 |
| `commits` | how many commits changed the file |
| `authors` | how many different people changed it |
| `churn` | lines added + lines deleted over all those commits |
| `bugfixes` | how many of those commits were bug fixes |
| `age_days` | days since the file was created |
| `days_since_change` | days since the file was last changed |
| `recent_commits` | commits in the last 365 days before the date |
| `recent_bugfixes` | bug-fix commits in the last 365 days before the date |

Result: 2,492 files, of which 761 (30.5%) are buggy.

To look at the data yourself:

```
head -5 data/dataset.csv
python3 -c "import pandas as pd; d=pd.read_csv('data/dataset.csv'); print(d.sort_values('commits').tail(10).to_string())"
```

## Step 2: training and testing

**Preprocessing (one line of code).** Every number is replaced by its position
inside its own project, from 0 to 1. For example `loc = 0.95` means "larger
than 95% of the files in this project". Reason: a 500-line file is large in a
small project and ordinary in a big one, so the raw numbers of different
projects cannot be compared, but positions can.

**Three models are compared:**

- Logistic regression: gives each feature a weight, adds them up, turns the sum into a risk between 0 and 1.
- Decision tree: a chain of yes/no questions ("is the file in the larger half?").
- Random forest: 300 decision trees that vote.

**How they are tested: leave one project out.** Take one project away, train on
the other 11, predict the files of the one taken away, compare with what really
happened. Repeat 12 times, once per project, and average. The model is always
judged on a project it has never seen, which is how it would be used in real life.

**The measures:**

- **Precision**: of the files the model called buggy, how many really were.
- **Recall**: of the files that really were buggy, how many the model caught.
- **F1**: one number that combines precision and recall.
- **AUC**: take one buggy and one clean file at random; how often does the buggy one get the higher risk? 0.5 is guessing, 1.0 is perfect.
- **top20**: if the team inspects only the riskiest 20% of files, what share of all buggy files is in there? Picking files at random would give 0.20.

**Two simple rules without machine learning** are measured the same way, to see
whether the model is worth having: "inspect the largest files first" and
"inspect the most changed files first".

## The results in short

| Method | Precision | Recall | F1 | AUC | top20 |
|---|---|---|---|---|---|
| Logistic regression | 0.558 | 0.758 | 0.610 | 0.837 | 0.482 |
| Decision tree | 0.540 | 0.675 | 0.553 | 0.786 | 0.421 |
| Random forest | 0.580 | 0.690 | 0.587 | 0.821 | 0.465 |
| Rule: largest files | - | - | - | 0.827 | 0.469 |
| Rule: most changed files | - | - | - | 0.777 | 0.447 |

- Logistic regression is the best model, so it is the one saved and used.
- On projects it has never seen it catches 76% of the buggy files, and 56% of the files it flags are really buggy (30% would be buggy if you flagged files at random).
- Inspecting the riskiest 20% of files finds 48% of the buggy ones, against 20% for a random choice.
- The honest part: the rule "largest files first" is almost as good (0.827 against 0.837). File size is by far the strongest signal. The model is a small improvement, not a big one.
- Real example: for Scrapy, 7 of the 10 files the model ranked highest did get a bug fix in the following year. In Scrapy as a whole 30% of files did.

## Questions you may be asked

**Where do the labels come from? Did you label files by hand?**
No. The label comes from history: a file is buggy if a bug-fix commit changed it
in the following year. Bug-fix commits are found by keywords in the message.
This is a standard method in research, and it is not perfect (see limitations).

**Does the model see the answer?**
No. The features use only commits before 1 November 2025, the label uses only
commits after it. In `features.py` the line `if commit["time"] >= when: continue`
enforces this.

**Why test on whole projects instead of a random 80/20 split?**
With a random split, files of the same project land in both parts, and the model
is tested on a project it already knows. Leaving a whole project out is stricter
and closer to real use on a new project.

**Why convert the numbers to positions inside the project?**
Projects have different sizes and habits. With this step the F1 of logistic
regression goes from 0.541 to 0.610 and the AUC from 0.805 to 0.837
(both tables are printed by `train_model.py`).

**Why logistic regression and not the random forest?**
It had the best scores in the comparison, and it is the easiest to explain:
each feature has one weight (`results/feature_weights.png`).

**What do the weights say?**
Larger files, files changed often, and files with past bug fixes are riskier.
Old files and files nobody has touched for a long time are safer. `churn` is
near zero because it says almost the same thing as `loc` and `commits`.

**What is `class_weight="balanced"`?**
Only 30% of the files are buggy. Without it a model can look good by saying
"clean" most of the time. With it, mistakes on buggy files count more.

**If "largest files first" is almost as good, why use machine learning?**
For ranking, the gain is small, and the report says so. The model does give two
things the rule does not: a yes/no decision with a known precision and recall,
and one score that combines size with the history of the file.

**What are the weak points?**
- Keywords miss bug fixes that are worded differently and catch some that are not bugs.
- A renamed file loses its history.
- Bigger files are changed more often for any reason, so size is partly a shortcut.
- Only Python, only 12 projects, only one test year.

## User feedback (for the validation section of the report)

The assignment asks for feedback from real users. It takes about 15 minutes per person.

1. Pick a Python project that the person knows well: their own, or an
   open-source one they use. For a folder on your computer:
   `python3 predict.py /path/to/project 10`
2. Show them the 10 files and ask:
   - How many of these 10 would you also call risky?
   - Is there a file you expected in the list that is missing?
   - Would you use such a list to decide what to review or test first? (1 = no, 5 = yes)
3. Write the answers in the table in section 5.4 of the report.
