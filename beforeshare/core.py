"""Dispatch, safe-copy creation and verification."""
import os
import tempfile
from pathlib import Path

from . import xlsx, docx, pdf, image
from .models import Finding, Severity

_HANDLERS = {
    ".xlsx": xlsx, ".xlsm": xlsx,
    ".docx": docx,
    ".pdf": pdf,
    ".jpg": image, ".jpeg": image, ".png": image, ".tif": image, ".tiff": image, ".webp": image,
}
SUPPORTED = sorted(_HANDLERS)


class UnsupportedFile(ValueError):
    pass


def _handler(path):
    ext = Path(path).suffix.lower()
    if ext not in _HANDLERS:
        raise UnsupportedFile(f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED)}")
    return _HANDLERS[ext]


def scan(path):
    """Scan a file and return a list of Findings, highest severity first."""
    path = str(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    found = _handler(path).scan(path)
    return sorted(found, key=lambda f: (-int(f.severity), f.code))


def default_safe_path(path):
    p = Path(path)
    return str(p.with_name(f"{p.stem}.safe{p.suffix}"))


def clean(path, out=None, codes=None):
    """Write a safe copy. The original is never modified.

    codes: finding codes to remove. None means every removable finding.
    Returns the path of the new file.
    """
    path = str(path)
    findings = scan(path)
    removable = {f.code for f in findings if f.removable}
    if codes is None:
        codes = removable
    codes = set(codes)
    # images are rebuilt from pixels: all image metadata goes together
    if str(Path(path).suffix).lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
        codes = removable if codes & removable else set()
    out = out or default_safe_path(path)
    if os.path.abspath(out) == os.path.abspath(path):
        raise ValueError("Refusing to overwrite the original file.")
    _handler(path).clean(path, out, codes)
    return out


def scan_and_verify(path, out=None, codes=None):
    """Create a safe copy, rescan it, and report what is still present.

    Returns (out_path, remaining, removed_ok) where `remaining` are findings that
    the user asked to remove but are still in the copy.
    """
    before = scan(path)
    wanted = {f.code for f in before if f.removable} if codes is None else set(codes)
    out_path = clean(path, out, codes)
    after = scan(out_path)
    if str(Path(path).suffix).lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
        wanted = {f.code for f in before if f.removable}
    remaining = [f for f in after if f.code in wanted]
    return out_path, remaining, not remaining
