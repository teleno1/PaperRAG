"""FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, index, outline, parse, pipeline, review
from app.core.config import get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    setup_logging()
    yield


app = FastAPI(
    title=f"{get_settings().project.name} API",
    description="Academic review generation API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(pipeline.router, tags=["state"])
app.include_router(parse.router, prefix="/corpus", tags=["corpus"])
app.include_router(index.router, prefix="/index", tags=["index"])
app.include_router(outline.router, prefix="/outline", tags=["outline"])
app.include_router(review.router, prefix="/review", tags=["review"])
