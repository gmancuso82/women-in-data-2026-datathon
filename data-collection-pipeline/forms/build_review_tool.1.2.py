"""
v1.2 changes from build_review_tool.1.1.py:
  - Accepts either a single review_manifest CSV (unchanged) OR a directory
    containing several (as extract_paper_form.1.3.py --review --batch now
    produces, one manifest per scanned form) -- and builds ONE combined
    page covering every form in the batch, so a reviewer doesn't open a
    separate HTML file per vendor.
  - Each form gets its own collapsible block with its own line numbering and
    its own "Are all other lines blank?" bulk-confirm bar, scoped so
    confirming/flagging in one form's block never touches another form's
    cards (previously all lookups were document-wide, which only worked
    because there was only ever one form on the page).
  - The download button still exports ONE combined corrected CSV across every
    form in the batch -- extract_paper_form.py --ingest doesn't care how many
    form_ids are mixed into one manifest, so one download still feeds it
    directly.

Usage:
    python3 build_review_tool.1.2.py <review_manifest.csv> <output.html>
    python3 build_review_tool.1.2.py <folder_of_review_manifests> <output.html>
"""

import sys
import os
import re
import glob
import base64
import csv


FIELD_TYPE_ORDER = ["checkbox", "price", "write_in_price", "header",
                     "write_in_item_name", "write_in_unit"]
FIELD_TYPE_LABELS = {
    "checkbox": "Item checkboxes", "price": "Item prices",
    "write_in_price": "Write-in prices", "header": "Header fields",
    "write_in_item_name": "Write-in item names", "write_in_unit": "Write-in units",
}
LINE_NUMBERED_TYPES = ("checkbox", "price")


def img_data_uri(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)


