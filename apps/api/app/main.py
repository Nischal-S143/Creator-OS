from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.health import router as health_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.brand_brain import router as brand_brain_router
from app.api.v1.brands import router as brands_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.content import router as content_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.learning import router as learning_router
from app.api.v1.organizations import router as organizations_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    public_docs = get_settings().app_env == "development"
    app = FastAPI(
        title="CreatorOS",
        docs_url="/docs" if public_docs else None,
        redoc_url="/redoc" if public_docs else None,
        openapi_url="/openapi.json" if public_docs else None,
    )

    @app.exception_handler(OperationalError)
    async def database_unavailable(_request: Request, _exc: OperationalError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "The service is temporarily unavailable. Try again shortly."}
        )

    app.include_router(health_router)
    app.include_router(ai_router)
    app.include_router(auth_router)
    app.include_router(organizations_router)
    app.include_router(brands_router)
    app.include_router(brand_brain_router)
    app.include_router(campaigns_router)
    app.include_router(content_router)
    app.include_router(intelligence_router)
    app.include_router(learning_router)
    return app


app = create_app()
