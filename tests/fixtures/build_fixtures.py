"""Generate deterministic, PHI-free sample PDFs for tests.

Run once: `python tests/fixtures/build_fixtures.py`. Output committed.
NO real provider/patient data — invented analytes and values only.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
ROWS = [
    ("Widget", "12.0", "g/dL", "10.0-15.0"),
    ("Gadget", "4.5", "mmol", "3.0-5.0"),
    ("Sprocket", "99", "U/L", "0-120"),
]


def born_digital_columnar(path: Path) -> None:
    """Whitespace-aligned columns, no ruled lines (LabCorp archetype)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Courier", 11)
    y = 720
    c.drawString(72, y, "Test       Result   Units   Reference")
    for name, val, unit, ref in ROWS:
        y -= 18
        c.drawString(72, y, f"{name:<11}{val:<9}{unit:<8}{ref}")
    c.showPage()
    c.save()


def ruled_table(path: Path) -> None:
    """A bordered grid so page.lines is populated (Quest ruled archetype)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 11)
    xs = [72, 200, 300, 380, 500]
    top, rowh = 720, 22
    nrows = len(ROWS) + 1
    for i in range(nrows + 1):
        c.line(xs[0], top - i * rowh, xs[-1], top - i * rowh)
    for x in xs:
        c.line(x, top, x, top - nrows * rowh)
    header = ["Test", "Result", "Units", "Reference"]
    data = [header] + [list(r) for r in ROWS]
    for ri, row in enumerate(data):
        y = top - ri * rowh - 15
        for ci, cell in enumerate(row):
            c.drawString(xs[ci] + 4, y, cell)
    c.showPage()
    c.save()


def scanned_stub(path: Path) -> None:
    """Image-only PDF (no text layer) for is_scanned/OCR tests.

    Rendered large and high-resolution so a real OCR engine (tesseract) can
    read it cleanly: a low-res raster yields garbled, sub-threshold text and
    makes the OCR round-trip test flaky.
    """
    img = Image.new("RGB", (2000, 900), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=64)
    for i, (name, val, unit, ref) in enumerate(ROWS):
        d.text((80, 80 + i * 180), f"{name} {val} {unit} {ref}", fill="black", font=font)
    png = HERE / "_scanned_stub.png"
    img.save(png)
    c = canvas.Canvas(str(path), pagesize=letter)
    # near full page width so the rasterized glyphs are large enough for OCR
    c.drawImage(str(png), 56, 380, width=500, height=225)
    c.showPage()
    c.save()
    png.unlink()


if __name__ == "__main__":
    born_digital_columnar(HERE / "born_digital_columnar.pdf")
    ruled_table(HERE / "ruled_table.pdf")
    scanned_stub(HERE / "scanned_stub.pdf")
    print("fixtures written to", HERE)
