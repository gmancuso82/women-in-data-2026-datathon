"""
v1.5 changes from extract_paper_form.1.4.py:

  Price OCR can now optionally use a trained handwritten-digit classifier
  instead of tesseract -- the price-side equivalent of v1.4's checkbox
  classifier. Pass --digit-model <path-to-.pkl> (trained by
  train_digit_classifier.1.0.py) to any extract or --review command; omit it
  and price OCR is unchanged (tesseract), so this is fully opt-in.

  Mechanism: each price crop is segmented into individual ink components via
  connected-component analysis (segment_digits) -- the same crop-inset code
  path as before finds the box, this just replaces what happens to the pixels
  inside it. Components much shorter than the row's typical digit height are
  treated as a decimal point; everything else is resized to 8x8 and classified
  digit-by-digit, then reassembled left to right. A digit predicted with low
  confidence sets needs_review=True, same idea as the checkbox classifier's
  confidence flag.

  This is a harder problem than the checkbox classifier and the honest
  numbers say so: trained on scikit-learn's built-in handwritten-digit
  dataset (no network needed) plus whatever real corrected examples exist in
  price_labels.csv, per-digit accuracy on a handful of real examples was
  measured (via train_digit_classifier.1.0.py's leave-one-out report) at
  roughly 30-45% -- a real improvement over tesseract on this same
  handwriting (tesseract got essentially none of those digits right), but
  still something to double-check, not trust blindly. It should keep
  improving as --ingest accumulates more real corrected prices and the
  classifier is retrained on them.

  This does not touch write-in item name recognition (arbitrary handwritten
  words) -- that needs a much larger sequence model than a per-character
  classifier can provide, and isn't part of this version.

v1.4 changes from extract_paper_form.1.3.py:

  Checkbox fill detection can now optionally use a trained classifier instead
  of the fixed darkness/angle-cluster thresholds -- the other end of the
  feedback loop that --ingest was building labeled data for. Pass
  --model <path-to-.pkl> (trained by train_checkbox_classifier.1.0.py from
  labels/checkbox_labels.csv) to any extract or --review command; omit it and
  behavior is identical to v1.3 (the fixed thresholds), so this is fully
  opt-in and backward compatible. When a model is used, a low-confidence
  prediction (below ML_CONFIDENCE_THRESHOLD) sets needs_review=True even if
  the box was predicted marked, so uncertain calls still surface to a human
  instead of silently trusting a shaky prediction.

  This only ever replaces the checkbox marked/blank decision. Price and
  header OCR are unchanged -- retraining those (real handwriting/digit
  recognition) is a materially bigger undertaking than this small classifier
  and isn't part of this version.

v1.3 changes from extract_paper_form.1.2.py:

  --review now also accepts --batch, so a whole folder of scans can be turned
  into review manifests/crops in one command, the same way plain extraction
  already could. One manifest CSV + one crop subfolder is written per PDF,
  all under the same output directory, ready for build_review_tool.1.2.py
  (which now accepts that whole directory and builds one combined review
  page covering every form in the batch).

  Constraint carried over unchanged: one --batch run uses ONE fieldmap/schema
  pair for every PDF in the folder, so a folder must be single-country. Mixed
  NGA/COL scans need two separate runs (into two subfolders, or two --batch
  calls with different output basenames/dirs).

v1.2 changes from extract_paper_form.1.1.py:

  Replaces the earlier idea of fitting ONE global affine correction per photo
  (which needed a different fit for each of two real scans we tried -- 0.859
  vertical scale for the first, ~0.92 for the second -- so it can't be a fixed
  constant, and fitting it required a person to manually identify known-marked
  boxes each time) with something that needs no manual step at all: checkboxes
  and price boxes are PRINTED as closed rectangles, so their real positions can
  be found directly in the scanned image via contour detection, independent of
  whatever scale/crop distortion that particular photo has. Header and write-in
  fields (just a printed underline, not a closed box) are located the same way
  via a row-darkness scan for the underline itself.

  Mechanism: for each page, detect ALL checkbox-shaped contours in the
  checkbox column and ALL price-box-shaped contours in the price column, once,
  then assign them 1:1 in top-to-bottom order to the fieldmap's items (whose
  order on the page is already fixed and known from how the form was built).
  This only works if the detected count matches the expected count for that
  page -- when it doesn't (a smudge created an extra contour, a very faint
  print dropped one), this falls back to the old fixed pt_bbox_to_px position
  for that page/column and flags every affected row for review, rather than
  silently mis-assigning rows.

Usage:
    python3 extract_paper_form.1.5.py <pdf_path> <fieldmap.json> <schema.json> <output_basename> [--model <checkbox_model.pkl>] [--digit-model <digit_model.pkl>]
    python3 extract_paper_form.1.5.py --batch <folder_of_pdfs> <fieldmap.json> <schema.json> <output_basename> [--model ...] [--digit-model ...]
    python3 extract_paper_form.1.5.py --review <pdf_path> <fieldmap.json> <schema.json> <out_dir> [--model ...] [--digit-model ...]
    python3 extract_paper_form.1.5.py --review --batch <folder_of_pdfs> <fieldmap.json> <schema.json> <out_dir> [--model ...] [--digit-model ...]
    python3 extract_paper_form.1.5.py --ingest <corrected_manifest.csv> <labels_dir>
"""