def build_form_block(form_id, rows):
    fid = slug(form_id)
    rows_by_type = {}
    for row in rows:
        rows_by_type.setdefault(row["field_type"], []).append(row)

    n_flagged_candidates = sum(
        1 for r in rows_by_type.get("checkbox", []) if str(r["extracted_value"]).strip() != "True"
    )
    sections = []
    for ft in FIELD_TYPE_ORDER:
        if ft not in rows_by_type:
            continue
        cards = []
        for j, row in enumerate(rows_by_type[ft]):
            uri = img_data_uri(row["crop_path"])
            row_id = f"{fid}_{ft}_{j}"
            extracted = row["extracted_value"]
            line_no = j + 1 if ft in LINE_NUMBERED_TYPES else ""
            badge_html = f'<span class="badge">#{line_no}</span>' if line_no else ""
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
            <div class="card" id="card_{row_id}" data-rowid="{row_id}" data-line_no="{line_no}"
                 data-field_type="{row['field_type']}" data-flagged="False"
                 data-form_id="{row['form_id']}"
                 data-food_group_id="{row['food_group_id']}" data-item_id="{row['item_id']}"
                 data-crop_path="{row['crop_path']}" data-extracted_value="{extracted}">
              {badge_html}
              <img src="{uri}" alt="{row['item_id']}">
              <div class="meta">
                <div class="label">{row['item_id'] or row['field_type']}</div>
                <div class="extracted">pipeline read: <code>{extracted or '(blank)'}</code></div>
                {input_html}
              </div>
            </div>""")
        bulk_bar = ""
        if ft == "checkbox":
            bulk_bar = f"""
            <div class="bulk-bar">
              <strong>Are all other lines blank?</strong>
              <button class="yes" onclick="confirmAllBlank(this, [])">Yes, confirm all</button>
              <span class="or">or list the line number(s) that are NOT actually blank:</span>
              <input id="exceptionLines_{fid}" type="text" placeholder="e.g. 3, 9" style="width:120px">
              <button class="flag" onclick="confirmAllBlank(this, parseExceptions('exceptionLines_{fid}'))">Apply</button>
            </div>"""
        sections.append(f"""
        <section>
          <h3>{FIELD_TYPE_LABELS.get(ft, ft)} <span class="count">({len(cards)})</span></h3>
          {bulk_bar}
          <div class="grid">{''.join(cards)}</div>
        </section>""")

    return f"""
    <details class="form-block" open data-form="{fid}">
      <summary>{form_id} <span class="count">— {n_flagged_candidates} blank-read line(s) to confirm</span></summary>
      {''.join(sections)}
    </details>"""


def build_html(forms):
    """forms: list of (form_id, rows) tuples."""
    blocks = "".join(build_form_block(form_id, rows) for form_id, rows in forms)
    title = forms[0][0] if len(forms) == 1 else f"{len(forms)} forms"

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Review: {title}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 0; padding: 24px 32px 80px;
          background: #faf9f6; color: #1c1a17; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  .sub {{ color: #6b6558; font-size: 13px; margin-bottom: 20px; }}
  h3 {{ font-size: 15px; border-bottom: 1px solid #ddd8cc; padding-bottom: 6px; margin-top: 24px; }}
  .count {{ color: #948d7d; font-weight: normal; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
  .card {{ position: relative; border: 1px solid #ddd8cc; border-radius: 8px; background: #fff; padding: 10px;
           width: 220px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
  .card img {{ max-width: 100%; border: 1px solid #eee; border-radius: 4px; background: #fff; }}
  .card.confirmed {{ background: #f3f7f2; border-color: #cfe0c8; }}
  .card.flagged {{ background: #fdf3ec; border-color: #e3a86b; box-shadow: 0 0 0 2px #e3a86b33; }}
  .badge {{ position: absolute; top: -8px; left: -8px; background: #4a4436; color: #fff; font-size: 11px;
            border-radius: 10px; padding: 2px 7px; font-weight: 600; }}
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
  .bulk-bar {{ background: #eef2ec; border: 1px solid #cfe0c8; border-radius: 8px; padding: 10px 12px;
               margin: 10px 0 4px; font-size: 13px; display: flex; align-items: center; gap: 8px;
               flex-wrap: wrap; }}
  .bulk-bar button {{ padding: 6px 12px; font-size: 13px; }}
  .bulk-bar button.flag {{ background: #b5651d; }}
  .bulk-bar button.flag:hover {{ background: #954f14; }}
  .bulk-bar .or {{ color: #6b6558; }}
  .bulk-status {{ font-size: 12px; color: #2f6b4f; margin-left: 6px; }}
  .form-block {{ border: 1px solid #ddd8cc; border-radius: 10px; background: #fff; padding: 6px 18px 18px;
                 margin-bottom: 18px; }}
  .form-block > summary {{ font-size: 15px; font-weight: 700; padding: 12px 0; cursor: pointer; }}
  .form-block > summary .count {{ font-weight: 400; }}
</style></head>
<body>
  <h1>Review: {title}</h1>
  <div class="sub">Confirm or correct each field, then download one corrected manifest for --ingest -- it covers every form below.</div>
  <div class="toolbar">
    <button onclick="downloadCorrected()">Download corrected CSV</button>
    <span class="hint">Every field is prefilled with what the pipeline read -- edit only what's wrong.</span>
  </div>
  {blocks}
<script>
function parseExceptions(inputId) {{
  const raw = document.getElementById(inputId).value || '';
  return raw.split(/[,\\s]+/).map(s => s.trim()).filter(Boolean).map(Number).filter(n => !isNaN(n));
}}

function confirmAllBlank(btn, exceptions) {{
  const scope = btn.closest('.form-block');
  const exceptSet = new Set(exceptions);
  const checkboxCards = scope.querySelectorAll('.card[data-field_type="checkbox"]');
  let confirmedCount = 0, flaggedCount = 0;
  checkboxCards.forEach(cbCard => {{
    const lineNo = Number(cbCard.dataset.line_no);
    const wasBlank = cbCard.dataset.extracted_value !== 'True';
    if (!wasBlank) return;
    const priceCard = scope.querySelector(
      '.card[data-field_type="price"][data-line_no="' + lineNo + '"]');
    if (exceptSet.has(lineNo)) {{
      cbCard.dataset.flagged = 'True'; cbCard.classList.add('flagged'); cbCard.classList.remove('confirmed');
      if (priceCard) {{ priceCard.dataset.flagged = 'True'; priceCard.classList.add('flagged'); priceCard.classList.remove('confirmed'); }}
      flaggedCount++;
    }} else {{
      document.getElementById('val_' + cbCard.dataset.rowid).value = 'False';
      cbCard.dataset.flagged = 'False'; cbCard.classList.add('confirmed'); cbCard.classList.remove('flagged');
      if (priceCard) {{
        document.getElementById('val_' + priceCard.dataset.rowid).value = 'BLANK';
        priceCard.dataset.flagged = 'False'; priceCard.classList.add('confirmed'); priceCard.classList.remove('flagged');
      }}
      confirmedCount++;
    }}
  }});
  const bar = btn.closest('.bulk-bar');
  let status = bar.querySelector('.bulk-status');
  if (!status) {{ status = document.createElement('span'); status.className = 'bulk-status'; bar.appendChild(status); }}
  status.textContent = `Confirmed ${{confirmedCount}} blank line(s)` +
    (flaggedCount ? `, flagged ${{flaggedCount}} for your review below.` : '.');
}}

function downloadCorrected() {{
  const cards = document.querySelectorAll('.card');
  const header = ['form_id','field_type','food_group_id','item_id','line_no','crop_path',
                   'extracted_value','operator_value','flagged'];
  const lines = [header.join(',')];
  cards.forEach(card => {{
    const rowid = card.dataset.rowid;
    const input = document.getElementById('val_' + rowid);
    const opVal = (input.value || '');
    const esc = s => '"' + String(s || '').replace(/"/g, '""') + '"';
    lines.push([
      esc(card.dataset.form_id), esc(card.dataset.field_type), esc(card.dataset.food_group_id),
      esc(card.dataset.item_id), esc(card.dataset.line_no), esc(card.dataset.crop_path),
      esc(card.dataset.extracted_value), esc(opVal), esc(card.dataset.flagged)
    ].join(','));
  }});
  const blob = new Blob([lines.join('\\n')], {{type: 'text/csv'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'review_manifest_batch_corrected.csv';
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}}
</script>
</body></html>"""


def load_manifest(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    form_id = rows[0]["form_id"] if rows else os.path.basename(path)
    return form_id, rows


def main():
    src, out_html = sys.argv[1], sys.argv[2]
    if os.path.isdir(src):
        manifest_paths = sorted(glob.glob(os.path.join(src, "review_manifest_*.csv")))
        if not manifest_paths:
            print(f"No review_manifest_*.csv files found in {src}")
            sys.exit(1)
        forms = [load_manifest(p) for p in manifest_paths]
    else:
        forms = [load_manifest(src)]

    html = build_html(forms)
    with open(out_html, "w") as f:
        f.write(html)
    total_rows = sum(len(rows) for _, rows in forms)
    print(f"Wrote {out_html} ({len(forms)} form(s), {total_rows} fields total)")


if __name__ == "__main__":
    main()
