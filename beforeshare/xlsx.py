"""Excel (.xlsx / .xlsm) scanning and cleaning with openpyxl.

Caveat: openpyxl rewrites the workbook. Charts, images, pivot tables and
some formatting may not survive the safe copy. The original is never changed.
"""
import openpyxl
from .models import Finding, Severity
from .detectors import scan_text

C = "xlsx"


def _load(path):
    return openpyxl.load_workbook(path, keep_vba=str(path).lower().endswith(".xlsm"))


def scan(path):
    wb = _load(path)
    out = []
    hidden = [ws.title for ws in wb.worksheets if ws.sheet_state != "visible"]
    if hidden:
        very = [ws.title for ws in wb.worksheets if ws.sheet_state == "veryHidden"]
        out.append(Finding("xlsx.hidden_sheet", Severity.HIGH,
                           f"{len(hidden)} hidden sheet(s): {', '.join(hidden)}"
                           + (f" ({len(very)} very hidden)" if very else ""), count=len(hidden)))
    hrows = hcols = comments = 0
    text_parts, formulas_ext = [], 0
    for ws in wb.worksheets:
        hrows += sum(1 for d in ws.row_dimensions.values() if d.hidden)
        hcols += sum(1 for d in ws.column_dimensions.values() if d.hidden)
        for row in ws.iter_rows():
            for c in row:
                if c.comment:
                    comments += 1
                    text_parts.append(c.comment.text or "")
                v = c.value
                if isinstance(v, str):
                    text_parts.append(v)
                    if v.startswith("=") and "[" in v and "]" in v:
                        formulas_ext += 1
    if hrows:
        out.append(Finding("xlsx.hidden_rows", Severity.HIGH, f"{hrows} hidden row(s)", count=hrows))
    if hcols:
        out.append(Finding("xlsx.hidden_cols", Severity.HIGH, f"{hcols} hidden column(s)", count=hcols))
    if comments:
        out.append(Finding("xlsx.comments", Severity.MEDIUM, f"{comments} cell comment(s)", count=comments))
    names = [n for n in wb.defined_names]
    if names:
        out.append(Finding("xlsx.defined_names", Severity.LOW, f"{len(names)} defined name(s)", removable=False, count=len(names)))
    if getattr(wb, "_external_links", None):
        out.append(Finding("xlsx.external_links", Severity.LOW,
                           f"{len(wb._external_links)} external link(s) to other workbooks", count=len(wb._external_links)))
    p = wb.properties
    meta = [x for x in (p.creator, p.lastModifiedBy, p.company if hasattr(p, "company") else None) if x]
    if meta or p.title or p.subject or p.keywords or p.description:
        out.append(Finding("xlsx.metadata", Severity.MEDIUM,
                           "Document properties" + (f" (author: {', '.join(dict.fromkeys(meta))})" if meta else "")))
    out += scan_text("\n".join(text_parts), C)
    return out


def clean(src, dst, codes):
    wb = _load(src)
    if "xlsx.hidden_sheet" in codes:
        for ws in list(wb.worksheets):
            if ws.sheet_state != "visible":
                wb.remove(ws)
    for ws in wb.worksheets:
        if "xlsx.hidden_rows" in codes:
            rows = sorted((i for i, d in ws.row_dimensions.items() if d.hidden), reverse=True)
            for i in rows:
                ws.delete_rows(i)
            for d in ws.row_dimensions.values():
                d.hidden = False
        if "xlsx.hidden_cols" in codes:
            cols = [(k, d) for k, d in ws.column_dimensions.items() if d.hidden]
            from openpyxl.utils import column_index_from_string
            for k, d in sorted(cols, key=lambda kd: -column_index_from_string(kd[0])):
                lo, hi = d.min or column_index_from_string(k), d.max or column_index_from_string(k)
                ws.delete_cols(lo, hi - lo + 1)
            for d in ws.column_dimensions.values():
                d.hidden = False
        if "xlsx.comments" in codes:
            for row in ws.iter_rows():
                for c in row:
                    c.comment = None
    if "xlsx.external_links" in codes:
        wb._external_links = []
    if "xlsx.metadata" in codes:
        from openpyxl.packaging.core import DocumentProperties
        wb.properties = DocumentProperties(creator="", lastModifiedBy="")
    wb.save(dst)
