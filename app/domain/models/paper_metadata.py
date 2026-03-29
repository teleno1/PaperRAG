from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PaperMetadata:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""

