"""PowerPoint (.pptx) scanning and cleaning with python-pptx."""
from pptx import Presentation
from .models import Finding, Severity
from .detectors import scan_text

C = "pptx"
_REL_COMMENTS = ("/comments", "/commentAuthors")


def _slide_texts(prs):
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                yield shape.text_frame.text
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    for c in row.cells:
                        yield c.text


def scan(path):
    prs = Presentation(path)
    out = []
    hidden = [i for i, s in enumerate(prs.slides, 1) if s._element.get("show") == "0"]
    if hidden:
        out.append(Finding("pptx.hidden_slides", Severity.HIGH, f"{len(hidden)} hidden slide(s): {', '.join(map(str, hidden))}", count=len(hidden)))
    notes = [i for i, s in enumerate(prs.slides, 1) if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()]
    texts = list(_slide_texts(prs))
    if notes:
        out.append(Finding("pptx.notes", Severity.HIGH, f"Speaker notes on {len(notes)} slide(s): {', '.join(map(str, notes))}", count=len(notes)))
        texts += [prs.slides[i - 1].notes_slide.notes_text_frame.text for i in notes]
    ncomments = sum(1 for s in prs.slides for r in s.part.rels.values() if r.reltype.endswith("/comments"))
    if ncomments:
        out.append(Finding("pptx.comments", Severity.HIGH, f"Review comments on {ncomments} slide(s)", count=ncomments))
    cp = prs.core_properties
    people = [x for x in (cp.author, cp.last_modified_by) if x]
    if people or cp.title or cp.subject or cp.keywords or cp.comments:
        out.append(Finding("pptx.metadata", Severity.MEDIUM,
                           "Document properties" + (f" (author: {', '.join(dict.fromkeys(people))})" if people else "")))
    out += scan_text("\n".join(texts), C)
    return out


def clean(src, dst, codes):
    prs = Presentation(src)
    if "pptx.hidden_slides" in codes:
        lst = prs.slides._sldIdLst
        for sld_id, slide in list(zip(list(lst), list(prs.slides))):
            if slide._element.get("show") == "0":
                prs.part.drop_rel(sld_id.rId)
                lst.remove(sld_id)
    if "pptx.notes" in codes:
        for s in prs.slides:
            if s.has_notes_slide:
                s.notes_slide.notes_text_frame.text = ""
    if "pptx.comments" in codes:
        for s in prs.slides:
            for rid, rel in list(s.part.rels.items()):
                if rel.reltype.endswith("/comments"):
                    s.part.drop_rel(rid)
    if "pptx.metadata" in codes:
        cp = prs.core_properties
        for attr in ("author", "last_modified_by", "title", "subject", "keywords", "comments", "category"):
            setattr(cp, attr, "")
    prs.save(dst)
