"""
`app` package initializer.

Important: importing `app.main` has side effects (env-dependent middleware/services).
To keep library-style imports safe (e.g. scripts, unit tests), we avoid importing
the FastAPI instance at module import time.
"""

__all__ = ["app"]


def __getattr__(name: str):
    # Backwards compatible lazy import: `from app import app`
    if name == "app":
        from .main import app  # noqa: WPS433 (intentional runtime import)
        return app
    raise AttributeError(name)
