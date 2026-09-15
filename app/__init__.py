from fastapi import FastAPI

from app.app_factory import create_app as _create_app
from app.lifecycle import lifespan, on_shutdown, on_startup
from app.scheduler import scheduler
from app.version import __version__


def create_app() -> FastAPI:
    """Create the application and expose a dependency-free liveness endpoint."""
    app = _create_app()

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"status": "ok", "version": __version__}

    return app


__all__ = [
    "__version__",
    "create_app",
    "lifespan",
    "on_shutdown",
    "on_startup",
    "scheduler",
]
