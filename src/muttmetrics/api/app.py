"""FastAPI application factory and ASGI entrypoint."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from muttmetrics.api.routes.dogs import router as dogs_router
from muttmetrics.api.routes.health import router as health_router
from muttmetrics.api.routes.owners import router as owners_router
from muttmetrics.api.routes.ping import router as ping_router
from muttmetrics.api.routes.visits import router as visits_router


def create_app() -> FastAPI:
    """Build and return the API app (used by uvicorn and tests)."""
    app = FastAPI(
        title="MuttMetrics",
        version="0.1.0",
        description="Duration intelligence API - capture and priors",
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
        """Unexpected crashes → JSON body the SPA can read (not plain text)."""
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(health_router)
    app.include_router(ping_router)
    app.include_router(visits_router)
    app.include_router(owners_router)
    app.include_router(dogs_router)
    return app


app = create_app()
