import argparse
import json
import sys

from . import __version__
from .core import scan, clean, scan_and_verify, SUPPORTED, UnsupportedFile
from .models import Severity
from .report import render


def main(argv=None):
    ap = argparse.ArgumentParser(prog="beforeshare",
                                 description="Find hidden data in a file before you share it.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a file and print findings")
    s.add_argument("file")
    s.add_argument("--json", action="store_true", help="machine readable output")
    c = sub.add_parser("clean", help="create a verified safe copy (original is not changed)")
    c.add_argument("file")
    c.add_argument("-o", "--output", help="output path (default: NAME.safe.EXT)")
    c.add_argument("--only", help="comma separated finding codes to remove (default: all removable)")
    sub.add_parser("formats", help="list supported file types")
    a = ap.parse_args(argv)

    if a.cmd == "formats":
        print(" ".join(SUPPORTED))
        return 0
    try:
        if a.cmd == "scan":
            findings = scan(a.file)
            if a.json:
                print(json.dumps([{"code": f.code, "severity": f.severity.label(), "message": f.message,
                                   "removable": f.removable, "count": f.count} for f in findings], indent=2))
            else:
                print(render(a.file, findings, color=sys.stdout.isatty()))
            return 1 if any(f.severity == Severity.HIGH for f in findings) else 0
        if a.cmd == "clean":
            codes = a.only.split(",") if a.only else None
            out, remaining, ok = scan_and_verify(a.file, a.output, codes)
            print(f"Safe copy written: {out}")
            print("Original file was not changed.")
            if ok:
                print("Verification: rescanned the copy, the selected items are gone.")
                left = [f for f in scan(out)]
                if left:
                    print("Still present (not selected or not removable):")
                    for f in left:
                        print(f"  {f}")
                return 0
            print("Verification FAILED. Still present in the copy:")
            for f in remaining:
                print(f"  {f}")
            return 2
    except (UnsupportedFile, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    except Exception as e:  # corrupt or unreadable file
        print(f"error: could not process file ({type(e).__name__}: {e})", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
