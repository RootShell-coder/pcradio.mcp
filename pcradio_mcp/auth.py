import json
import secrets
from typing import Any


class BearerTokenMiddleware:
    """Require one static Bearer token for HTTP requests."""

    def __init__(self, app: Any, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authorization = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == b"authorization"
            ),
            "",
        )
        scheme, separator, supplied = authorization.partition(" ")
        valid = (
            separator == " "
            and scheme.lower() == "bearer"
            and secrets.compare_digest(supplied, self.token)
        )
        if not valid:
            body = json.dumps({
                "error": "invalid_token",
                "error_description": "A valid Bearer token is required",
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b'Bearer error="invalid_token"'),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)
