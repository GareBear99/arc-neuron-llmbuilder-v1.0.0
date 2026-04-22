from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from arc.api.routes import router
from arc.api.deps import startup
from arc.core.config import APP_NAME, APP_VERSION, DEMO_MODE


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEMO_MODE else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

ui_dir = Path(__file__).resolve().parents[1] / "ui"
app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
app.include_router(router)
