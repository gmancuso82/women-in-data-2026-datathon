# Local price-sheet intake tests

The dashboard contains a proof-of-concept intake step for more current local price observations. It is intentionally **review-first**:

> Price received; nutrition match still needs review.

## What the local prototype does

1. Accepts a PDF price sheet without uploading it to a server.
2. Reads a searchable PDF directly or uses browser-side OCR for a scanned PDF.
3. Extracts likely locality, collection date, market/source, food, unit, and price fields.
4. Displays editable fields and asks the user to complete anything missing.
5. Stores only reviewer-approved structured rows in that browser, with download and clear controls. The source PDF itself is not retained.

## Repeatable synthetic fixtures

- `test_files/digital_price_sheet.pdf` has a genuine searchable text layer. Expected: four price rows, Montería, 2025-11-20.
- `test_files/scanned_price_sheet.pdf` is an image-only PDF. Expected: browser-side OCR is attempted; the reviewer must confirm every extracted field. It contains a different date: 2025-11-21.

Both fixtures use synthetic values and a fictional source. They are for demonstration/testing only and are not DANE/SIPSA data.

The small file-level check below confirms that the two fixtures genuinely exercise different routes. It verifies the searchable text in the digital PDF and the absence of a text layer in the scanned-style PDF.

```bash
python src/validate_upload_test_pdfs.py
```

## Validation rule

Saving requires locality, collection date, food name, unit, and price for every included row. A saved price is **not** an automatic substitution recommendation. Foods with no verified profile in this pilot are shown as `Needs nutrition review`.

## Presentation note

This is a local proof of concept, not a permanent data system. A production deployment would need role-based access, consent and retention rules, secure storage, validation against official product catalogues, multilingual OCR testing, audit logs, and government stewardship of the data.

The current browser prototype loads open-source PDF and OCR libraries when it is opened. The uploaded document and approved observations remain on the device. A production deployment for low-connectivity settings would bundle the OCR engine and Spanish language data locally before field use.
