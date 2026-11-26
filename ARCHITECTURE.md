# BeforeShare: technical notes

**Modules**
- `models.py`: `Finding(code, severity, message, removable, count)` and `Severity`.
- `xlsx.py`, `docx.py`, `pptx.py`, `pdf.py`, `image.py`: one scanner and one cleaner per format. Each exposes `scan(path)` and `clean(src, dst, codes)`.
- `detectors.py`: rule-based text detectors (secrets, Luhn-checked card numbers, 14-digit national IDs, emails, phones).
- `core.py`: dispatch by extension, `clean` (safe copy), `scan_and_verify` (clean, rescan, compare).
- `cli.py`: command line. `gui.py`: a local web window (stdlib `http.server`, bound to 127.0.0.1, random per-run token, temporary folder deleted on exit).

**Algorithm**
1. `scan`: parse with a normal library, collect structural findings (hidden sheets, rows, columns, comments, tracked changes, hidden text, hidden slides, notes, annotations, attachments, EXIF GPS, metadata), then run text detectors over the visible content.
2. `clean`: write to a new file. Only the finding codes you pick are removed. The original is never opened for writing, and writing over it is refused.
3. Verification: rescan the copy. Any selected, removable code still present is reported and the CLI exits with code 2.
4. Word cleaning edits the XML: tracked changes are accepted (insertions kept, deletions dropped), comment ranges and the comments part are removed. Images are rebuilt from pixels, which drops all metadata at once. PDF is rewritten with pikepdf after removing info, XMP, annotations, attachments and auto-run actions. PDF hidden text is found with the optional PyMuPDF extra (white color, size under 2 pt, invisible render mode).

**Design decisions**
- Rules not AI, so every finding is explainable and works offline.
- Verification is the feature: removal bugs are common, so every safe copy is checked. It already caught a real bug in testing (the Excel library stamped its own name as the author).
- Text findings (emails, IDs, secrets) are report-only: deleting user content automatically is riskier than flagging it.
- The window is a local web page because it is testable in a real browser and has no GUI toolkit dependency.

**Testing** (15 pytest tests plus a real-browser end-to-end script): all five formats scanned and cleaned, originals byte-identical, refusal to overwrite, corrupt and unsupported files, the detectors, the web window's token check, scan, clean and download flow, and `tests/e2e_gui.py` driving real Chrome.

**Limits**: see the README (a safe copy is not a guarantee, text patterns are heuristic, PDF hidden text is not removed, Excel charts may be lost).
