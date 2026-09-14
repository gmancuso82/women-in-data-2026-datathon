"""
v1.1 changes from extract_paper_form.1.0.py:

  1. Checkbox-fill detection now supports two mark styles, auto-selected from
     the field map's "mark_style" key (fieldmap built by build_paper_form.1.1.py
     says "star"; older 1.0 field maps have no key and fall back to "check"):
       - "check": the original v1.0 darkness-fraction threshold (kept for the
         real NGA scan we already collected under the old check-mark form).
       - "star": a stricter combined check -- minimum ink fraction PLUS at
         least 2 distinct stroke-angle clusters via Hough line detection.
         A star's several crossing strokes are much harder for scan noise
         (paper texture, shadow, compression artifacts) to fake than a single
         darkness threshold, especially now that the box is 8mm instead of
         4mm (roughly 4x the pixels at the same DPI -> much less noise
         relative to a real mark).
     NOTE: this has only been validated on synthetic star fills (test_extract.1.1.py)
     -- exactly like the v1.0 checkbox logic before it was tested on a real
     scan, this needs a real star-marked scan to confirm the thresholds hold
     up, the same way the geometry calibration did.

  2. Review/correction-logging support, for the human-in-the-loop feedback
     loop: export_review_crops() saves every extracted field's source crop
     plus its extracted value to a manifest CSV an operator can open and
     correct; ingest_corrections() folds a corrected manifest back into
     growing, reusable label files (one per field type) that can later train
     a real classifier in place of the fixed thresholds above.

Usage (unchanged from v1.0):
    python3 extract_paper_form.1.1.py <pdf_path> <fieldmap.json> <schema.json> <output_basename>
    python3 extract_paper_form.1.1.py --batch <folder_of_pdfs> <fieldmap.json> <schema.json> <output_basename>

New:
    python3 extract_paper_form.1.1.py --review <pdf_path> <fieldmap.json> <schema.json> <out_dir>
    python3 extract_paper_form.1.1.py --ingest <corrected_manifest.csv> <labels_dir>
"""

import sys
import os
import glob
import json
import re
import csv
import numpy as np
import pandas as pd
import pytesseract
import cv2
from PIL import Image
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4

DPI = 300
PAGE_H_PTS = A4[1]
CHECKBOX_DARK_FRACTION = 0.15   # "check" style threshold, unchanged from v1.0
STAR_MIN_DARK_FRACTION = 0.06   # "star" style: lower floor is fine, since we also require stroke structure
STAR_MIN_ANGLE_CLUSTERS = 2     # distinct stroke directions required to call it a star
INSET_PX = 2


def pt_bbox_to_px(bbox_pts, dpi=DPI, page_h_pts=PAGE_H_PTS):
    scale = dpi / 72.0
    x0, y0, x1, y1 = bbox_pts
    px_x0 = x0 * scale
    px_x1 = x1 * scale
    px_y0 = (page_h_pts - y1) * scale
    px_y1 = (page_h_pts - y0) * scale
    return (px_x0, px_y0, px_x1, px_y1)


def crop(img, bbox_px, inset=INSET_PX):
    x0, y0, x1, y1 = bbox_px
    x0, y0, x1, y1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    return img.crop((max(0, x0), max(0, y0), x1, y1))


def _dark_fraction(gray):
    if gray.size == 0:
        return 0.0
    return float((gray < 140).sum()) / gray.size


def _stroke_angle_clusters(gray, min_len_frac=0.35, max_gap_frac=0.15, bin_deg=20,
                            canny_lo=40, canny_hi=120, hough_thresh=8):
    """Count distinct stroke directions in a box crop via Hough line detection.
    Returns the number of populated angle bins (0-180deg, bin_deg-wide)."""
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
    """v1.0 logic: pure darkness threshold. Kept for field maps built for a
    check-mark form (mark_style == "check" or absent)."""
    gray = np.array(img_crop.convert("L"))
    return _dark_fraction(gray) > threshold


