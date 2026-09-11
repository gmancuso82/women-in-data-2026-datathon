# Local dashboard

Open `index.html` in a web browser to use the current prototype. Choose a locality and collection date to inspect the price action and the nutrition tradeoff.

## Local price-sheet intake

The **Add more current local evidence** panel accepts a searchable or scanned PDF price sheet. It extracts what it can, presents editable locality/date/market/food/unit/price fields, and requires a person to review them before saving structured rows locally in that browser. The original PDF is not retained.

Use the two synthetic files in `../test_files/` to demonstrate the two paths:

- `digital_price_sheet.pdf` - direct text extraction
- `scanned_price_sheet.pdf` - browser-side OCR, then review

The prototype currently loads open-source PDF/OCR tools when it opens. For a low-connectivity production setting, the OCR engine and language data would be bundled locally.

The dashboard displays a **price comparison**, not cost per nutrient. It blocks fresh-corn recommendations because the market-product and edible-nutrition units have not yet been reconciled.

Before presenting the pilot, rerun these two scripts after changing price or nutrition data:

```bash
python src/build_orange_vegetable_actions.py
```

Then update the small `dashboard_data.js` dataset or replace it with an automated export step.
