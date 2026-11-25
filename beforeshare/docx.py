"""Word (.docx) scanning and cleaning with python-docx + raw XML."""
import docx
from docx.oxml.ns import qn
from .models import Finding, Severity
from .detectors import scan_text

C = "docx"
_REL_COMMENTS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def _body_parts(d):
    parts = [d.element.body]
    for s in d.sections:
        for hf in (s.header, s.footer, s.first_page_header, s.first_page_footer):
            try:
                parts.append(hf._element)
            except Exception:
                pass
    return parts


def scan(path):
    d = docx.Document(path)
    out = []
    ins = dels = 0
    hidden_runs = 0
    for root in _body_parts(d):
        ins += len(root.findall(".//" + qn("w:ins")))
        dels += len(root.findall(".//" + qn("w:del")))
        hidden_runs += len(root.findall(".//" + qn("w:vanish")))
    if ins or dels:
        out.append(Finding("docx.tracked_changes", Severity.HIGH,
                           f"Tracked changes: {ins} insertion(s), {dels} deletion(s) (deleted text is still stored)", count=ins + dels))
    ncomments = 0
    for rel in d.part.rels.values():
        if rel.reltype == _REL_COMMENTS:
            try:
                ncomments = len(rel.target_part.element.findall(qn("w:comment")))
            except Exception:
                ncomments = 1
    if ncomments:
        out.append(Finding("docx.comments", Severity.HIGH, f"{ncomments} comment(s)", count=ncomments))
    if hidden_runs:
        out.append(Finding("docx.hidden_text", Severity.MEDIUM, f"{hidden_runs} run(s) of hidden text", count=hidden_runs))
    cp = d.core_properties
    people = [x for x in (cp.author, cp.last_modified_by) if x]
    if people or cp.title or cp.subject or cp.keywords or cp.comments:
        out.append(Finding("docx.metadata", Severity.MEDIUM,
                           "Document properties" + (f" (author: {', '.join(dict.fromkeys(people))})" if people else "")))
    texts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                texts.append(c.text)
    out += scan_text("\n".join(texts), C)
    return out


def clean(src, dst, codes):
    d = docx.Document(src)
    if "docx.tracked_changes" in codes:
        for root in _body_parts(d):
            for el in list(root.iter(qn("w:del"))):
                el.getparent().remove(el)
            for el in list(root.iter(qn("w:ins"))):
                parent = el.getparent()
                idx = parent.index(el)
                for child in list(el):
                    parent.insert(idx, child)
                    idx += 1
                parent.remove(el)
    if "docx.hidden_text" in codes:
        for root in _body_parts(d):
            for el in list(root.iter(qn("w:vanish"))):
                el.getparent().remove(el)
    if "docx.comments" in codes:
        for root in _body_parts(d):
            for tag in ("w:commentRangeStart", "w:commentRangeEnd"):
                for el in list(root.iter(qn(tag))):
                    el.getparent().remove(el)
            for el in list(root.iter(qn("w:commentReference"))):
                run = el.getparent()
                run.getparent().remove(run)
        for rid, rel in list(d.part.rels.items()):
            if rel.reltype == _REL_COMMENTS:
                d.part.rels.pop(rid)
    if "docx.metadata" in codes:
        cp = d.core_properties
        for attr in ("author", "last_modified_by", "title", "subject", "keywords", "comments", "category"):
            setattr(cp, attr, "")
    d.save(dst)