import sys
import os
import glob
import json
import re
import numpy as np
import pandas as pd
import pytesseract
import cv2
import joblib
from PIL import Image
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4

DPI = 300
PAGE_H_PTS = A4[1]
CHECKBOX_DARK_FRACTION = 0.15
STAR_MIN_DARK_FRACTION = 0.06
STAR_MIN_ANGLE_CLUSTERS = 2
ML_CONFIDENCE_THRESHOLD = 0.75  # below this, flag for review even if predicted "marked"
DIGIT_ML_CONFIDENCE_THRESHOLD = 0.6  # below this for ANY digit in a price, flag for review
INSET_PX = 2
CHECKBOX_INSET_PX = 12  # auto-located boxes hug the printed border tightly (they ARE its
# contour), so the default inset leaves border ink in the crop -- enough on its own to look
# like a multi-stroke "star" to the stroke-angle detector. A wider inset here is safe: it
# only needs to clear the border's own ink, and real marks are drawn well inside it.
PRICE_INSET_PX = 10  # same border-hugging issue affects price OCR: tesseract reliably
# returns nothing at all when the box's own border is in the crop (confirmed empirically);
# a real fix for handwritten-digit accuracy itself is a separate, harder problem (see below).

BOX_SEARCH_MARGIN_X = 180   # generous: real scans have shown ~130-140px horizontal shift
BOX_SEARCH_MARGIN_Y = 150   # per-end padding on top of the item block's own vertical extent
BOX_SIZE_TOL = 0.5          # real boxes have come in ~8-14% smaller than predicted; allow more


def pt_bbox_to_px(bbox_pts, dpi=DPI, page_h_pts=PAGE_H_PTS):
    scale = dpi / 72.0
    x0, y0, x1, y1 = bbox_pts
    return (x0 * scale, (page_h_pts - y1) * scale, x1 * scale, (page_h_pts - y0) * scale)


def crop(img, bbox_px, inset=INSET_PX):
    x0, y0, x1, y1 = bbox_px
    x0, y0, x1, y1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    return img.crop((max(0, x0), max(0, y0), x1, y1))


# --- geometry auto-location -----------------------------------------------

