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


def found_in_top20(truth, risk):
    """If we inspect only the 20% of files with the highest risk,
    what share of all buggy files do we find?"""
    truth, risk = np.asarray(truth), np.asarray(risk)
    top = np.argsort(-risk, kind="stable")[: round(0.2 * len(risk))]
    return truth[top].sum() / truth.sum()


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


def main():
    os.makedirs("results", exist_ok=True)
    raw = pd.read_csv("data/dataset.csv")

    # ---- the dataset ---------------------------------------------------------
    summary = raw.groupby("repo").agg(files=("buggy", "size"), buggy=("buggy", "sum"))
    summary.loc["TOTAL"] = summary.sum()
    summary["buggy_share"] = summary.buggy / summary.files
    print("DATASET\n" + summary.round(3).to_string() + "\n")
    summary.round(3).to_csv("results/dataset_summary.csv")

    # ---- preprocessing ---------------------------------------------------------
    # Replace every number by its position inside its own project, from 0 to 1
    # (1.0 = the highest value in that project). A 500-line file is big in one
    # project and ordinary in another; the position is comparable between projects.
    data = raw.copy()
    data[FEATURES] = raw.groupby("repo")[FEATURES].rank(pct=True)

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
