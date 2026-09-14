"""
Trains a handwritten-digit classifier that extract_paper_form.1.5.py can use
in place of tesseract for price OCR (--digit-model <path>).

Unlike the checkbox classifier, this doesn't start from zero: scikit-learn
ships a real handwritten-digit dataset (load_digits, ~1800 examples, no
network needed) that gives full 0-9 coverage before you've corrected a
single price -- including digits you may not have any real example of yet.
Any price_labels.csv examples you've --ingest'd are layered on top of that
base set (each one segmented into individual digit glyphs and augmented
with small rotations/thickness changes) to nudge the classifier toward your
actual handwriting and paper/scan characteristics.

Digit-level accuracy on real examples is reported honestly via leave-one-
price-out cross-validation: for each real price, the classifier is trained
on everything else and tested on that one, so the reported number is a
genuine out-of-sample estimate, not training-set memorization. With only a
handful of real examples this number will be noisy and modest -- that's the
data-volume reality, not a bug -- but it should climb as --ingest
accumulates more real corrected prices and this is re-run.

This only trains a PRICE-digit classifier. Write-in item name recognition
(arbitrary handwritten words) is a different, larger problem -- see the
docstring in extract_paper_form.1.5.py for why it isn't in scope here.

Usage:
    python3 train_digit_classifier.1.0.py <price_labels.csv> [<more_labels.csv> ...] <out_model.pkl>

Example:
    python3 train_digit_classifier.1.0.py real_scan_v2/labels/price_labels.csv models/digit_classifier.1.0.pkl
"""

import sys
import os
import importlib.util
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
import cv2
from PIL import Image
from sklearn.datasets import load_digits
from sklearn.svm import SVC

# Reuse the exact segmentation/glyph code extraction itself uses, so training
# and inference can never quietly drift apart.
spec = importlib.util.spec_from_file_location("extract_paper_form", "extract_paper_form.1.5.py")
extract_paper_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_paper_form)
segment_digits = extract_paper_form.segment_digits
glyph_square = extract_paper_form.glyph_square
square_to_8x8 = extract_paper_form.square_to_8x8

N_AUG = 20  # augmented variants generated per real digit glyph -- see
# augment(); chosen empirically (tested 0/20/50 on the one real scan
# available while building this -- 20 already captured most of the gain)


def load_labels(paths):
    frames = [pd.read_csv(p, dtype=str) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="crop_path", keep="last").reset_index(drop=True)
    return df


def augment(square, n, rng):
    """Small rotations + thickness jitter (dilate/erode) -- a cheap stand-in
    for the pen-pressure/angle variation real data would eventually supply
    on its own, so a handful of real examples pull a bit more weight."""
    side = square.shape[0]
    out = []
    for _ in range(n):
        angle = rng.uniform(-12, 12)
        M = cv2.getRotationMatrix2D((side / 2, side / 2), angle, 1.0)
        rotated = cv2.warpAffine(square, M, (side, side), flags=cv2.INTER_LINEAR, borderValue=0)
        k = rng.choice([0, 1, 2])
        if k == 1:
            rotated = cv2.dilate(rotated, np.ones((3, 3), np.uint8), iterations=1)
        elif k == 2:
            rotated = cv2.erode(rotated, np.ones((2, 2), np.uint8), iterations=1)
        out.append(rotated)
    return out


def extract_real_glyphs(df):
    """Returns a list of (price_group_id, square, true_char) -- one entry per
    digit glyph, grouped by which original price string it came from (so
    leave-one-out can hold out a whole price, not just one digit of it)."""
    df = df[df["field_type"].isin(["price", "write_in_price"])]
    df = df[~df["true_value"].isin(["", "BLANK"])]
    glyphs = []
    for group_id, row in enumerate(df.itertuples(index=False)):
        true_value = row.true_value.strip()
        if not true_value or not all(ch.isdigit() or ch in ".," for ch in true_value):
            print(f"  [skip] non-numeric true_value {true_value!r} for {row.crop_path}")
            continue
        if not os.path.exists(row.crop_path):
            print(f"  [skip] missing crop file: {row.crop_path}")
            continue
        digit_chars = [ch for ch in true_value if ch.isdigit()]
        gray = np.array(Image.open(row.crop_path).convert("L"))
        comps, binary = segment_digits(gray)
        digit_comps = [c for c in comps if c["type"] == "digit"]
        if len(digit_comps) != len(digit_chars):
            print(f"  [skip] segmentation found {len(digit_comps)} digit(s) but true_value "
                  f"{true_value!r} has {len(digit_chars)} -- can't safely align, for {row.crop_path}")
            continue
        for comp, ch in zip(digit_comps, digit_chars):
            glyphs.append((group_id, glyph_square(binary, comp), ch))
    return glyphs


