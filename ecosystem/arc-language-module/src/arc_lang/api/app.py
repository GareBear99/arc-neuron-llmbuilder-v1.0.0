from __future__ import annotations
from fastapi import FastAPI
from arc_lang.api.routes import router
from arc_lang.version import VERSION

app = FastAPI(title="ARC Language Module", version=VERSION)
app.include_router(router)
