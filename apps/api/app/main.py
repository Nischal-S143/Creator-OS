from fastapi import FastAPI

from app.api.v1.ai import router as ai_router
from app.config import get_settings
from app.health import router as health_router


def create_app() -> FastAPI:
    public_docs = get_settings().app_env == "development"
    app = FastAPI(
        title="CreatorOS",
        docs_url="/docs" if public_docs else None,
        redoc_url="/redoc" if public_docs else None,
        openapi_url="/openapi.json" if public_docs else None,
    )
    app.include_router(health_router)
    app.include_router(ai_router)
    return app


app = create_app()
