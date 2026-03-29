"""CLI package."""

__all__ = ["main"]


def __getattr__(name: str):
    if name == "main":
        from app.cli.main import main

        return main
    raise AttributeError(name)
