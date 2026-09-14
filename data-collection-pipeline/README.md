# Hoos' Cooking — Retail Food Price Data Pipeline

**Part of the WiD Datathon 2026 project**. Collects real-time, subnational retail food price data in Nigeria and Colombia via a digital form or a printed paper form, extracts paper-form submissions automatically (checkbox marks + handwritten prices), and includes a human review step and a feedback loop that turns operator corrections into training data for two small classifiers.

**This is a proof-of-concept:** real-time, subnational retail food price data — the
kind needed to track the cost and affordability of a healthy diet — is one of
the data categories most consistently flagged as necessary for monitoring
progress toward the UN's 2030 Agenda (SDG 2), yet it remains largely
unavailable or collected too infrequently in the countries where it's needed
most (see FAO's [State of Food Security and Nutrition in the World](https://www.fao.org/publications/fao-flagship-publications/the-state-of-food-security-and-nutrition-in-the-world/en)
report). 

**Rather than collecting this data externally, the pipeline is designed
to be run by the countries themselves** — a *bottom-up model* that builds local
data-collection capacity while filling a gap the UN has already documented.

## Folder layout

- `forms/` — the paper/digital form builders, the extraction pipeline, the
  review-tool page generator, and the classifier trainers. Files are
  versioned in the filename (`extract_paper_form.1.5.py` is newer than
  `.1.4.py`); each version's docstring explains what changed. Use the
  highest-numbered version of each script unless you have a reason not to.
- `schema/` — `hoos_cooking_form_schema.*.json`, the single source of truth
  for food groups, item lists, and output table shape. Everything else is
  generated from this.
- `models/` — trained classifiers (`.pkl`, via `joblib`):
  `checkbox_classifier.1.0.pkl` (marked/blank detection) and
  `digit_classifier.1.0.pkl` (handwritten price digits). Both are optional —
  omit `--model`/`--digit-model` and the pipeline falls back to fixed
  thresholds / tesseract.
- `labels/` — `checkbox_labels.csv` and `price_labels.csv`, the accumulated
  operator-corrected examples the two classifiers are trained on. Grows via
  `extract_paper_form.*.py --ingest`.
- `demo/` — a ready-to-open demo set: one real hand-marked scan plus two
  synthetic ones, already run through extraction and review, for a
  click-through walkthrough with no terminal needed (`demo_review.html`).

## Quick start

```
pip install -r requirements.txt

# Extract one scanned/photographed paper form
python3 forms/extract_paper_form.1.5.py <scan.pdf> \
    forms/hoos_cooking_paper_form_COL.1.2_fieldmap.json \
    schema/hoos_cooking_form_schema.1.2.json \
    <output_basename>

# ...or a whole folder of scans at once
python3 forms/extract_paper_form.1.5.py --batch <folder_of_pdfs> \
    forms/hoos_cooking_paper_form_COL.1.2_fieldmap.json \
    schema/hoos_cooking_form_schema.1.2.json \
    <output_basename>
```

See `pipeline_hub.*.html` for the full collect → extract → review →
ingest walkthrough with copy-paste commands, or open `demo/demo_review.html`
directly for a working example with no setup.

## Retraining the classifiers

```
python3 forms/train_checkbox_classifier.1.0.py labels/checkbox_labels.csv models/checkbox_classifier.1.0.pkl
python3 forms/train_digit_classifier.1.0.py labels/price_labels.csv models/digit_classifier.1.0.pkl
```

Both print an honest accuracy estimate before saving. See each script's
docstring for how the classifier works and its current limitations.

## References 
- [The State of Food Security and Nutrition in the World (FAO flagship page)](https://www.fao.org/publications/fao-flagship-publications/the-state-of-food-security-and-nutrition-in-the-world/en)
- [2.3 Cost and affordability of a healthy diet: an update (SOFI 2022, FAO)](https://openknowledge.fao.org/server/api/core/bitstreams/6ca1510c-9341-4d6a-b285-5f5e8743cc46/content/sofi-2022/cost-affordability-healthy-diet.html)
- [Cost and Affordability of a Healthy Diet (CoAHD) — ANH Academy Data4Diets](https://www.anh-academy.org/data4diets/indicator/cost-and-affordability-healthy-diet-coahd)
