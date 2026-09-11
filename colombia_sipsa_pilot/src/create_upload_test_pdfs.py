"""Create synthetic PDF fixtures for the local price-sheet intake prototype.

The first file has an actual PDF text layer. The second is a raster image inside
a PDF, so it behaves like a scanned sheet and requires OCR.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_files"
OUT.mkdir(exist_ok=True)

ROWS = [
    ("Zanahoria", "COP/kg", "2.850"),
    ("Ahuyama", "COP/kg", "1.600"),
    ("Yuca", "COP/kg", "2.450"),
    ("Frijol cargamanto", "COP/kg", "9.800"),
]


def draw_text_sheet(target: Path) -> None:
    pdf = canvas.Canvas(str(target), pagesize=letter)
    width, height = letter
    pdf.setFillColor(HexColor("#17332d"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(54, height - 62, "DEMO LOCAL PRICE SHEET")
    pdf.setFillColor(HexColor("#61706a"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(54, height - 80, "Synthetic searchable-PDF fixture for the Local Healthy Food Swap Monitor")
    pdf.setFillColor(HexColor("#17332d"))
    pdf.setFont("Helvetica", 11)
    metadata = [("Locality", "Montería"), ("Market", "Demonstration Food Hub"), ("Collection date", "2025-11-20")]
    y = height - 120
    for label, value in metadata:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(54, y, f"{label}: ")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(145, y, value)
        y -= 22
    y -= 12
    pdf.setFillColor(HexColor("#2e6d57"))
    pdf.rect(54, y, 500, 24, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 10)
    for text, x in [("Food", 65), ("Unit", 260), ("Price (COP)", 395)]:
        pdf.drawString(x, y + 8, text)
    y -= 25
    pdf.setFillColor(HexColor("#17332d"))
    for index, (food, unit, price) in enumerate(ROWS):
        if index % 2 == 0:
            pdf.setFillColor(HexColor("#edf7ea"))
            pdf.rect(54, y - 3, 500, 23, fill=1, stroke=0)
        pdf.setFillColor(HexColor("#17332d"))
        pdf.setFont("Helvetica", 10)
        pdf.drawString(65, y + 4, food)
        pdf.drawString(260, y + 4, unit)
        pdf.drawRightString(520, y + 4, price)
        y -= 24
    pdf.setFillColor(HexColor("#61706a"))
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(54, 50, "Demo only - values are synthetic and require human review before any use.")
    pdf.save()


def draw_scanned_sheet(target: Path) -> None:
    image = Image.new("RGB", (1700, 2200), "#f8f2e6")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 34)
    bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 25)
    draw.rectangle((100, 95, 1600, 2100), outline="#806f53", width=4)
    draw.text((150, 160), "DEMO LOCAL PRICE SHEET", fill="#17332d", font=bold)
    draw.text((150, 235), "Synthetic scanned-PDF fixture - OCR and human review required", fill="#61706a", font=small)
    details = [("Locality", "Montería"), ("Market", "Demonstration Food Hub"), ("Collection date", "2025-11-21")]
    y = 340
    for label, value in details:
        draw.text((150, y), f"{label}: {value}", fill="#17332d", font=regular)
        y += 62
    y += 42
    draw.rectangle((145, y, 1540, y + 60), fill="#2e6d57")
    for text, x in [("Food", 180), ("Unit", 760), ("Price (COP)", 1120)]:
        draw.text((x, y + 12), text, fill="white", font=regular)
    y += 72
    for food, unit, price in ROWS:
        draw.line((145, y + 50, 1540, y + 50), fill="#b9b09e", width=2)
        draw.text((180, y + 8), food, fill="#17332d", font=regular)
        draw.text((760, y + 8), unit, fill="#17332d", font=regular)
        draw.text((1120, y + 8), price, fill="#17332d", font=regular)
        y += 68
    draw.text((150, 2000), "DEMO ONLY - this image is intentionally embedded without a PDF text layer.", fill="#61706a", font=small)
    image.save(OUT / "scanned_price_sheet_source.png")
    pdf = canvas.Canvas(str(target), pagesize=letter)
    pdf.drawImage(str(OUT / "scanned_price_sheet_source.png"), 0, 0, width=letter[0], height=letter[1])
    pdf.save()
    (OUT / "scanned_price_sheet_source.png").unlink()


if __name__ == "__main__":
    draw_text_sheet(OUT / "digital_price_sheet.pdf")
    draw_scanned_sheet(OUT / "scanned_price_sheet.pdf")
    print(f"Wrote PDF fixtures to {OUT}")
