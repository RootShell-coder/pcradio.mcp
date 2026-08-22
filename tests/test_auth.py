import pytest
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from pcradio_mcp.auth import BearerTokenMiddleware
from pcradio_mcp.config import Settings


async def endpoint(request: Request):
    return JSONResponse({"ok": True})


def protected_app():
    app = Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])])
    return BearerTokenMiddleware(app, "correct-token")


@pytest.mark.asyncio
async def test_valid_bearer_token_is_accepted():
    transport = httpx.ASGITransport(app=protected_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/mcp", headers={"Authorization": "Bearer correct-token"},
        )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_missing_or_invalid_bearer_token_is_rejected():
    transport = httpx.ASGITransport(app=protected_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for headers in ({}, {"Authorization": "Bearer wrong-token"}):
            response = await client.post("/mcp", headers=headers)
            assert response.status_code == 401
            assert response.json()["error"] == "invalid_token"
            assert response.headers["www-authenticate"].startswith("Bearer ")


def test_empty_environment_token_disables_authentication(monkeypatch):
    monkeypatch.setenv("MCP_BEARER_TOKEN", "  ")
    assert Settings().mcp_bearer_token is None


def test_non_empty_environment_token_enables_authentication(monkeypatch):
    monkeypatch.setenv("MCP_BEARER_TOKEN", "configured-token")
    token = Settings().mcp_bearer_token
    assert token is not None
    assert token.get_secret_value() == "configured-token"
    assert "configured-token" not in repr(Settings())


@pytest.mark.asyncio
async def test_non_http_scope_is_forwarded():
    called = []

    async def app(scope, receive, send):
        called.append(scope["type"])

    middleware = BearerTokenMiddleware(app, "token")
    await middleware({"type": "lifespan"}, None, None)
    assert called == ["lifespan"]