def _find_rect_contours(gray, x0, x1, y0, y1, expect_w, expect_h, aspect_range, size_tol=BOX_SIZE_TOL):
    H, W = gray.shape
    x0, x1 = max(0, int(x0)), min(W, int(x1))
    y0, y1 = max(0, int(y0)), min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return []
    col = gray[y0:y1, x0:x1]
    _, binary = cv2.threshold(col, 190, 255, cv2.THRESH_BINARY_INV)
    binary = cv2.dilate(binary, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for cnt in contours:
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if not (expect_w * (1 - size_tol) < bw < expect_w * (1 + size_tol)):
            continue
        if not (expect_h * (1 - size_tol) < bh < expect_h * (1 + size_tol)):
            continue
        if not (aspect_range[0] < bw / bh < aspect_range[1]):
            continue
        candidates.append((x0 + bx, y0 + by, x0 + bx + bw, y0 + by + bh))
    candidates.sort(key=lambda b: (b[1] + b[3]) / 2)

    deduped = []
    for c in candidates:
        ccy = (c[1] + c[3]) / 2
        if deduped and abs(ccy - (deduped[-1][1] + deduped[-1][3]) / 2) < expect_h * 0.3:
            prev = deduped[-1]  # same box's inner/outer stroke contour -- keep the larger
            if (c[2] - c[0]) * (c[3] - c[1]) > (prev[2] - prev[0]) * (prev[3] - prev[1]):
                deduped[-1] = c
            continue
        deduped.append(c)
    return deduped


def locate_boxes(gray, expected_bboxes_pts, aspect_range, margin_x=BOX_SEARCH_MARGIN_X, margin_y=BOX_SEARCH_MARGIN_Y):
    """expected_bboxes_pts: ordered list of PDF-point bboxes for one page/column
    (already in the fieldmap's draw order). Returns (located_bboxes_px, ok) --
    ok is False if the detected count didn't match, in which case
    located_bboxes_px falls back to the naive pt_bbox_to_px prediction."""
    predicted = [pt_bbox_to_px(b) for b in expected_bboxes_pts]
    if not predicted:
        return [], True
    xs0 = min(p[0] for p in predicted) - margin_x
    xs1 = max(p[2] for p in predicted) + margin_x
    ys0 = min(p[1] for p in predicted) - margin_y
    ys1 = max(p[3] for p in predicted) + margin_y
    expect_w = np.median([p[2] - p[0] for p in predicted])
    expect_h = np.median([p[3] - p[1] for p in predicted])
    found = _find_rect_contours(gray, xs0, xs1, ys0, ys1, expect_w, expect_h, aspect_range)
    if len(found) == len(predicted):
        return found, True
    return predicted, False


def locate_underlines(gray, expected_bboxes_pts, margin_x=60, margin_y=BOX_SEARCH_MARGIN_Y, min_dark_run_frac=0.5):
    """Header/write-in fields have no closed box -- just a printed underline.
    Detect each as the darkest, longest near-horizontal run of pixels within
    the field's x-range, and rebuild the bbox around it at the field's
    original (predicted) height so the OCR crop still spans the writing area
    above the line, not just the line itself."""
    predicted = [pt_bbox_to_px(b) for b in expected_bboxes_pts]
    if not predicted:
        return [], True
    H, W = gray.shape
    x0 = max(0, int(min(p[0] for p in predicted) - margin_x))
    x1 = min(W, int(max(p[2] for p in predicted) + margin_x))
    y0 = max(0, int(min(p[1] for p in predicted) - margin_y))
    y1 = min(H, int(max(p[3] for p in predicted) + margin_y))
    box_h = np.median([p[3] - p[1] for p in predicted])
    box_w = np.median([p[2] - p[0] for p in predicted])
    strip = gray[y0:y1, x0:x1]
    if strip.size == 0:
        return predicted, False
    dark = (strip < 140).sum(axis=1)  # dark-pixel count per row
    min_run = min_dark_run_frac * box_w
    line_rows = [i for i, count in enumerate(dark) if count > min_run]
    # cluster consecutive rows into single line detections
    lines = []
    for r in line_rows:
        if lines and r - lines[-1][-1] <= 3:
            lines[-1].append(r)
        else:
            lines.append([r])
    line_ys = sorted(y0 + int(np.mean(cluster)) for cluster in lines)
    if len(line_ys) != len(predicted):
        return predicted, False
    found = [(p[0], ly - box_h, p[2], ly) for p, ly in zip(predicted, line_ys)]
    return found, True


# --- fill / OCR primitives (unchanged from v1.1) --------------------------

def _dark_fraction(gray):
    if gray.size == 0:
        return 0.0
    return float((gray < 140).sum()) / gray.size


def _stroke_angle_clusters(gray, min_len_frac=0.35, max_gap_frac=0.15, bin_deg=20,
                            canny_lo=40, canny_hi=120, hough_thresh=8):
    h, w = gray.shape
    if h == 0 or w == 0:
        return 0
    edges = cv2.Canny(gray, canny_lo, canny_hi)
    min_len = min_len_frac * min(w, h)
    max_gap = max_gap_frac * min(w, h)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=hough_thresh,
                             minLineLength=min_len, maxLineGap=max_gap)
    if lines is None:
        return 0
    n_bins = max(1, 180 // bin_deg)
    bins = set()
    for x1, y1, x2, y2 in lines[:, 0]:
        ang = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
        bins.add(int(ang // bin_deg) % n_bins)
    return len(bins)


def is_checkbox_filled_check(img_crop, threshold=CHECKBOX_DARK_FRACTION):
    gray = np.array(img_crop.convert("L"))
    return _dark_fraction(gray) > threshold


def is_checkbox_filled_star(img_crop, min_dark_fraction=STAR_MIN_DARK_FRACTION,
                             min_clusters=STAR_MIN_ANGLE_CLUSTERS):
    gray = np.array(img_crop.convert("L"))
    if gray.size == 0:
        return False
    if _dark_fraction(gray) <= min_dark_fraction:
        return False
    return _stroke_angle_clusters(gray) >= min_clusters


def is_checkbox_filled(img_crop, mark_style="check"):
    if mark_style == "star":
        return is_checkbox_filled_star(img_crop)
    return is_checkbox_filled_check(img_crop)


# --- optional trained classifier, replacing the fixed thresholds above ----
# Same two engineered features the thresholds already used (dark_fraction,
# stroke_angle_clusters) -- see train_checkbox_classifier.1.0.py. Loading a
# model is an explicit opt-in (--model <path>); with none given, behavior is
# identical to v1.3.

def load_checkbox_model(path):
    if not path:
        return None
    bundle = joblib.load(path)
    print(f"[model] loaded checkbox classifier from {path} "
          f"(trained on {bundle.get('n_samples', '?')} labeled examples, "
          f"cv_accuracy={bundle.get('cv_accuracy', '?')})")
    return bundle


def is_checkbox_filled_ml(img_crop, model_bundle):
    gray = np.array(img_crop.convert("L"))
    if gray.size == 0:
        return False, 1.0
    feats = [[_dark_fraction(gray), _stroke_angle_clusters(gray)]]
    pipeline = model_bundle["pipeline"]
    proba = pipeline.predict_proba(feats)[0]
    classes = list(pipeline.classes_)
    p_true = proba[classes.index(True)]
    return bool(p_true >= 0.5), float(max(p_true, 1 - p_true))


def has_handwriting(img_crop, threshold=0.02):
    w, h = img_crop.size
    if w == 0 or h == 0:
        return False
    upper = img_crop.crop((0, 0, w, int(h * 0.65)))
    gray = np.array(upper.convert("L"))
    if gray.size == 0:
        return False
    return _dark_fraction(gray) > threshold


def _upscale(img_crop, factor=3):
    w, h = img_crop.size
    if w == 0 or h == 0:
        return img_crop
    return img_crop.resize((w * factor, h * factor), Image.LANCZOS)


def ocr_price(img_crop):
    up = _upscale(img_crop)
    raw = pytesseract.image_to_string(
        up, config="--psm 7 -c tessedit_char_whitelist=0123456789,."
    ).strip()
    digits = re.sub(r"[^0-9.]", "", raw.replace(",", ""))
    try:
        price = float(digits) if digits else None
    except ValueError:
        price = None
    return raw, price


def ocr_text(img_crop):
    up = _upscale(img_crop)
    return pytesseract.image_to_string(up, config="--psm 7").strip()


# --- optional trained digit classifier, replacing tesseract for price OCR --
# See train_digit_classifier.1.0.py. Loading a model is opt-in (--digit-model
# <path>); with none given, ocr_price (tesseract) is unchanged from v1.4.

DOT_HEIGHT_FRAC = 0.45  # a component shorter than this fraction of the row's
# typical digit height is a decimal point, not a digit -- matches the visible
# gap between a full digit's height and a period's in every real example seen
# so far (real digits ~35-55px tall at 300dpi crops, the period ~6-10px).
MIN_COMPONENT_AREA = 6  # drops single-pixel scan noise without dropping a
# genuine (small) decimal point


def segment_digits(gray, min_area=MIN_COMPONENT_AREA, dot_height_frac=DOT_HEIGHT_FRAC):
    """Splits a price crop into left-to-right ink components and tags each as
    a 'digit' or a 'dot' (decimal point), by connected-component analysis --
    the same kind of contour-based approach used elsewhere in this file for
    locating printed boxes, just applied to handwritten ink instead. Returns
    (components, binary_mask); components is [] for a blank/empty crop."""
    if gray.size == 0:
        return [], np.zeros((0, 0), dtype=np.uint8)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, _labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    comps = []
    for i in range(1, n):  # label 0 is the background
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        comps.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area)})
    comps.sort(key=lambda c: c["x"])
    if not comps:
        return [], binary
    biggest = max(c["area"] for c in comps)
    reference = [c for c in comps if c["area"] >= 0.15 * biggest]
    median_h = float(np.median([c["h"] for c in reference]))
    for c in comps:
        c["type"] = "dot" if c["h"] < dot_height_frac * median_h else "digit"
    return comps, binary


