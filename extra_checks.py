"""
extra_checks.py - NOT part of the pipeline. Small experiments for understanding
the project and for answering "what if" questions. Needs data/dataset.csv and
model.joblib (run train_model.py first).

Run:    python3 extra_checks.py
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from features import FEATURES
from train_model import found_in_top20, make_models

raw = pd.read_csv("data/dataset.csv")
data = raw.copy()
data[FEATURES] = raw.groupby("repo")[FEATURES].rank(pct=True)      # same preprocessing as training
PROJECTS = sorted(data.repo.unique())


def leave_one_out(model_name="Logistic regression", features=FEATURES):
    """Risk for every file, always predicted by a model that never saw its project."""
    risk = pd.Series(0.0, index=data.index)
    for project in PROJECTS:
        train, test = data[data.repo != project], data[data.repo == project]
        model = make_models()[model_name].fit(train[features], train.buggy)
        risk[test.index] = model.predict_proba(test[features])[:, 1]
    return risk


def average_auc(risk):
    """AUC per project, then the average (the way the report does it)."""
    return np.mean([roc_auc_score(data.buggy[data.repo == p], risk[data.repo == p]) for p in PROJECTS])


def check_1_one_prediction_by_hand():
    print("\n=== 1. One prediction calculated by hand =====================================")
    model = joblib.load("model.joblib")
    scaler, logreg = model[0], model[-1]
    row = data[data.file == "scrapy/extensions/feedexport.py"].index[0]

    position = data.loc[row, FEATURES].values.astype(float)        # the 9 numbers the model gets
    standardised = (position - scaler.mean_) / scaler.scale_       # what StandardScaler does
    weight = logreg.coef_[0]
    table = pd.DataFrame({"raw value": raw.loc[row, FEATURES].values, "position": position.round(3),
                          "standardised": standardised.round(3), "weight": weight.round(3),
                          "contribution": (standardised * weight).round(3)}, index=FEATURES)
    print(table.to_string())

    total = (standardised * weight).sum() + logreg.intercept_[0]
    print(f"\nsum of contributions {(standardised * weight).sum():.3f} + intercept {logreg.intercept_[0]:.3f} = {total:.3f}")
    print(f"risk = 1 / (1 + e^-{total:.3f}) = {1 / (1 + np.exp(-total)):.3f}")
    print(f"the model itself says:           {model.predict_proba(data.loc[[row], FEATURES])[0, 1]:.3f}")


def check_2_measures_by_hand(risk, project="scrapy/scrapy"):
    print(f"\n=== 2. The measures calculated by hand for {project} ======================")
    truth = data.buggy[data.repo == project].values
    r = risk[data.repo == project].values
    flagged = r >= 0.5
    tp = int((flagged & (truth == 1)).sum())      # flagged and really buggy
    fp = int((flagged & (truth == 0)).sum())      # flagged but clean      (false alarm)
    fn = int((~flagged & (truth == 1)).sum())     # not flagged but buggy  (missed)
    tn = int((~flagged & (truth == 0)).sum())     # not flagged and clean
    print(f"files {len(truth)}, really buggy {truth.sum()}, flagged by the model {flagged.sum()}")
    print(f"TP {tp}   FP {fp}   FN {fn}   TN {tn}")
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    print(f"precision = TP / (TP + FP) = {tp} / {tp + fp} = {precision:.3f}")
    print(f"recall    = TP / (TP + FN) = {tp} / {tp + fn} = {recall:.3f}")
    print(f"F1        = 2 * P * R / (P + R) = {2 * precision * recall / (precision + recall):.3f}")
    print(f"accuracy  = (TP + TN) / all = {(tp + tn) / len(truth):.3f}   (saying 'clean' for every file: {(truth == 0).mean():.3f})")
    top = round(0.2 * len(truth))
    found = int(truth[np.argsort(-r, kind='stable')[:top]].sum())
    print(f"top 20%   = the {top} riskiest files contain {found} of the {truth.sum()} buggy files = {found / truth.sum():.3f}")
    print(f"AUC       = {roc_auc_score(truth, r):.3f}")


def check_3_thresholds(risk):
    print("\n=== 3. What happens when the 0.5 threshold is moved ==========================")
    for threshold in (0.3, 0.5, 0.7):
        rows = []
        for p in PROJECTS:
            truth, flagged = data.buggy[data.repo == p], risk[data.repo == p] >= threshold
            rows.append((precision_score(truth, flagged, zero_division=0), recall_score(truth, flagged),
                         f1_score(truth, flagged), flagged.mean()))
        precision, recall, f1, share = np.mean(rows, axis=0)
        print(f"threshold {threshold}: precision {precision:.3f}  recall {recall:.3f}  F1 {f1:.3f}  files flagged {share:.0%}")


def check_4_which_features_matter():
    print("\n=== 4. Leaving features out (logistic regression, average AUC) ===============")
    history = [f for f in FEATURES if f != "loc"]
    for name, features in [("all 9 features", FEATURES), ("without loc", history), ("only loc", ["loc"]),
                           ("only commits", ["commits"]), ("only loc + bugfixes", ["loc", "bugfixes"])]:
        print(f"{name:22s} {average_auc(leave_one_out(features=features)):.3f}")


def check_5_random_split():
    print("\n=== 5. A random 80/20 split instead of leaving a project out =================")
    train, test = train_test_split(data, test_size=0.2, random_state=42, stratify=data.buggy)
    for name, model in make_models().items():
        model.fit(train[FEATURES], train.buggy)
        test_risk = model.predict_proba(test[FEATURES])[:, 1]
        auc = np.mean([roc_auc_score(test.buggy[test.repo == p], test_risk[test.repo == p]) for p in PROJECTS])
        print(f"{name:20s} random split AUC {auc:.3f}   leave-one-project-out AUC {average_auc(leave_one_out(name)):.3f}")


def check_6_overfitting():
    print("\n=== 6. Overfitting: AUC on the training data against AUC on unseen projects ==")
    for name, model in make_models().items():
        model.fit(data[FEATURES], data.buggy)
        seen = np.mean([roc_auc_score(data.buggy[data.repo == p],
                                      model.predict_proba(data.loc[data.repo == p, FEATURES])[:, 1]) for p in PROJECTS])
        print(f"{name:20s} on data it was trained on {seen:.3f}   on unseen projects {average_auc(leave_one_out(name)):.3f}")


def check_7_model_against_size_rule(risk):
    print("\n=== 7. Model against the rule 'largest files first', project by project ======")
    wins = 0
    for p in PROJECTS:
        part = data.repo == p
        model_auc, rule_auc = roc_auc_score(data.buggy[part], risk[part]), roc_auc_score(data.buggy[part], raw["loc"][part])
        model_top, rule_top = found_in_top20(data.buggy[part], risk[part]), found_in_top20(data.buggy[part], raw["loc"][part])
        wins += model_auc > rule_auc
        print(f"{p:28s} AUC model {model_auc:.3f} rule {rule_auc:.3f}   top20 model {model_top:.3f} rule {rule_top:.3f}")
    print(f"The model has the higher AUC in {wins} of {len(PROJECTS)} projects.")


if __name__ == "__main__":
    check_1_one_prediction_by_hand()
    risk = leave_one_out()
    check_2_measures_by_hand(risk)
    check_3_thresholds(risk)
    check_4_which_features_matter()
    check_5_random_split()
    check_6_overfitting()
    check_7_model_against_size_rule(risk)