def is_checkbox_filled_star(img_crop, min_dark_fraction=STAR_MIN_DARK_FRACTION,
                             min_clusters=STAR_MIN_ANGLE_CLUSTERS):
    """v1.1 logic for star-marked boxes: require both real ink content AND
    multi-directional stroke structure, so a single noise patch (which rarely
    produces >=2 clean, differently-angled line segments) doesn't pass."""
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


def extract_from_images(page_images, fieldmap, schema, source_channel="paper_scan"):
    country = fieldmap["country"]
    mark_style = fieldmap.get("mark_style", "check")
    item_lookup = build_item_lookup(schema, country)

    submission = {"country": country, "currency": schema["countries"][country]["currency"],
                  "source_channel": source_channel}
    for f in fieldmap["header_fields"]:
        page_img = page_images[f["page"] - 1]
        field_crop = crop(page_img, pt_bbox_to_px(f["bbox"]))
        submission[f["field_id"]] = ocr_text(field_crop) if has_handwriting(field_crop) else ""

    line_items = []
    for f in fieldmap["item_fields"]:
        page_img = page_images[f["page"] - 1]
        checkbox_px = pt_bbox_to_px(f["checkbox_bbox"])
        if not is_checkbox_filled(crop(page_img, checkbox_px), mark_style):
            continue
        price_px = pt_bbox_to_px(f["price_bbox"])
        raw_price, price = ocr_price(crop(page_img, price_px))
        meta = item_lookup.get((f["food_group_id"], f["item_id"]), {})
        line_items.append({
            "food_group_id": f["food_group_id"],
            "food_group_label": meta.get("food_group_label"),
            "item_id": f["item_id"],
            "item_label": meta.get("item_label"),
            "unit": meta.get("unit"),
            "price": price,
            "raw_price_text": raw_price,
            "is_write_in": False,
            "needs_review": price is None,
        })

    for f in fieldmap["write_in_fields"]:
        page_img = page_images[f["page"] - 1]
        name_px = pt_bbox_to_px(f["item_name_bbox"])
        name_crop = crop(page_img, name_px)
        if not has_handwriting(name_crop):
            continue
        item_text = ocr_text(name_crop)
        if len(re.sub(r"[^A-Za-z]", "", item_text)) < 2:
            continue
        unit_px = pt_bbox_to_px(f["unit_bbox"])
        unit_text = ocr_text(crop(page_img, unit_px))
        price_px = pt_bbox_to_px(f["price_bbox"])
        raw_price, price = ocr_price(crop(page_img, price_px))
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


def extract_from_pdf(pdf_path, fieldmap, schema):
    page_images = pdf_to_page_images(pdf_path)
    return extract_from_images(page_images, fieldmap, schema)


def process_one(pdf_path, fieldmap, schema, form_id):
    submission, line_items = extract_from_pdf(pdf_path, fieldmap, schema)
    submission["form_id"] = form_id
    for li in line_items:
        li["form_id"] = form_id
    return submission, line_items


# --- review / correction-feedback-loop support --------------------------------