def glyph_square(binary, comp, pad=2):
    """Crops one component out of the binary mask, padded to a square (so the
    8x8 resize below doesn't distort aspect ratio)."""
    x, y, w, h = comp["x"], comp["y"], comp["w"], comp["h"]
    H, W = binary.shape
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    glyph = binary[y0:y1, x0:x1]
    gh, gw = glyph.shape
    side = max(gh, gw, 1)
    square = np.zeros((side, side), dtype=np.uint8)
    oy, ox = (side - gh) // 2, (side - gw) // 2
    square[oy:oy + gh, ox:ox + gw] = glyph
    return square


def square_to_8x8(square):
    """Matches sklearn's load_digits format: 8x8, ink intensity 0-16 (higher
    = darker ink), so a classifier trained on that built-in dataset can be
    applied directly to a real crop's glyphs."""
    small = cv2.resize(square, (8, 8), interpolation=cv2.INTER_AREA)
    return (small.astype(np.float64) / 255.0) * 16.0


def load_digit_model(path):
    if not path:
        return None
    bundle = joblib.load(path)
    print(f"[digit-model] loaded from {path} (base=sklearn digits + "
          f"{bundle.get('n_real_examples', 0)} real examples, "
          f"leave-one-out per-digit accuracy={bundle.get('finetuned_accuracy', '?')})")
    return bundle


