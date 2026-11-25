from .models import Severity

COLORS = {Severity.HIGH: "\033[31m", Severity.MEDIUM: "\033[33m", Severity.LOW: "\033[36m"}
RESET = "\033[0m"


def render(path, findings, color=False):
    lines = ["BeforeShare Report", "", f"File: {path}", ""]
    if not findings:
        lines.append("No hidden data found by the checks BeforeShare has for this file type.")
        lines.append("This is not a guarantee that the file is safe to share.")
        return "\n".join(lines)
    lines.append("Found:")
    lines.append("")
    for f in findings:
        text = str(f)
        if color:
            text = f"{COLORS[f.severity]}{text}{RESET}"
        tag = "" if f.removable else "  (review manually, cannot be removed automatically)"
        lines.append(f"  {text}{tag}")
    return "\n".join(lines)
