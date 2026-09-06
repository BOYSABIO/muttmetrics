"""FastAPI application factory and ASGI entrypoint."""

from fastapi import FastAPI

from muttmetrics.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Build and return the API app (used by uvicorn and tests)."""
    app = FastAPI(
        title="MuttMetrics",
        version="0.1.0",
        description="Duration intelligence API - capture and priors",
    )
    app.include_router(health_router)
    return app


app = create_app()