def ocr_price_ml(img_crop, model_bundle):
    """Digit-classifier equivalent of ocr_price: segment, classify each glyph,
    reassemble. Returns (raw_text, price_or_None, min_confidence_or_None) --
    min_confidence is None for a blank crop (nothing to be confident about)."""
    gray = np.array(img_crop.convert("L"))
    comps, binary = segment_digits(gray)
    if not comps:
        return "", None, None
    clf = model_bundle["pipeline"]
    chars, confidences = [], []
    for c in comps:
        if c["type"] == "dot":
            chars.append(".")
            continue
        feat = square_to_8x8(glyph_square(binary, c)).reshape(1, -1)
        proba = clf.predict_proba(feat)[0]
        best_i = int(np.argmax(proba))
        chars.append(str(clf.classes_[best_i]))
        confidences.append(float(proba[best_i]))
    raw = "".join(chars)
    try:
        price = float(raw) if raw and raw != "." else None
    except ValueError:
        price = None
    min_confidence = min(confidences) if confidences else None
    return raw, price, min_confidence


def ocr_price_dispatch(img_crop, digit_model):
    """Picks tesseract or the trained digit classifier depending on whether a
    digit_model was loaded, and always returns (raw_text, price, needs_review)
    so callers don't need their own branch on which backend ran."""
    if digit_model is not None:
        raw, price, min_confidence = ocr_price_ml(img_crop, digit_model)
        low_confidence = min_confidence is not None and min_confidence < DIGIT_ML_CONFIDENCE_THRESHOLD
        return raw, price, low_confidence
    raw, price = ocr_price(img_crop)
    return raw, price, False


def pdf_to_page_images(pdf_path, dpi=DPI):
    return convert_from_path(pdf_path, dpi=dpi)


def build_item_lookup(schema, country):
    lookup = {}
    group_labels = {g["id"]: g["label"] for g in schema["food_groups"]}
    item_lists = schema["countries"][country]["item_lists"]
    for group_id, items in item_lists.items():
        for item in items:
            lookup[(group_id, item["item_id"])] = {
                "item_label": item["label"],
                "unit": item["default_unit"],
                "food_group_label": group_labels.get(group_id, group_id),
            }
    return lookup


