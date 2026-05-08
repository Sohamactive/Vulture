from dotenv import load_dotenv
load_dotenv()  # loads .env from CWD (d:\Vulture\backend) before anything else

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.storage.db import engine, Base
import app.storage.models  # noqa: F401 — ensures all models are registered on Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Vulture API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
