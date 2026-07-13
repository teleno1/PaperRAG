"""Same-origin delivery for the compiled Research Workspace browser app."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
router = APIRouter()


def _index_response() -> Response:
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "frontend_not_built",
                "detail": "Build the frontend with `npm run build` before starting the production app.",
            },
        )
    return FileResponse(index_path)


@router.get("/", include_in_schema=False)
def frontend_index() -> Response:
    return _index_response()


@router.get("/{path:path}", include_in_schema=False)
def frontend_route(path: str) -> Response:
    """Serve an asset or fall back to index.html for client-side routes."""

    if path == "api" or path.startswith(("api/", "corpus/", "index/", "outline/", "query/", "report/", "eval/", "review/")):
        raise HTTPException(status_code=404, detail="Not Found")

    requested_path = (FRONTEND_DIST / path).resolve()
    try:
        requested_path.relative_to(FRONTEND_DIST.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not Found") from exc

    if requested_path.is_file():
        return FileResponse(requested_path)
    if Path(path).suffix:
        raise HTTPException(status_code=404, detail="Not Found")
    return _index_response()