def extract_from_images(page_images, fieldmap, schema, source_channel="paper_scan",
                         checkbox_model=None, digit_model=None):
    country = fieldmap["country"]
    mark_style = fieldmap.get("mark_style", "check")
    item_lookup = build_item_lookup(schema, country)
    n_pages = len(page_images)

    submission = {"country": country, "currency": schema["countries"][country]["currency"],
                  "source_channel": source_channel}
    line_items = []

    for page_num in range(1, n_pages + 1):
        page_img = page_images[page_num - 1]
        gray = np.array(page_img.convert("L"))

        # -- header fields: column-wise underline detection --------------
        hdr_fields = [f for f in fieldmap["header_fields"] if f["page"] == page_num]
        if hdr_fields:
            xs = sorted({f["bbox"][0] for f in hdr_fields})
            # group header fields into their print columns (x may vary slightly per row; cluster)
            columns = []
            for x in xs:
                if columns and abs(x - columns[-1][0]) < 5:
                    continue
                columns.append([x])
            col_assign = {i: [] for i in range(len(columns))}
            for f in hdr_fields:
                ci = min(range(len(columns)), key=lambda i: abs(f["bbox"][0] - columns[i][0]))
                col_assign[ci].append(f)
            for ci, fields in col_assign.items():
                fields.sort(key=lambda f: f["bbox"][1], reverse=True)  # PDF y grows upward; top row = largest y
                bboxes_pts = [f["bbox"] for f in fields]
                located, ok = locate_underlines(gray, bboxes_pts)
                for f, bbox_px in zip(fields, located):
                    field_crop = crop(page_img, bbox_px)
                    submission[f["field_id"]] = ocr_text(field_crop) if has_handwriting(field_crop) else ""

        # -- item checkboxes + prices: sequential contour detection -------
        item_fields = [f for f in fieldmap["item_fields"] if f["page"] == page_num]
        write_in_fields = [f for f in fieldmap["write_in_fields"] if f["page"] == page_num]

        if item_fields:
            cb_bboxes_pts = [f["checkbox_bbox"] for f in item_fields]
            cb_located, cb_ok = locate_boxes(gray, cb_bboxes_pts, aspect_range=(0.7, 1.4))
            if not cb_ok:
                print(f"  [warn] page {page_num}: checkbox auto-locate count mismatch, "
                      f"falling back to predicted geometry for this page")
        else:
            cb_located, cb_ok = [], True

        # price boxes are shared by item rows and write-in rows, interleaved
        # in the same draw order they were laid out on the page
        price_slots = sorted(item_fields + write_in_fields, key=lambda f: f["price_bbox"][1], reverse=True)
        price_bboxes_pts = [f["price_bbox"] for f in price_slots]
        price_located, price_ok = locate_boxes(gray, price_bboxes_pts, aspect_range=(2.0, 6.0))
        if not price_ok:
            print(f"  [warn] page {page_num}: price-box auto-locate count mismatch, "
                  f"falling back to predicted geometry for this page")
        price_by_slot = {id(f): bbox for f, bbox in zip(price_slots, price_located)}

        for f, cb_px in zip(item_fields, cb_located):
            cb_inset = CHECKBOX_INSET_PX if cb_ok else INSET_PX
            cb_crop = crop(page_img, cb_px, inset=cb_inset)
            if checkbox_model is not None and mark_style == "star":
                filled, confidence = is_checkbox_filled_ml(cb_crop, checkbox_model)
            else:
                filled, confidence = is_checkbox_filled(cb_crop, mark_style), None
            if not filled:
                continue
            price_px = price_by_slot[id(f)]
            price_inset = PRICE_INSET_PX if price_ok else INSET_PX
            raw_price, price, price_low_conf = ocr_price_dispatch(
                crop(page_img, price_px, inset=price_inset), digit_model)
            meta = item_lookup.get((f["food_group_id"], f["item_id"]), {})
            low_confidence = (confidence is not None and confidence < ML_CONFIDENCE_THRESHOLD) or price_low_conf
            line_items.append({
                "food_group_id": f["food_group_id"],
                "food_group_label": meta.get("food_group_label"),
                "item_id": f["item_id"],
                "item_label": meta.get("item_label"),
                "unit": meta.get("unit"),
                "price": price,
                "raw_price_text": raw_price,
                "is_write_in": False,
                "needs_review": price is None or not cb_ok or low_confidence,
            })

        for f in write_in_fields:
            name_px = pt_bbox_to_px(f["item_name_bbox"])
            name_crop = crop(page_img, name_px)
            if not has_handwriting(name_crop):
                continue
            item_text = ocr_text(name_crop)
            if len(re.sub(r"[^A-Za-z]", "", item_text)) < 2:
                continue
            unit_px = pt_bbox_to_px(f["unit_bbox"])
            unit_text = ocr_text(crop(page_img, unit_px))
            price_px = price_by_slot[id(f)]
            price_inset = PRICE_INSET_PX if price_ok else INSET_PX
            raw_price, price, _price_low_conf = ocr_price_dispatch(
                crop(page_img, price_px, inset=price_inset), digit_model)
            line_items.append({
                "food_group_id": f["food_group_id"],
                "food_group_label": None,
                "item_id": None,
                "item_label": item_text,
                "unit": unit_text,
                "price": price,
                "raw_price_text": raw_price,
                "is_write_in": True,
                "needs_review": True,
            })

    return submission, line_items


def extract_from_pdf(pdf_path, fieldmap, schema, checkbox_model=None, digit_model=None):
    page_images = pdf_to_page_images(pdf_path)
    return extract_from_images(page_images, fieldmap, schema,
                                checkbox_model=checkbox_model, digit_model=digit_model)


def process_one(pdf_path, fieldmap, schema, form_id, checkbox_model=None, digit_model=None):
    submission, line_items = extract_from_pdf(pdf_path, fieldmap, schema,
                                               checkbox_model=checkbox_model, digit_model=digit_model)
    submission["form_id"] = form_id
    for li in line_items:
        li["form_id"] = form_id
    return submission, line_items


# --- review / correction-feedback-loop support (carried over from v1.1,
# updated to save the same auto-located crops the extractor actually used) ---

