"""Confirm the two PDF fixtures exercise different intake paths."""

from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test_files"


def pdf_text(name: str) -> str:
    reader = PdfReader(FIXTURES / name)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


digital = pdf_text("digital_price_sheet.pdf")
assert "Montería" in digital
assert "2025-11-20" in digital
for item in ("Zanahoria", "Ahuyama", "Yuca", "Frijol cargamanto"):
    assert item in digital, f"Missing searchable test item: {item}"

scanned = pdf_text("scanned_price_sheet.pdf")
assert not scanned.strip(), "The scanned fixture must remain image-only."

print("PASS: digital fixture has searchable text; scanned fixture has no PDF text layer.")
