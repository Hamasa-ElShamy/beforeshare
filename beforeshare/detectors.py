"""Text detectors for secrets and personal data. Rule based, no AI model.

These are heuristics. They will miss things and can flag harmless text.
"""
import re
from .models import Finding, Severity

_SECRET_RULES = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Password assignment", re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key)\s*[:=]\s*\S{4,}")),
]
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)\d{3,4}[\s-]?\d{3,4}(?!\d)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_EG_NID = re.compile(r"(?<!\d)[23]\d{13}(?!\d)")  # Egyptian national ID: 14 digits


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def scan_text(text: str, prefix: str):
    """Return findings for secrets and personal data in `text`."""
    out = []
    if not text:
        return out
    for name, rx in _SECRET_RULES:
        n = len(rx.findall(text))
        if n:
            out.append(Finding(f"{prefix}.secret", Severity.HIGH,
                               f"Possible secret in content: {name} (x{n})", removable=False, count=n))
    cards = [re.sub(r"\D", "", m.group()) for m in _CARD.finditer(text)]
    cards = [c for c in cards if 13 <= len(c) <= 19 and _luhn(c)]
    if cards:
        out.append(Finding(f"{prefix}.card", Severity.HIGH,
                           f"Possible payment card number(s) in content (x{len(cards)})", removable=False, count=len(cards)))
    nids = _EG_NID.findall(text)
    if nids:
        out.append(Finding(f"{prefix}.national_id", Severity.HIGH,
                           f"Possible 14-digit national ID number(s) in content (x{len(nids)})", removable=False, count=len(nids)))
    emails = set(_EMAIL.findall(text))
    if emails:
        out.append(Finding(f"{prefix}.email", Severity.MEDIUM,
                           f"{len(emails)} email address(es) in content", removable=False, count=len(emails)))
    phones = [p for p in _PHONE.findall(text) if len(re.sub(r"\D", "", p)) >= 9]
    if phones and not nids and not cards:
        out.append(Finding(f"{prefix}.phone", Severity.LOW,
                           f"Possible phone number(s) in content (x{len(phones)})", removable=False, count=len(phones)))
    return out