def export_review_crops(pdf_path, fieldmap, schema, form_id, out_dir, checkbox_model=None, digit_model=None):
    country = fieldmap["country"]
    mark_style = fieldmap.get("mark_style", "check")
    item_lookup = build_item_lookup(schema, country)
    crop_dir = os.path.join(out_dir, form_id)
    os.makedirs(crop_dir, exist_ok=True)
    page_images = pdf_to_page_images(pdf_path)

    rows = []

    def save(field_type, food_group_id, item_id, page_img, bbox_px, extracted_value, tag, inset=INSET_PX):
        img_crop = crop(page_img, bbox_px, inset=inset)
        crop_path = os.path.join(crop_dir, f"{tag}.png")
        img_crop.save(crop_path)
        rows.append({
            "form_id": form_id, "field_type": field_type,
            "food_group_id": food_group_id or "", "item_id": item_id or "",
            "crop_path": crop_path, "extracted_value": extracted_value,
            "operator_value": "",
        })

    for page_num in range(1, len(page_images) + 1):
        page_img = page_images[page_num - 1]
        gray = np.array(page_img.convert("L"))

        hdr_fields = [f for f in fieldmap["header_fields"] if f["page"] == page_num]
        if hdr_fields:
            located, _ = locate_underlines(gray, [f["bbox"] for f in hdr_fields])
            for f, bbox_px in zip(hdr_fields, located):
                field_crop = crop(page_img, bbox_px)
                extracted = ocr_text(field_crop) if has_handwriting(field_crop) else ""
                save("header", None, f["field_id"], page_img, bbox_px, extracted, f"header_{f['field_id']}")

        item_fields = [f for f in fieldmap["item_fields"] if f["page"] == page_num]
        write_in_fields = [f for f in fieldmap["write_in_fields"] if f["page"] == page_num]
        cb_located, cb_ok = locate_boxes(gray, [f["checkbox_bbox"] for f in item_fields],
                                          aspect_range=(0.7, 1.4)) if item_fields else ([], True)
        price_slots = sorted(item_fields + write_in_fields, key=lambda f: f["price_bbox"][1], reverse=True)
        price_located, price_ok = locate_boxes(gray, [f["price_bbox"] for f in price_slots],
                                                aspect_range=(2.0, 6.0))
        price_by_slot = {id(f): bbox for f, bbox in zip(price_slots, price_located)}

        for f, cb_px in zip(item_fields, cb_located):
            cb_inset = CHECKBOX_INSET_PX if cb_ok else INSET_PX
            cb_crop = crop(page_img, cb_px, inset=cb_inset)
            if checkbox_model is not None and mark_style == "star":
                filled, _confidence = is_checkbox_filled_ml(cb_crop, checkbox_model)
            else:
                filled = is_checkbox_filled(cb_crop, mark_style)
            save("checkbox", f["food_group_id"], f["item_id"], page_img, cb_px, filled,
                 f"checkbox_{f['food_group_id']}_{f['item_id']}", inset=cb_inset)
            price_px = price_by_slot[id(f)]
            price_inset = PRICE_INSET_PX if price_ok else INSET_PX
            raw_price, price, _price_low_conf = ocr_price_dispatch(
                crop(page_img, price_px, inset=price_inset), digit_model)
            save("price", f["food_group_id"], f["item_id"], page_img, price_px, price,
                 f"price_{f['food_group_id']}_{f['item_id']}", inset=price_inset)

        for f in write_in_fields:
            for part in ("item_name_bbox", "unit_bbox"):
                bbox_px = pt_bbox_to_px(f[part])
                tag = f"writein_{f['food_group_id']}_{f['slot_index']}_{part.replace('_bbox', '')}"
                save(f"write_in_{part.replace('_bbox', '')}", f["food_group_id"], None,
                     page_img, bbox_px, "", tag)
            price_px = price_by_slot[id(f)]
            price_inset = PRICE_INSET_PX if price_ok else INSET_PX
            save("write_in_price", f["food_group_id"], None, page_img, price_px, "",
                 f"writein_{f['food_group_id']}_{f['slot_index']}_price", inset=price_inset)

    manifest_path = os.path.join(out_dir, f"review_manifest_{form_id}.csv")
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    print(f"Wrote {len(rows)} review crops to {crop_dir}/ and manifest {manifest_path}")
    return manifest_path


