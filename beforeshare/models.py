from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def label(self):
        return self.name


@dataclass(frozen=True)
class Finding:
    """One thing found in a file.

    code: stable identifier, used to choose what to remove (e.g. "xlsx.hidden_sheet").
    removable: True if `clean` can remove it from a copy.
    """
    code: str
    severity: Severity
    message: str
    removable: bool = True
    count: int = 1

    def __str__(self):
        return f"[{self.severity.label()}] {self.message}"
