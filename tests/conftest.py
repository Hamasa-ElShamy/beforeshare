import pytest
from PIL import Image
import openpyxl, docx, pikepdf
from reportlab.pdfgen import canvas


@pytest.fixture
def xlsx_file(tmp_path):
    p = tmp_path / "customers.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Public"
    for i in range(1, 6):
        ws.append([f"row{i}", f"user{i}@example.com"])
    ws.row_dimensions[3].hidden = True
    ws.column_dimensions["B"].hidden = True
    ws["A1"].comment = openpyxl.comments.Comment("internal note", "Ahmed")
    sec = wb.create_sheet("Secret")
    sec["A1"] = "password: hunter2hunter2"
    sec.sheet_state = "hidden"
    wb.properties.creator = "Ahmed Ali"
    wb.save(p)
    return str(p)


@pytest.fixture
def docx_file(tmp_path):
    p = tmp_path / "contract.docx"
    d = docx.Document()
    d.add_paragraph("Visible text")
    para = d.add_paragraph()
    r = para.add_run("secret hidden words")
    r.font.hidden = True
    d.core_properties.author = "Sara Hassan"
    d.save(p)
    # inject a tracked deletion + insertion
    import zipfile, shutil
    tmp = tmp_path / "t.docx"
    with zipfile.ZipFile(p) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                x = data.decode()
                x = x.replace("<w:p>", '<w:p><w:del w:id="1" w:author="X" w:date="2026-01-01T00:00:00Z"><w:r><w:delText>old price 500</w:delText></w:r></w:del><w:ins w:id="2" w:author="X" w:date="2026-01-01T00:00:00Z"><w:r><w:t>new price 400</w:t></w:r></w:ins>', 1)
                data = x.encode()
            zout.writestr(item, data)
    shutil.move(tmp, p)
    return str(p)


@pytest.fixture
def pdf_file(tmp_path):
    p = tmp_path / "report.pdf"
    c = canvas.Canvas(str(p))
    c.setAuthor("Mona Said")
    c.setTitle("Quarterly")
    c.drawString(72, 700, "Contact: mona@example.com")
    c.save()
    with pikepdf.open(p, allow_overwriting_input=True) as pdf:
        pdf.save(p)
    return str(p)


@pytest.fixture
def jpg_file(tmp_path):
    p = tmp_path / "photo.jpg"
    img = Image.new("RGB", (40, 30), "red")
    ex = Image.Exif()
    ex[0x010F] = "Acme"
    ex[0x0110] = "PhoneX"
    ex[0x0132] = "2026:01:02 03:04:05"
    ex[0x8825] = {1: "N", 2: (30.0, 3.0, 0.0), 3: "E", 4: (31.0, 14.0, 0.0)}
    img.save(p, exif=ex)
    return str(p)


@pytest.fixture
def pptx_file(tmp_path):
    from pptx import Presentation
    p = tmp_path / "deck.pptx"
    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[1])
    s1.shapes.title.text = "Public"
    s1.placeholders[1].text = "Contact sales@example.com"
    s1.notes_slide.notes_text_frame.text = "Discount floor is 30 percent, do not tell client"
    s2 = prs.slides.add_slide(prs.slide_layouts[1])
    s2.shapes.title.text = "Internal pricing"
    s2._element.set("show", "0")
    prs.core_properties.author = "Omar Khaled"
    prs.save(p)
    return str(p)


@pytest.fixture
def hidden_pdf(tmp_path):
    p = tmp_path / "hidden.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(72, 700, "Visible heading")
    c.setFillColorRGB(1, 1, 1)
    c.drawString(72, 650, "secret white text for robots")
    c.save()
    return str(p)
