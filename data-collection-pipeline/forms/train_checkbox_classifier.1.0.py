"""
Trains a small classifier that replaces the fixed darkness/angle-cluster
thresholds extract_paper_form uses to decide "is this checkbox marked?" --
the other half of the correction feedback loop --ingest was set up for:
operator corrections accumulate in labels/checkbox_labels.csv, and this
script turns that CSV into a model extract_paper_form.1.4.py can load with
--model <path>.

Features are the SAME two signals the fixed thresholds already used
(dark_fraction, stroke_angle_clusters), computed with the exact same code
extraction uses -- so this is closer to "let the data pick the thresholds"
than a wholly new approach, which matters with only a few dozen labels.

This does NOT retrain price or header OCR (that's real handwriting/digit
recognition -- a much bigger undertaking, out of scope here). It only ever
replaces the checkbox marked/blank decision.

Usage:
    python3 train_checkbox_classifier.1.0.py <checkbox_labels.csv> [<more_labels.csv> ...] <out_model.pkl>

Example:
    python3 train_checkbox_classifier.1.0.py real_scan_v2/labels/checkbox_labels.csv models/checkbox_classifier.1.0.pkl
"""

import sys
import os
import importlib.util
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_predict, StratifiedKFold, LeaveOneOut
from sklearn.metrics import accuracy_score, confusion_matrix

# Reuse the exact feature-extraction code extraction itself uses, so training
# and inference can never quietly drift apart.
spec = importlib.util.spec_from_file_location("extract_paper_form", "extract_paper_form.1.4.py")
extract_paper_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_paper_form)
_dark_fraction = extract_paper_form._dark_fraction
_stroke_angle_clusters = extract_paper_form._stroke_angle_clusters

FEATURE_NAMES = ["dark_fraction", "stroke_angle_clusters"]
MIN_SAMPLES = 6  # below this, cross-validation is meaningless and we refuse to train


def load_labels(paths):
    frames = [pd.read_csv(p, dtype=str) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    # a crop_path that appears in more than one file (e.g. a re-corrected
    # example) keeps its LAST occurrence -- the most recent correction wins
    df = df.drop_duplicates(subset="crop_path", keep="last").reset_index(drop=True)
    return df


def compute_features(df):
    X, y, kept_paths = [], [], []
    for _, row in df.iterrows():
        crop_path = row["crop_path"]
        if not os.path.exists(crop_path):
            print(f"  [skip] missing crop file: {crop_path}")
            continue
        img = Image.open(crop_path)
        gray = np.array(img.convert("L"))
        X.append([_dark_fraction(gray), _stroke_angle_clusters(gray)])
        y.append(row["true_value"].strip().lower() == "true")
        kept_paths.append(crop_path)
    return np.array(X, dtype=float), np.array(y, dtype=bool), kept_paths


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    *label_csvs, out_model_path = sys.argv[1:]

    df = load_labels(label_csvs)
    df = df[df["field_type"] == "checkbox"].reset_index(drop=True)
    print(f"Loaded {len(df)} checkbox labels from {len(label_csvs)} file(s)")

    X, y, kept_paths = compute_features(df)
    n = len(y)
    n_true, n_false = int(y.sum()), int((~y).sum())
    print(f"Usable examples: {n} (marked={n_true}, blank={n_false})")

    if n < MIN_SAMPLES or n_true == 0 or n_false == 0:
        print(f"\nRefusing to train: need at least {MIN_SAMPLES} labeled examples covering "
              f"BOTH classes (marked and blank). Correct more scans via the review tool, "
              f"--ingest them, and re-run this once you have more.")
        sys.exit(1)

    pipeline = Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced")),
    ])

    # Honest out-of-sample accuracy estimate before fitting on everything.
    # With very few examples, leave-one-out is the least optimistic option;
    # once there's more data, k-fold is more stable.
    if n < 30:
        cv = LeaveOneOut()
        cv_desc = "leave-one-out"
    else:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        cv_desc = "5-fold"
    y_pred_cv = cross_val_predict(pipeline, X, y, cv=cv)
    cv_accuracy = accuracy_score(y, y_pred_cv)
    tn, fp, fn, tp = confusion_matrix(y, y_pred_cv, labels=[False, True]).ravel()

    print(f"\nCross-validated accuracy ({cv_desc}): {cv_accuracy:.3f}")
    print(f"  true blank predicted blank:  {tn}")
    print(f"  true blank predicted marked: {fp}  <- false positives")
    print(f"  true marked predicted blank: {fn}  <- false negatives")
    print(f"  true marked predicted marked:{tp}")
    if n < 30:
        print(f"  (only {n} examples -- treat this number as a rough signal, not a "
              f"guarantee; retrain as more corrections come in)")

    # Refit on all available data for the model that actually ships.
    pipeline.fit(X, y)

    os.makedirs(os.path.dirname(out_model_path) or ".", exist_ok=True)
    bundle = {
        "pipeline": pipeline,
        "feature_names": FEATURE_NAMES,
        "mark_style": "star",
        "n_samples": n,
        "n_true": n_true,
        "n_false": n_false,
        "cv_accuracy": round(float(cv_accuracy), 3),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source_files": label_csvs,
    }
    joblib.dump(bundle, out_model_path)
    print(f"\nWrote {out_model_path}")
    print(f"Use it with: python3 extract_paper_form.1.4.py ... --model {out_model_path}")


if __name__ == "__main__":
    main()
