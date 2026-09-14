"""
Verification harness for extract_paper_form.1.0.py.

Since no real scanned/handwritten form exists yet, this synthesizes a
"filled" version of the blank NGA form by drawing filled checkboxes and
typed prices directly onto the rendered page images at a handful of known
field positions (from the field map), then runs the extraction pipeline
against those images and checks the recovered values against what was
drawn. This validates the coordinate math (PDF points -> pixels) and the
checkbox/OCR logic end to end, independent of real handwriting quality.
"""

import json
import importlib.util
from PIL import ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location("extract_paper_form", "extract_paper_form.1.0.py")
extract_paper_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_paper_form)
pdf_to_page_images = extract_paper_form.pdf_to_page_images
pt_bbox_to_px = extract_paper_form.pt_bbox_to_px
extract_from_images = extract_paper_form.extract_from_images

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)

with open("hoos_cooking_paper_form_NGA.1.0_fieldmap.json") as f:
    fieldmap = json.load(f)
with open("hoos_cooking_form_schema.1.1.json") as f:
    schema = json.load(f)

images = pdf_to_page_images("hoos_cooking_paper_form_NGA.1.0.pdf")
images = [img.copy() for img in images]

# Pick a handful of fixed items across different pages/food groups + one write-in.
EXPECTED_ITEMS = [
    ("starchy_staples", "rice_local", 1250),
    ("starchy_staples", "garri", 630),
    ("vegetables", "tomato", 1370),
    ("fruits", "pineapple", 1130),
    ("animal_source_foods", "beef", 5370),
    ("oils_fats", "palm_oil", 1820),
]
EXPECTED_HEADER = {
    "market_location": "Gboko Rural Market",
    "vendor_stall_id": "Stall 13",
}
EXPECTED_WRITE_IN = ("vegetables", "Scent leaf", "bundle", 300)

item_by_key = {(f["food_group_id"], f["item_id"]): f for f in fieldmap["item_fields"]}
header_by_id = {f["field_id"]: f for f in fieldmap["header_fields"]}

def draw_text(img, bbox_px, text):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = bbox_px
    d.text((x0 + 4, y0 + 2), text, font=FONT, fill=(0, 0, 0))

def fill_checkbox(img, bbox_px):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = bbox_px
    d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=(0, 0, 0))

# draw the fixed-item checkboxes + prices
for group_id, item_id, price in EXPECTED_ITEMS:
    field = item_by_key[(group_id, item_id)]
    page = field["page"] - 1
    fill_checkbox(images[page], pt_bbox_to_px(field["checkbox_bbox"]))
    draw_text(images[page], pt_bbox_to_px(field["price_bbox"]), str(price))

# draw the header fields
for field_id, text in EXPECTED_HEADER.items():
    field = header_by_id[field_id]
    page = field["page"] - 1
    draw_text(images[page], pt_bbox_to_px(field["bbox"]), text)

# draw one write-in row (first write-in slot of the vegetables group)
group_id, name, unit, price = EXPECTED_WRITE_IN
wi_field = next(f for f in fieldmap["write_in_fields"] if f["food_group_id"] == group_id and f["slot_index"] == 0)
page = wi_field["page"] - 1
draw_text(images[page], pt_bbox_to_px(wi_field["item_name_bbox"]), name)
draw_text(images[page], pt_bbox_to_px(wi_field["unit_bbox"]), unit)
draw_text(images[page], pt_bbox_to_px(wi_field["price_bbox"]), str(price))

# save synthetic pages for visual inspection
for i, img in enumerate(images):
    img.save(f"synthetic_filled_page_{i+1}.png")

# --- run extraction and check ---
submission, line_items = extract_from_images(images, fieldmap, schema)

print("=== Header extraction ===")
ok_header = True
for field_id, expected in EXPECTED_HEADER.items():
    got = submission.get(field_id, "")
    match = expected.lower() in got.lower()
    ok_header &= match
    print(f"  {field_id}: expected~='{expected}' got='{got}' {'OK' if match else 'MISMATCH'}")

print("=== Fixed item extraction ===")
found = {(li["food_group_id"], li["item_id"]): li for li in line_items if not li["is_write_in"]}
ok_items = True
for group_id, item_id, price in EXPECTED_ITEMS:
    li = found.get((group_id, item_id))
    match = li is not None and li["price"] == float(price)
    ok_items &= match
    print(f"  {item_id}: expected={price} got={li['price'] if li else None} "
          f"(raw='{li['raw_price_text'] if li else None}') {'OK' if match else 'MISMATCH'}")
unexpected_checks = [li for li in line_items if not li["is_write_in"]
                     and (li["food_group_id"], li["item_id"]) not in dict.fromkeys(
                         (g, i) for g, i, _ in EXPECTED_ITEMS)]
print(f"  false-positive checked boxes (should be 0): {len(unexpected_checks)}")

print("=== Write-in extraction ===")
write_ins = [li for li in line_items if li["is_write_in"]]
wi = write_ins[0] if write_ins else None
ok_wi = wi is not None and EXPECTED_WRITE_IN[1].lower() in (wi["item_label"] or "").lower() \
        and wi["price"] == float(EXPECTED_WRITE_IN[3])
print(f"  got: {wi}")
print(f"  {'OK' if ok_wi else 'MISMATCH'}")

print("\n=== SUMMARY ===")
print(f"header: {'PASS' if ok_header else 'FAIL'}")
print(f"fixed items: {'PASS' if ok_items and not unexpected_checks else 'FAIL'}")
print(f"write-in: {'PASS' if ok_wi else 'FAIL'}")
