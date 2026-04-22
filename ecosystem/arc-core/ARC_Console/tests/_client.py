import httpx
from arc.api.main import app


def make_transport():
    return httpx.ASGITransport(app=app)
