"""
Verification harness for extract_paper_form.1.1.py's new star-mark detector
and bigger (8mm) checkbox, run against build_paper_form.1.1's NGA form.

Draws actual crossing-line star strokes (not a solid black fill -- that would
trivially pass any darkness threshold and wouldn't exercise the new
stroke-based check at all) at a handful of known items, plus a couple of
"noise" distractors (a smudge, a single stray line) in otherwise-blank boxes,
to check those are correctly NOT flagged. This validates the coordinate math
and detector logic synthetically; it does not replace testing against a real
star-marked scan, which is the next real-world step once one exists.
"""

import json
import math
import importlib.util
from PIL import ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location("extract_paper_form", "extract_paper_form.1.1.py")
extract_paper_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_paper_form)
pdf_to_page_images = extract_paper_form.pdf_to_page_images
pt_bbox_to_px = extract_paper_form.pt_bbox_to_px
extract_from_images = extract_paper_form.extract_from_images

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)

with open("hoos_cooking_paper_form_NGA.1.2_fieldmap.json") as f:
    fieldmap = json.load(f)
with open("hoos_cooking_form_schema.1.2.json") as f:
    schema = json.load(f)

images = pdf_to_page_images("hoos_cooking_paper_form_NGA.1.2.pdf")
images = [img.copy() for img in images]

EXPECTED_ITEMS = [
    ("starchy_staples", "rice_local", 1250),
    ("starchy_staples", "garri", 630),
    ("vegetables", "tomato", 1370),
]
NOISE_ITEMS = ["rice_imported", "cassava_fresh"]  # left blank except for synthetic noise

item_by_key = {(f["food_group_id"], f["item_id"]): f for f in fieldmap["item_fields"]}


def draw_text(img, bbox_px, text):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = bbox_px
    d.text((x0 + 4, y0 + 2), text, font=FONT, fill=(0, 0, 0))


def draw_star(img, bbox_px, n_strokes=3, width=3):
    """Draw n_strokes lines through the box center at evenly spaced angles --
    an asterisk, not a solid fill -- to actually exercise stroke detection."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = bbox_px
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = min(x1 - x0, y1 - y0) / 2 - 3
    for k in range(n_strokes):
        angle = math.pi * k / n_strokes
        dx, dy = r * math.cos(angle), r * math.sin(angle)
        d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=(0, 0, 0), width=width)


def draw_smudge(img, bbox_px):
    """A diffuse gray patch (no clean edges) -- simulates a shadow/paper-texture
    false trigger, not a real mark."""
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = bbox_px
    d.ellipse([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=(90, 90, 90, 110))


def draw_stray_line(img, bbox_px):
    """A single stray pen line -- one direction only, should NOT count as a
    star (needs >=2 distinct stroke directions)."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = bbox_px
    d.line([(x0 + 3, y1 - 3), (x1 - 3, y0 + 3)], fill=(0, 0, 0), width=2)


for group_id, item_id, price in EXPECTED_ITEMS:
    field = item_by_key[(group_id, item_id)]
    page = field["page"] - 1
    draw_star(images[page], pt_bbox_to_px(field["checkbox_bbox"]))
    draw_text(images[page], pt_bbox_to_px(field["price_bbox"]), str(price))

noise_field_1 = item_by_key[("starchy_staples", NOISE_ITEMS[0])]
draw_smudge(images[noise_field_1["page"] - 1], pt_bbox_to_px(noise_field_1["checkbox_bbox"]))
noise_field_2 = item_by_key[("starchy_staples", NOISE_ITEMS[1])]
draw_stray_line(images[noise_field_2["page"] - 1], pt_bbox_to_px(noise_field_2["checkbox_bbox"]))

for i, img in enumerate(images):
    img.save(f"synthetic_star_12_page_{i+1}.png")

submission, line_items = extract_from_images(images, fieldmap, schema)

print("=== Fixed item extraction (star marks) ===")
found = {(li["food_group_id"], li["item_id"]): li for li in line_items if not li["is_write_in"]}
ok_items = True
for group_id, item_id, price in EXPECTED_ITEMS:
    li = found.get((group_id, item_id))
    match = li is not None and li["price"] == float(price)
    ok_items &= match
    print(f"  {item_id}: expected={price} got={li['price'] if li else None} {'OK' if match else 'MISMATCH'}")

false_positives = [key for key in found if key[1] in NOISE_ITEMS]
print(f"\n=== Noise distractors (smudge, stray line) -- should NOT be flagged ===")
for item_id in NOISE_ITEMS:
    flagged = any(k[1] == item_id for k in found)
    print(f"  {item_id}: flagged={flagged} {'MISMATCH' if flagged else 'OK'}")

print("\n=== SUMMARY ===")
print(f"star marks detected correctly: {'PASS' if ok_items else 'FAIL'}")
print(f"noise correctly rejected: {'PASS' if not false_positives else 'FAIL'}")