def export_review_crops(pdf_path, fieldmap, schema, form_id, out_dir):
    """Save every extracted field's source crop + its extracted value to
    out_dir/<form_id>/*.png, and a manifest CSV an operator can open, add an
    'operator_value' column to (for every row, confirming or correcting), and
    hand back to ingest_corrections(). This is the raw material for the
    training-feedback loop: real crops paired with a human-verified label."""
    country = fieldmap["country"]
    mark_style = fieldmap.get("mark_style", "check")
    item_lookup = build_item_lookup(schema, country)
    crop_dir = os.path.join(out_dir, form_id)
    os.makedirs(crop_dir, exist_ok=True)
    page_images = pdf_to_page_images(pdf_path)

    rows = []

    def save(field_type, food_group_id, item_id, page_img, bbox_px, extracted_value, tag):
        img_crop = crop(page_img, bbox_px)
        crop_path = os.path.join(crop_dir, f"{tag}.png")
        img_crop.save(crop_path)
        rows.append({
            "form_id": form_id, "field_type": field_type,
            "food_group_id": food_group_id or "", "item_id": item_id or "",
            "crop_path": crop_path, "extracted_value": extracted_value,
            "operator_value": "",
        })

    for f in fieldmap["header_fields"]:
        page_img = page_images[f["page"] - 1]
        bbox_px = pt_bbox_to_px(f["bbox"])
        field_crop = crop(page_img, bbox_px)
        extracted = ocr_text(field_crop) if has_handwriting(field_crop) else ""
        save("header", None, f["field_id"], page_img, bbox_px, extracted, f"header_{f['field_id']}")

    for f in fieldmap["item_fields"]:
        page_img = page_images[f["page"] - 1]
        cb_px = pt_bbox_to_px(f["checkbox_bbox"])
        filled = is_checkbox_filled(crop(page_img, cb_px), mark_style)
        save("checkbox", f["food_group_id"], f["item_id"], page_img, cb_px, filled,
             f"checkbox_{f['food_group_id']}_{f['item_id']}")
        price_px = pt_bbox_to_px(f["price_bbox"])
        raw_price, price = ocr_price(crop(page_img, price_px))
        save("price", f["food_group_id"], f["item_id"], page_img, price_px, price,
             f"price_{f['food_group_id']}_{f['item_id']}")

    for f in fieldmap["write_in_fields"]:
        page_img = page_images[f["page"] - 1]
        for part in ("item_name_bbox", "unit_bbox", "price_bbox"):
            bbox_px = pt_bbox_to_px(f[part])
            tag = f"writein_{f['food_group_id']}_{f['slot_index']}_{part.replace('_bbox', '')}"
            save(f"write_in_{part.replace('_bbox', '')}", f["food_group_id"], None,
                 page_img, bbox_px, "", tag)

    manifest_path = os.path.join(out_dir, f"review_manifest_{form_id}.csv")
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    print(f"Wrote {len(rows)} review crops to {crop_dir}/ and manifest {manifest_path}")
    return manifest_path


def ingest_corrections(corrected_manifest_csv, labels_dir):
    """Fold an operator-reviewed manifest (operator_value filled in for rows
    they checked) into persistent, append-only label files, one per field
    type family, for later use training a real classifier/OCR model in place
    of the fixed thresholds. De-dupes on crop_path so re-ingesting an updated
    manifest replaces the old label rather than duplicating it."""
    os.makedirs(labels_dir, exist_ok=True)
    df = pd.read_csv(corrected_manifest_csv, dtype=str).fillna("")
    reviewed = df[df["operator_value"] != ""]

    families = {
        "checkbox": os.path.join(labels_dir, "checkbox_labels.csv"),
        "price": os.path.join(labels_dir, "price_labels.csv"),
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
    if args and args[0] == "--review":
        pdf_path, fieldmap_path, schema_path, out_dir = args[1], args[2], args[3], args[4]
        with open(fieldmap_path) as f:
            fieldmap = json.load(f)
        with open(schema_path) as f:
            schema = json.load(f)
        form_id = pdf_path.split("/")[-1].rsplit(".", 1)[0]
        export_review_crops(pdf_path, fieldmap, schema, form_id, out_dir)
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
        submission, line_items = process_one(pdf_path, fieldmap, schema, form_id)
        all_submissions.append(submission)
        all_line_items.extend(line_items)

    pd.DataFrame(all_submissions).to_csv(f"{out_base}_submissions.csv", index=False)
    pd.DataFrame(all_line_items).to_csv(f"{out_base}_line_items.csv", index=False)
    n_review = sum(1 for li in all_line_items if li["needs_review"])
    print(f"Wrote {out_base}_submissions.csv ({len(all_submissions)} forms) and "
          f"{out_base}_line_items.csv ({len(all_line_items)} rows, {n_review} flagged for review)")


if __name__ == "__main__":
    main()
