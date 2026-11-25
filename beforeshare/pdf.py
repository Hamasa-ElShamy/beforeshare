"""PDF scanning and cleaning with pikepdf."""
import pikepdf
from .models import Finding, Severity
from .detectors import scan_text

C = "pdf"


def scan(path):
    out = []
    with pikepdf.open(path) as pdf:
        info = {str(k): str(v) for k, v in (pdf.docinfo or {}).items()}
        interesting = {k: v for k, v in info.items() if k in ("/Author", "/Creator", "/Producer", "/Title", "/Subject", "/Keywords") and v.strip()}
        if interesting:
            parts = [f"{k[1:].lower()}={v}" for k, v in interesting.items() if k in ("/Author", "/Creator", "/Producer")]
            out.append(Finding("pdf.metadata", Severity.MEDIUM,
                               "Document metadata" + (f" ({'; '.join(parts)})" if parts else "")))
        try:
            with pdf.open_metadata() as meta:
                if len(meta) > 0:
                    out.append(Finding("pdf.xmp", Severity.LOW, "XMP metadata block"))
        except Exception:
            pass
        annots = 0
        for page in pdf.pages:
            a = page.obj.get("/Annots")
            if a is not None:
                annots += sum(1 for x in a if str(x.get("/Subtype")) != "/Link")
        if annots:
            out.append(Finding("pdf.annotations", Severity.MEDIUM, f"{annots} annotation(s) (comments, highlights, notes)", count=annots))
        try:
            n = len(pdf.attachments)
        except Exception:
            n = 0
        if n:
            out.append(Finding("pdf.attachments", Severity.HIGH, f"{n} embedded file attachment(s)", count=n))
        root = pdf.Root
        if "/JavaScript" in str(root.get("/Names", "")) or "/OpenAction" in root:
            out.append(Finding("pdf.javascript", Severity.MEDIUM, "Document has auto-run actions or JavaScript", count=1))
        if "/AcroForm" in root:
            out.append(Finding("pdf.forms", Severity.LOW, "Interactive form fields (values may hold data)", removable=False))
    try:
        import pymupdf as fitz  # optional: PyMuPDF for text content checks
        with fitz.open(path) as doc:
            text = "\n".join(p.get_text() for p in doc)
            hidden = _hidden_text(doc)
        if hidden:
            out.append(Finding("pdf.hidden_text", Severity.HIGH,
                               f"Text that is invisible on the page: {hidden.get('white', 0)} white, {hidden.get('tiny', 0)} tiny, {hidden.get('invisible', 0)} invisible-mode span(s). "
                               "Scanned PDFs with an OCR layer also show up here", removable=False, count=sum(hidden.values())))
        out += scan_text(text, C)
    except ImportError:
        pass
    return out


def clean(src, dst, codes):
    with pikepdf.open(src) as pdf:
        if "pdf.metadata" in codes:
            for k in list(pdf.docinfo.keys()):
                del pdf.docinfo[k]
        if "pdf.xmp" in codes or "pdf.metadata" in codes:
            if "/Metadata" in pdf.Root:
                del pdf.Root["/Metadata"]
        if "pdf.annotations" in codes:
            for page in pdf.pages:
                a = page.obj.get("/Annots")
                if a is not None:
                    keep = [x for x in a if str(x.get("/Subtype")) == "/Link"]
                    if keep:
                        page.obj["/Annots"] = pikepdf.Array(keep)
                    else:
                        del page.obj["/Annots"]
        if "pdf.attachments" in codes:
            for name in list(pdf.attachments.keys()):
                del pdf.attachments[name]
        if "pdf.javascript" in codes:
            if "/OpenAction" in pdf.Root:
                del pdf.Root["/OpenAction"]
            if "/AA" in pdf.Root:
                del pdf.Root["/AA"]
            names = pdf.Root.get("/Names")
            if names is not None and "/JavaScript" in names:
                del names["/JavaScript"]
        pdf.save(dst)


def _hidden_text(doc):
    """Count text spans a reader cannot see: white text, tiny text (under 2 pt), invisible render mode."""
    n = {"white": 0, "tiny": 0, "invisible": 0}
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    if span["color"] == 0xFFFFFF:
                        n["white"] += 1
                    elif span["size"] < 2:
                        n["tiny"] += 1
        try:
            for t in page.get_texttrace():
                if t.get("type") == 3:
                    n["invisible"] += 1
        except Exception:
            pass
    return {k: v for k, v in n.items() if v}
