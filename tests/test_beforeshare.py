import json, os, hashlib
import pytest, openpyxl, docx
from PIL import Image
from beforeshare import scan, clean, scan_and_verify
from beforeshare.cli import main
from beforeshare.detectors import scan_text


def codes(fs):
    return {f.code for f in fs}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def test_xlsx_scan(xlsx_file):
    c = codes(scan(xlsx_file))
    assert {"xlsx.hidden_sheet", "xlsx.hidden_rows", "xlsx.hidden_cols", "xlsx.comments", "xlsx.metadata", "xlsx.secret"} <= c


def test_xlsx_clean_verified(xlsx_file):
    before = sha(xlsx_file)
    out, remaining, ok = scan_and_verify(xlsx_file)
    assert ok and not remaining
    assert sha(xlsx_file) == before  # original untouched
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Public"]
    assert wb.active.max_row == 4  # hidden row removed
    assert wb.properties.creator != "Ahmed Ali"


def test_docx(docx_file):
    c = codes(scan(docx_file))
    assert {"docx.tracked_changes", "docx.hidden_text", "docx.metadata"} <= c
    out, remaining, ok = scan_and_verify(docx_file)
    assert ok
    d = docx.Document(out)
    xml = d.element.xml
    assert "old price 500" not in xml
    assert "new price 400" in xml  # insertion accepted
    assert d.core_properties.author == ""


def test_pdf(pdf_file):
    c = codes(scan(pdf_file))
    assert "pdf.metadata" in c
    out, remaining, ok = scan_and_verify(pdf_file)
    assert ok
    assert "pdf.metadata" not in codes(scan(out))


def test_image(jpg_file):
    c = codes(scan(jpg_file))
    assert {"image.gps", "image.device", "image.datetime"} <= c
    out, remaining, ok = scan_and_verify(jpg_file)
    assert ok
    assert not (codes(scan(out)) & {"image.gps", "image.device", "image.datetime"})
    assert Image.open(out).size == (40, 30)


def test_refuses_overwrite(jpg_file):
    with pytest.raises(ValueError):
        clean(jpg_file, out=jpg_file)


def test_unsupported(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x")
    assert main(["scan", str(p)]) == 3


def test_cli_json_and_exit_code(xlsx_file, capsys):
    rc = main(["scan", xlsx_file, "--json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1 and any(d["code"] == "xlsx.hidden_sheet" for d in data)


def test_cli_clean(xlsx_file, capsys):
    assert main(["clean", xlsx_file]) == 0
    assert os.path.exists(xlsx_file.replace(".xlsx", ".safe.xlsx"))


def test_detectors():
    assert "text.secret" in codes(scan_text("password = hunter2hunter2", "text"))
    assert "text.card" in codes(scan_text("card 4111 1111 1111 1111", "text"))
    assert "text.card" not in codes(scan_text("number 1234 5678 9012 3456", "text"))
    assert "text.national_id" in codes(scan_text("ID 29901011234567", "text"))
    assert "text.email" in codes(scan_text("a@b.com", "text"))


def test_corrupt_file(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"not a pdf")
    assert main(["scan", str(p)]) == 3
