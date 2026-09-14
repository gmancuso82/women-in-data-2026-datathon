"""
Generates a single, self-contained HTML review page from a review_manifest
CSV (produced by extract_paper_form.1.2.py --review). A back-office reviewer
opens the file directly in any browser -- no install, no server, works fully
offline -- sees each field's source crop next to what the pipeline extracted,
types the true value, and clicks "Download corrected CSV" to get a manifest
ready for extract_paper_form.1.2.py --ingest.

Crop images are embedded as base64 data URIs, so the page is one file: no
separate image folder has to travel with it.

Usage: python3 build_review_tool.1.0.py <review_manifest.csv> <output.html>
"""

import sys
import os
import base64
import csv


FIELD_TYPE_ORDER = ["checkbox", "price", "write_in_price", "header",
                     "write_in_item_name", "write_in_unit"]
FIELD_TYPE_LABELS = {
    "checkbox": "Item checkboxes", "price": "Item prices",
    "write_in_price": "Write-in prices", "header": "Header fields",
    "write_in_item_name": "Write-in item names", "write_in_unit": "Write-in units",
}


def img_data_uri(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_html(rows, form_id):
    rows_by_type = {}
    for row in rows:
        rows_by_type.setdefault(row["field_type"], []).append(row)

    sections = []
    for i, ft in enumerate(FIELD_TYPE_ORDER):
        if ft not in rows_by_type:
            continue
        cards = []
        for j, row in enumerate(rows_by_type[ft]):
            uri = img_data_uri(row["crop_path"])
            row_id = f"{ft}_{j}"
            extracted = row["extracted_value"]
            if ft == "checkbox":
                is_true = str(extracted).strip().lower() == "true"
                input_html = (
                    f'<select id="val_{row_id}" data-rowid="{row_id}">'
                    f'<option value="True" {"selected" if is_true else ""}>marked</option>'
                    f'<option value="False" {"selected" if not is_true else ""}>blank</option>'
                    f'</select>'
                )
            else:
                safe_val = "" if extracted in (None, "nan", "") else str(extracted)
                input_html = (
                    f'<input id="val_{row_id}" data-rowid="{row_id}" type="text" '
                    f'value="{safe_val}" placeholder="(blank)">'
                )
            cards.append(f"""
            <div class="card" data-rowid="{row_id}"
                 data-form_id="{row['form_id']}" data-field_type="{row['field_type']}"
                 data-food_group_id="{row['food_group_id']}" data-item_id="{row['item_id']}"
                 data-crop_path="{row['crop_path']}" data-extracted_value="{extracted}">
              <img src="{uri}" alt="{row['item_id']}">
              <div class="meta">
                <div class="label">{row['item_id'] or row['field_type']}</div>
                <div class="extracted">pipeline read: <code>{extracted or '(blank)'}</code></div>
                {input_html}
              </div>
            </div>""")
        sections.append(f"""
        <section>
          <h2>{FIELD_TYPE_LABELS.get(ft, ft)} <span class="count">({len(cards)})</span></h2>
          <div class="grid">{''.join(cards)}</div>
        </section>""")

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Review: {form_id}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 0; padding: 24px 32px 80px;
          background: #faf9f6; color: #1c1a17; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  .sub {{ color: #6b6558; font-size: 13px; margin-bottom: 20px; }}
  h2 {{ font-size: 15px; border-bottom: 1px solid #ddd8cc; padding-bottom: 6px; margin-top: 28px; }}
  .count {{ color: #948d7d; font-weight: normal; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
  .card {{ border: 1px solid #ddd8cc; border-radius: 8px; background: #fff; padding: 10px;
           width: 220px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
  .card img {{ max-width: 100%; border: 1px solid #eee; border-radius: 4px; background: #fff; }}
  .meta {{ margin-top: 8px; font-size: 12px; }}
  .label {{ font-weight: 600; margin-bottom: 2px; }}
  .extracted {{ color: #6b6558; margin-bottom: 6px; }}
  .extracted code {{ background: #f1efe7; padding: 1px 4px; border-radius: 3px; }}
  input, select {{ width: 100%; box-sizing: border-box; padding: 5px 6px; font-size: 13px;
           border: 1px solid #c9c3b3; border-radius: 5px; }}
  .toolbar {{ position: sticky; top: 0; background: #faf9f6; padding: 10px 0; z-index: 5;
              border-bottom: 1px solid #ddd8cc; margin-bottom: 4px; }}
  button {{ background: #2f6b4f; color: white; border: none; border-radius: 6px; padding: 10px 16px;
            font-size: 14px; cursor: pointer; }}
  button:hover {{ background: #255a41; }}
  .hint {{ color: #6b6558; font-size: 12px; margin-left: 12px; }}
</style></head>
<body>
  <h1>Review: {form_id}</h1>
  <div class="sub">Confirm or correct each field, then download the corrected manifest for --ingest.</div>
  <div class="toolbar">
    <button onclick="downloadCorrected()">Download corrected CSV</button>
    <span class="hint">Every field is prefilled with what the pipeline read -- edit only what's wrong.</span>
  </div>
  {''.join(sections)}
<script>
function downloadCorrected() {{
  const cards = document.querySelectorAll('.card');
  const header = ['form_id','field_type','food_group_id','item_id','crop_path','extracted_value','operator_value'];
  const lines = [header.join(',')];
  cards.forEach(card => {{
    const rowid = card.dataset.rowid;
    const input = document.getElementById('val_' + rowid);
    const opVal = (input.value || '').replace(/"/g, '""');
    const esc = s => '"' + String(s || '').replace(/"/g, '""') + '"';
    lines.push([
      esc(card.dataset.form_id), esc(card.dataset.field_type), esc(card.dataset.food_group_id),
      esc(card.dataset.item_id), esc(card.dataset.crop_path), esc(card.dataset.extracted_value),
      esc(opVal)
    ].join(','));
  }});
  const blob = new Blob([lines.join('\\n')], {{type: 'text/csv'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'review_manifest_{form_id}_corrected.csv';
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}}
</script>
</body></html>"""


def main():
    manifest_csv, out_html = sys.argv[1], sys.argv[2]
    with open(manifest_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    form_id = rows[0]["form_id"] if rows else "unknown"
    html = build_html(rows, form_id)
    with open(out_html, "w") as f:
        f.write(html)
    print(f"Wrote {out_html} ({len(rows)} fields from {manifest_csv})")


if __name__ == "__main__":
    main()