def ingest_corrections(corrected_manifest_csv, labels_dir):
    os.makedirs(labels_dir, exist_ok=True)
    df = pd.read_csv(corrected_manifest_csv, dtype=str).fillna("")
    reviewed = df[df["operator_value"] != ""]

    families = {
        "checkbox": os.path.join(labels_dir, "checkbox_labels.csv"),
        "price": os.path.join(labels_dir, "price_labels.csv"),
        "write_in_price": os.path.join(labels_dir, "price_labels.csv"),
    }
    families["header"] = families["write_in_item_name"] = families["write_in_unit"] = \
        os.path.join(labels_dir, "text_labels.csv")

    n_written = 0
    for out_path in set(families.values()):
        field_types = [k for k, v in families.items() if v == out_path]
        subset = reviewed[reviewed["field_type"].isin(field_types)]
        if subset.empty:
            continue
        existing = pd.read_csv(out_path) if os.path.exists(out_path) else pd.DataFrame(
            columns=["crop_path", "field_type", "form_id", "food_group_id", "item_id",
                     "extracted_value", "true_value"])
        existing = existing[~existing["crop_path"].isin(subset["crop_path"])]
        new_rows = pd.DataFrame({
            "crop_path": subset["crop_path"],
            "field_type": subset["field_type"],
            "form_id": subset["form_id"],
            "food_group_id": subset["food_group_id"],
            "item_id": subset["item_id"],
            "extracted_value": subset["extracted_value"],
            "true_value": subset["operator_value"],
        })
        combined = pd.concat([existing, new_rows], ignore_index=True)
        combined.to_csv(out_path, index=False)
        n_written += len(new_rows)

    print(f"Ingested {n_written} corrected/confirmed labels from {corrected_manifest_csv} into {labels_dir}/")


def main():
    args = sys.argv[1:]

    # --model / --digit-model <path> are accepted anywhere on the command
    # line and pulled out first so they don't disturb the existing positional
    # argument handling below; omitting both reproduces v1.3 behavior exactly.
    def pop_flag(args, flag):
        if flag in args:
            i = args.index(flag)
            return args[i + 1], args[:i] + args[i + 2:]
        return None, args

    model_path, args = pop_flag(args, "--model")
    digit_model_path, args = pop_flag(args, "--digit-model")
    checkbox_model = load_checkbox_model(model_path) if model_path else None
    digit_model = load_digit_model(digit_model_path) if digit_model_path else None

    if args and args[0] == "--review":
        if args[1] == "--batch":
            folder, fieldmap_path, schema_path, out_dir = args[2], args[3], args[4], args[5]
            pdf_paths = sorted(glob.glob(f"{folder}/*.pdf"))
        else:
            pdf_paths = [args[1]]
            fieldmap_path, schema_path, out_dir = args[2], args[3], args[4]
        with open(fieldmap_path) as f:
            fieldmap = json.load(f)
        with open(schema_path) as f:
            schema = json.load(f)
        for i, pdf_path in enumerate(pdf_paths, start=1):
            form_id = pdf_path.split("/")[-1].rsplit(".", 1)[0]
            print(f"[{i}/{len(pdf_paths)}] exporting review crops for {pdf_path} ...")
            export_review_crops(pdf_path, fieldmap, schema, form_id, out_dir,
                                 checkbox_model=checkbox_model, digit_model=digit_model)
        return
    if args and args[0] == "--ingest":
        corrected_manifest_csv, labels_dir = args[1], args[2]
        ingest_corrections(corrected_manifest_csv, labels_dir)
        return
    if args and args[0] == "--batch":
        folder, fieldmap_path, schema_path, out_base = args[1], args[2], args[3], args[4]
        pdf_paths = sorted(glob.glob(f"{folder}/*.pdf"))
    else:
        pdf_paths = [args[0]]
        fieldmap_path, schema_path, out_base = args[1], args[2], args[3]

    with open(fieldmap_path) as f:
        fieldmap = json.load(f)
    with open(schema_path) as f:
        schema = json.load(f)

    all_submissions, all_line_items = [], []
    for i, pdf_path in enumerate(pdf_paths, start=1):
        form_id = pdf_path.split("/")[-1].rsplit(".", 1)[0]
        print(f"[{i}/{len(pdf_paths)}] extracting {pdf_path} ...")
        submission, line_items = process_one(pdf_path, fieldmap, schema, form_id,
                                              checkbox_model=checkbox_model, digit_model=digit_model)
        all_submissions.append(submission)
        all_line_items.extend(line_items)

    pd.DataFrame(all_submissions).to_csv(f"{out_base}_submissions.csv", index=False)
    pd.DataFrame(all_line_items).to_csv(f"{out_base}_line_items.csv", index=False)
    n_review = sum(1 for li in all_line_items if li["needs_review"])
    print(f"Wrote {out_base}_submissions.csv ({len(all_submissions)} forms) and "
          f"{out_base}_line_items.csv ({len(all_line_items)} rows, {n_review} flagged for review)")


if __name__ == "__main__":
    main()
