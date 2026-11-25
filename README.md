# BeforeShare

**Your files may reveal more than you think.** BeforeShare scans a file for hidden data before you send or publish it, lets you choose what to remove, writes a safe copy, and then **scans the copy again** to check the removal worked. Your original file is never changed.

Runs fully offline. No AI model, no cloud: every check is a plain rule you can read in the code.

## What it checks

| File type | Found and removable | Found, review by hand |
|---|---|---|
| Excel `.xlsx` `.xlsm` | hidden sheets (incl. very hidden), hidden rows and columns, cell comments, external links, author metadata | emails, phone numbers, card numbers (Luhn checked), 14-digit national IDs, API keys and passwords in cell text |
| Word `.docx` | tracked changes (deleted text is still stored), comments, hidden text, author metadata | same text checks |
| PDF `.pdf` | author/creator metadata, XMP, annotations, embedded attachments, auto-run actions | form fields, same text checks |
| Images `.jpg` `.png` `.tiff` `.webp` | GPS location, capture time, camera or phone model, owner and software tags | none |

## Install

```bash
git clone https://github.com/mohamed-elshamy-ai/beforeshare
cd beforeshare
pip install -e .
```

Python 3.9+. For the window app you also need Tkinter (it ships with Python on Windows and macOS; on Linux install `python3-tk`).

## Use

```bash
beforeshare scan Company_Report.xlsx          # report only
beforeshare scan Company_Report.xlsx --json   # for scripts
beforeshare clean Company_Report.xlsx         # writes Company_Report.safe.xlsx and verifies it
beforeshare clean file.xlsx --only xlsx.hidden_sheet,xlsx.comments
beforeshare-gui                               # simple window with checkboxes (see note below)
```

Real output from `demo/Company_Report.xlsx` (see [`demo/demo-output.txt`](demo/demo-output.txt)):

```
BeforeShare Report

File: demo/Company_Report.xlsx

Found:

  [HIGH] 3 hidden row(s)
  [HIGH] 1 hidden sheet(s): Internal margins
  [MEDIUM] 1 cell comment(s)
  [MEDIUM] 7 email address(es) in content  (review manually, cannot be removed automatically)
  [MEDIUM] Document properties (author: Omar Khaled)
```

Exit codes: `scan` returns 1 if a HIGH item is found (useful in scripts), 0 otherwise. `clean` returns 2 if verification fails. 3 means the file could not be read.

## Install on Windows, macOS and Linux

Needs Python 3.9 or newer. On Windows install it from python.org and tick "Add python.exe to PATH".

```bash
# Windows (PowerShell):  py -m pip install git+https://github.com/mohamed-elshamy-ai/beforeshare
# macOS:                 python3 -m pip install git+https://github.com/mohamed-elshamy-ai/beforeshare
# Linux:                 python3 -m pip install --user git+https://github.com/mohamed-elshamy-ai/beforeshare
```

Tested on Linux only. Android: no app; Termux is untested. Technical notes (architecture, algorithms, testing): [ARCHITECTURE.md](ARCHITECTURE.md). Website: https://mohamed-elshamy-ai.github.io/beforeshare/

## How it works

1. **Detect** the file type by extension.
2. **Parse** it with a normal library (openpyxl, python-docx, pikepdf, Pillow).
3. **Scan** for hidden content and metadata, then run text rules over the visible content for secrets and personal data.
4. **Report** each finding with a severity (HIGH, MEDIUM, LOW).
5. **Safe copy**: write a new file without the items you selected. The original stays untouched.
6. **Verify**: scan the new file again. If anything you asked to remove is still there, the command says so and exits with code 2.

### الشرح بالعربي

الأداة بتفحص الملف قبل ما تبعته لحد: بتدور على حاجات مخفية جواه (شيتات مخفية في Excel، صفوف وأعمدة مخفية، تعليقات، تعديلات متتبعة في Word، اسم الكاتب، مواقع GPS في الصور، مرفقات داخل PDF). بتعرضلك كل حاجة بدرجة خطورة، وانت بتختار تمسح إيه، والأداة بتعمل **نسخة جديدة** (الأصلي ما بيتغيرش) وبعدين **بتفحص النسخة تاني** عشان تتأكد إن اللي اخترت تمسحه اتمسح فعلاً. بتشتغل أوفلاين تماماً وبقواعد واضحة، من غير أي AI.

## Limits (read these)

- The window app (`beforeshare-gui`) has not been tested on a real desktop yet. The command line is what the tests cover.
- **A safe copy is not a guarantee that a file is safe.** BeforeShare only knows the checks listed above. It can miss things and can flag harmless text.
- Text rules (emails, phones, cards, IDs, secrets) are pattern matches. They are reported for you to review. They are not removed automatically.
- Excel: the copy is rewritten with openpyxl. Charts, images and pivot tables may be lost, and formulas pointing at removed rows may change. Check the copy.
- Word: accepting tracked changes means insertions are kept and deletions removed. Text in text boxes, footnotes and embedded objects is not inspected.
- PDF: text hidden under other content (for example white text) and removed-by-drawing "redactions" are **not** detected. Metadata and annotations are handled.
- Images: removal rebuilds the image from its pixels. JPEG is saved again at quality 95, which is lossy. Metadata inside the picture itself (a visible location sign) is not touched.
- PowerPoint and other formats are not supported yet.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests build their own sample files, run scan and clean on them, and check that the original is byte-for-byte unchanged and that the safe copy passes verification.

## Roadmap

PowerPoint support, PDF hidden-text detection, optional Presidio-based name detection, drag and drop in the window app. None of these exist yet.

## License

MIT