def leave_one_price_out_eval(base_X, base_y, glyphs, n_aug, rng):
    """Honest out-of-sample per-digit accuracy: for each real price string,
    train on the base set + every OTHER real price's (augmented) glyphs, and
    test on this one's un-augmented glyphs. Returns (baseline_acc, finetuned_acc)
    -- baseline never sees any real glyphs, finetuned sees all but the held-out
    price -- or (None, None) if there are no real glyphs to evaluate on."""
    group_ids = sorted(set(g for g, _, _ in glyphs))
    if not group_ids:
        return None, None
    base_correct, ft_correct, total = 0, 0, 0
    for holdout in group_ids:
        train = [(sq, ch) for g, sq, ch in glyphs if g != holdout]
        test = [(sq, ch) for g, sq, ch in glyphs if g == holdout]

        clf_base = SVC(gamma=0.001, probability=True)
        clf_base.fit(base_X, base_y)

        Xreal, yreal = [], []
        for sq, ch in train:
            for variant in [sq] + augment(sq, n_aug, rng):
                Xreal.append(square_to_8x8(variant).reshape(-1))
                yreal.append(ch)
        if Xreal:
            Xft = np.vstack([base_X, np.array(Xreal)])
            yft = np.concatenate([base_y, np.array(yreal)])
        else:
            Xft, yft = base_X, base_y
        clf_ft = SVC(gamma=0.001, probability=True)
        clf_ft.fit(Xft, yft)

        for sq, true_ch in test:
            feat = square_to_8x8(sq).reshape(1, -1)
            total += 1
            base_correct += int(clf_base.predict(feat)[0] == true_ch)
            ft_correct += int(clf_ft.predict(feat)[0] == true_ch)
    return base_correct / total, ft_correct / total


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    *label_csvs, out_model_path = sys.argv[1:]

    df = load_labels(label_csvs)
    glyphs = extract_real_glyphs(df)
    print(f"Loaded {len(df)} price labels from {len(label_csvs)} file(s); "
          f"{len(glyphs)} usable real digit glyphs from "
          f"{len(set(g for g, _, _ in glyphs))} price string(s)")

    d = load_digits()
    base_X = d.images.reshape(len(d.images), -1)
    base_y = d.target.astype(str)
    rng = np.random.default_rng(0)

    baseline_acc, finetuned_acc = leave_one_price_out_eval(base_X, base_y, glyphs, N_AUG, rng)
    if baseline_acc is None:
        print("\nNo usable real digit examples yet -- shipping the base (scikit-learn digits "
              "only) classifier. Accuracy on YOUR handwriting is unknown until you --ingest "
              "some corrected prices and re-run this.")
    else:
        print(f"\nLeave-one-price-out per-digit accuracy on your real examples:")
        print(f"  base (scikit-learn digits only): {baseline_acc:.3f}")
        print(f"  fine-tuned (+ your examples):    {finetuned_acc:.3f}")
        if len(glyphs) < 50:
            print(f"  (only {len(glyphs)} real digit glyphs -- treat these numbers as a rough "
                  f"signal, not a guarantee; they should improve as more real prices are "
                  f"--ingest'd and this is re-run)")

    # Final shipped model: base set + ALL real glyphs (augmented), no holdout.
    Xreal, yreal = [], []
    for _group, sq, ch in glyphs:
        for variant in [sq] + augment(sq, N_AUG, rng):
            Xreal.append(square_to_8x8(variant).reshape(-1))
            yreal.append(ch)
    if Xreal:
        X = np.vstack([base_X, np.array(Xreal)])
        y = np.concatenate([base_y, np.array(yreal)])
    else:
        X, y = base_X, base_y
    pipeline = SVC(gamma=0.001, probability=True)
    pipeline.fit(X, y)

    os.makedirs(os.path.dirname(out_model_path) or ".", exist_ok=True)
    bundle = {
        "pipeline": pipeline,
        "n_base_examples": len(base_y),
        "n_real_examples": len(glyphs),
        "baseline_accuracy": round(baseline_acc, 3) if baseline_acc is not None else None,
        "finetuned_accuracy": round(finetuned_acc, 3) if finetuned_acc is not None else None,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source_files": label_csvs,
    }
    joblib.dump(bundle, out_model_path)
    print(f"\nWrote {out_model_path}")
    print(f"Use it with: python3 extract_paper_form.1.5.py ... --digit-model {out_model_path}")


if __name__ == "__main__":
    main()
