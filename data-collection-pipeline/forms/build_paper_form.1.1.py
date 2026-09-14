"""
v1.1 changes from build_paper_form.1.0.py:
  - Checkbox enlarged 4mm -> 8mm. A real phone-scanned checkbox at 4mm is only
    ~47x47px at 300dpi -- close enough to JPEG/scan compression block size (8x8px)
    and paper-texture noise that darkness/shape-based fill detection struggles to
    tell a real mark from scan noise. Doubling the box gives any detector a much
    better signal-to-noise ratio.
  - Instructs the vendor to mark a STAR rather than a checkmark. A star's several
    crossing strokes are a much more distinctive, hard-to-fake-with-noise shape
    than a single tick or a filled square, and gives us a stroke/shape-based
    detector something real to look for (see extract_paper_form.1.1.py).
  - Added a small header glyph above the checkbox column so the star instruction
    is visible right at the point of marking, not just in the paragraph above.

Row height and internal text/price positions scale off CHECKBOX/ROW_H so the
layout stays proportional rather than hardcoding a second set of offsets.

Usage: python3 build_paper_form.1.1.py <schema_path> <country_code> <output_basename>
"""

import json
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
CHECKBOX = 8 * mm          # was 4mm in v1.0
ROW_H = 9.5 * mm           # was 6.3mm in v1.0 -- must exceed CHECKBOX + a little padding
TEXT_Y_OFFSET = ROW_H * (3.2 / 6.3)   # keep the same relative baseline position as v1.0
PRICE_BOX_H = 4.6 * mm
PRICE_Y_OFFSET = ROW_H * (4.6 / 6.3)

COL_CHECKBOX_X = MARGIN
COL_ITEM_X = MARGIN + 8 * mm + (CHECKBOX - 4 * mm)  # shift item column right to clear the bigger box
COL_UNIT_X = MARGIN + 92 * mm
COL_PRICE_X = MARGIN + 122 * mm
COL_PRICE_W = 40 * mm

INSTRUCTIONS = (
    "For each item you sell, mark a STAR (not a check or an X) in the box and write today's price "
    "for the unit shown. If you sell more than one variety or grade of an item at different prices, "
    "write the price of the LEAST EXPENSIVE option only. Leave items you don't sell unmarked."
)


