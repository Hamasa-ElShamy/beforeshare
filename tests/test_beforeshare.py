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


def test_pptx(pptx_file):
    c = codes(scan(pptx_file))
    assert {"pptx.hidden_slides", "pptx.notes", "pptx.metadata", "pptx.email"} <= c
    before = sha(pptx_file)
    out, remaining, ok = scan_and_verify(pptx_file)
    assert ok and sha(pptx_file) == before
    from pptx import Presentation
    prs = Presentation(out)
    assert len(prs.slides) == 1
    assert prs.slides[0].notes_slide.notes_text_frame.text == ""
    assert prs.core_properties.author == ""


def test_pdf_hidden_text_detected(hidden_pdf):
    fs = scan(hidden_pdf)
    hf = [f for f in fs if f.code == "pdf.hidden_text"]
    assert hf and not hf[0].removable
    assert "white" in hf[0].message


def test_pdf_visible_text_not_flagged(pdf_file):
    assert "pdf.hidden_text" not in codes(scan(pdf_file))


def _server():
    import threading
    from beforeshare.gui import make_server
    srv = make_server()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", srv.app.token


def test_gui_server_flow(xlsx_file):
    import urllib.request, urllib.error, json as j
    srv, base, tok = _server()
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/?t=wrong")
        assert e.value.code == 403
        assert b"BeforeShare" in urllib.request.urlopen(f"{base}/?t={tok}").read()
        data = open(xlsx_file, "rb").read()
        r = j.load(urllib.request.urlopen(urllib.request.Request(f"{base}/scan?t={tok}&name=customers.xlsx", data=data, method="POST")))
        assert any(f["code"] == "xlsx.hidden_sheet" for f in r["findings"])
        codes_ = [f["code"] for f in r["findings"] if f["removable"]]
        c = j.load(urllib.request.urlopen(urllib.request.Request(f"{base}/clean?t={tok}&id={r['id']}", data=j.dumps({"codes": codes_}).encode(), method="POST")))
        assert c["verified"] is True and c["copy_name"] == "customers.safe.xlsx"
        dl = urllib.request.urlopen(f"{base}/download?t={tok}&id={r['id']}").read()
        import io, openpyxl
        assert openpyxl.load_workbook(io.BytesIO(dl)).sheetnames == ["Public"]
        bad = j.load(urllib.request.urlopen(urllib.request.Request(f"{base}/scan?t={tok}&name=x.pdf", data=b"junk", method="POST")))
        assert "error" in bad
    finally:
        srv.shutdown()
        srv.app.close()
