from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.core.exceptions import EvaluationDatasetError
from app.domain.eval.models import EvalDataset, EvalDatasetRow


def load_eval_dataset(dataset_path: str | Path) -> EvalDataset:
    path = Path(dataset_path)
    if not path.exists():
        raise EvaluationDatasetError(str(path), "Dataset file does not exist.")

    rows: list[EvalDatasetRow] = []
    for row_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationDatasetError(str(path), f"Invalid JSON on row {row_number}: {exc.msg}", row_number=row_number) from exc

        try:
            rows.append(EvalDatasetRow.model_validate(payload))
        except ValidationError as exc:
            messages = []
            for error in exc.errors():
                field = ".".join(str(item) for item in error.get("loc", [])) or "row"
                message = str(error.get("msg", "invalid value"))
                if message.startswith("Value error, "):
                    message = message[len("Value error, ") :]
                messages.append(f"{field}: {message}")
            raise EvaluationDatasetError(
                str(path),
                f"Invalid row {row_number}: {'; '.join(messages)}",
                row_number=row_number,
            ) from exc

    return EvalDataset(rows=rows)