class FormBuilder:
    def __init__(self, schema, country, out_pdf_path):
        self.schema = schema
        self.country = country
        self.c = canvas.Canvas(out_pdf_path, pagesize=A4)
        self.page_num = 1
        self.y = PAGE_H - MARGIN
        self.fieldmap = {"header_fields": [], "item_fields": [], "write_in_fields": []}

    # -- low-level helpers --------------------------------------------------
    def ensure_space(self, needed):
        if self.y - needed < MARGIN:
            self.new_page()

    def new_page(self):
        self.c.showPage()
        self.page_num += 1
        self.y = PAGE_H - MARGIN
        self.draw_page_header()

    def draw_page_header(self):
        self.c.setFont("Helvetica-Bold", 13)
        self.c.drawString(MARGIN, self.y, "COMMUNITY RETAIL PRICE REPORTING FORM")
        self.y -= 5 * mm
        self.c.setFont("Helvetica", 8)
        self.c.drawString(
            MARGIN, self.y,
            f"Weekly submission - Cost of a Healthy Diet local price monitoring pilot - "
            f"Country: {self.country} - Page {self.page_num}"
        )
        self.y -= 8 * mm

    # -- sections -------------------------------------------------------
    def draw_header_block(self):
        fields = self.schema["header_fields"]
        self.c.setFont("Helvetica", 9)
        col_w = (PAGE_W - 2 * MARGIN) / 2
        for i, f in enumerate(fields):
            col = i % 2
            row = i // 2
            x = MARGIN + col * col_w
            y = self.y - row * 9 * mm
            self.c.setFont("Helvetica", 7)
            self.c.drawString(x, y, f["label"].upper())
            line_y = y - 4.2 * mm
            self.c.line(x, line_y, x + col_w - 6 * mm, line_y)
            self.fieldmap["header_fields"].append({
                "field_id": f["id"], "page": self.page_num,
                "bbox": [x, line_y, x + col_w - 6 * mm, line_y + 4.2 * mm]
            })
        rows_used = (len(fields) + 1) // 2
        self.y -= rows_used * 9 * mm + 6 * mm

    def draw_instructions(self):
        self.c.setFont("Helvetica-Oblique", 8)
        import textwrap
        for line in textwrap.wrap(INSTRUCTIONS, 100):
            self.c.drawString(MARGIN, self.y, line)
            self.y -= 4 * mm
        self.y -= 3 * mm

    def draw_group_table_header(self, label):
        self.ensure_space(14 * mm)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(MARGIN, self.y, label)
        self.y -= 5.5 * mm
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(COL_CHECKBOX_X, self.y, "★")  # star glyph, marks the checkbox column
        self.c.drawString(COL_ITEM_X, self.y, "ITEM")
        self.c.drawString(COL_UNIT_X, self.y, "UNIT")
        self.c.drawString(COL_PRICE_X, self.y, "PRICE (LOWEST, IF MULTIPLE)")
        self.y -= 3.5 * mm
        self.c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 3 * mm

    def draw_item_row(self, group_id, item):
        self.ensure_space(ROW_H)
        cb_y = self.y - CHECKBOX
        self.c.rect(COL_CHECKBOX_X, cb_y, CHECKBOX, CHECKBOX)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(COL_ITEM_X, self.y - TEXT_Y_OFFSET, item["label"])
        self.c.drawString(COL_UNIT_X, self.y - TEXT_Y_OFFSET, item["default_unit"])
        price_y0 = self.y - PRICE_Y_OFFSET
        self.c.rect(COL_PRICE_X, price_y0, COL_PRICE_W, PRICE_BOX_H)
        self.fieldmap["item_fields"].append({
            "food_group_id": group_id,
            "item_id": item["item_id"],
            "page": self.page_num,
            "checkbox_bbox": [COL_CHECKBOX_X, cb_y, COL_CHECKBOX_X + CHECKBOX, cb_y + CHECKBOX],
            "price_bbox": [COL_PRICE_X, price_y0, COL_PRICE_X + COL_PRICE_W, price_y0 + PRICE_BOX_H],
        })
        self.y -= ROW_H

    def draw_write_in_row(self, group_id, slot_index):
        self.ensure_space(ROW_H)
        self.c.setFont("Helvetica", 7)
        self.c.drawString(COL_CHECKBOX_X, self.y - TEXT_Y_OFFSET, "Other:")
        line_y = self.y - TEXT_Y_OFFSET - 1 * mm
        self.c.line(COL_ITEM_X, line_y, COL_UNIT_X - 3 * mm, line_y)
        self.c.line(COL_UNIT_X, line_y, COL_PRICE_X - 3 * mm, line_y)
        price_y0 = self.y - PRICE_Y_OFFSET
        self.c.rect(COL_PRICE_X, price_y0, COL_PRICE_W, PRICE_BOX_H)
        self.fieldmap["write_in_fields"].append({
            "food_group_id": group_id,
            "slot_index": slot_index,
            "page": self.page_num,
            "item_name_bbox": [COL_ITEM_X, line_y, COL_UNIT_X - 3 * mm, line_y + 4.2 * mm],
            "unit_bbox": [COL_UNIT_X, line_y, COL_PRICE_X - 3 * mm, line_y + 4.2 * mm],
            "price_bbox": [COL_PRICE_X, price_y0, COL_PRICE_X + COL_PRICE_W, price_y0 + PRICE_BOX_H],
        })
        self.y -= ROW_H

    def draw_signature_block(self):
        self.ensure_space(14 * mm)
        self.y -= 4 * mm
        self.c.line(MARGIN, self.y, MARGIN + 70 * mm, self.y)
        self.c.line(PAGE_W - MARGIN - 70 * mm, self.y, PAGE_W - MARGIN, self.y)
        self.c.setFont("Helvetica", 7)
        self.c.drawString(MARGIN, self.y - 3.5 * mm, "Vendor signature")
        self.c.drawString(PAGE_W - MARGIN - 70 * mm, self.y - 3.5 * mm, "Collected by (enumerator)")

    def build(self):
        self.draw_page_header()
        self.draw_header_block()
        self.draw_instructions()

        country_data = self.schema["countries"][self.country]
        write_in_slots = self.schema["write_in_slots_per_group"]

        for group in self.schema["food_groups"]:
            gid = group["id"]
            items = country_data["item_lists"].get(gid, [])
            self.draw_group_table_header(group["label"])
            for item in items:
                self.draw_item_row(gid, item)
            for slot in range(write_in_slots):
                self.draw_write_in_row(gid, slot)
            self.y -= 3 * mm

        self.draw_signature_block()
        self.c.showPage()
        self.c.save()


def main():
    schema_path, country, out_base = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(schema_path) as f:
        schema = json.load(f)

    builder = FormBuilder(schema, country, f"{out_base}.pdf")
    builder.build()

    with open(f"{out_base}_fieldmap.json", "w") as f:
        json.dump({
            "schema_version": schema["schema_version"],
            "country": country,
            "page_size": "A4",
            "units": "points (1/72 inch), origin bottom-left of page",
            "mark_style": "star",
            **builder.fieldmap
        }, f, indent=2)

    print(f"Wrote {out_base}.pdf and {out_base}_fieldmap.json ({builder.page_num} pages)")


if __name__ == "__main__":
    main()
