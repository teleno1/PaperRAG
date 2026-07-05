from __future__ import annotations

from pathlib import Path

CONTENT_MANIFEST_NAME = "content_list_v2.json"


def find_content_manifest(output_dir: Path) -> Path | None:
    candidates: list[Path] = []
    canonical_path = output_dir / CONTENT_MANIFEST_NAME
    if canonical_path.exists() and canonical_path.stat().st_size > 0:
        candidates.append(canonical_path)

    for candidate in output_dir.glob(f"*_{CONTENT_MANIFEST_NAME}"):
        if candidate.is_file() and candidate.stat().st_size > 0:
            candidates.append(candidate)

    if not candidates:
        return None

    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
