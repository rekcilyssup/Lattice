from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.health import router as health_router
from app.api.workspaces import router as workspaces_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.db.migrate import run_migrations_with_retry


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure schema exists even if developer forgot to run manual migration.
    run_migrations_with_retry()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.CORS_ORIGIN],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    app.include_router(health_router, prefix=settings.API_BASE_PATH)
    app.include_router(workspaces_router, prefix=settings.API_BASE_PATH)
    app.include_router(documents_router, prefix=settings.API_BASE_PATH)
    app.include_router(chat_router, prefix=settings.API_BASE_PATH)

    return app


app = create_app()
