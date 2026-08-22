from pydantic import SecretStr

from pcradio_mcp import server


class FakeClient:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        async def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return {"method": name}
        return method


async def test_read_and_basic_write_tools_delegate(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(server, "client", client)
    calls = [
        ("get_pcradio_state", {}),
        ("get_pcradio_playlist", {}),
        ("get_pcradio_user_playlist", {}),
        ("play_pcradio", {"channel": 2}),
        ("stop_pcradio", {}),
        ("set_pcradio_volume", {"volume_percent": 20}),
        ("set_pcradio_mute", {"muted": True}),
    ]
    for name, arguments in calls:
        assert await server.mcp.call_tool(name, arguments)
    assert [item[0] for item in client.calls] == [
        "state", "playlist", "user_playlist", "play", "stop",
        "set_volume", "set_mute",
    ]


def test_main_runs_stdio(monkeypatch):
    calls = []
    monkeypatch.setattr(server.settings, "mcp_transport", "stdio")
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    server.main()
    assert calls == [{"transport": "stdio"}]


def test_main_runs_http_without_authentication(monkeypatch):
    app = object()
    served = []
    monkeypatch.setattr(server.settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(server.settings, "mcp_bearer_token", None)
    monkeypatch.setattr(server.mcp, "streamable_http_app", lambda: app)
    monkeypatch.setattr(server.uvicorn, "Config", lambda value, **kwargs: (value, kwargs))

    class FakeServer:
        def __init__(self, config):
            served.append(config)

        def run(self):
            served.append("run")

    monkeypatch.setattr(server.uvicorn, "Server", FakeServer)
    server.main()
    assert served[0][0] is app
    assert served[1] == "run"


def test_main_wraps_http_app_when_token_is_configured(monkeypatch):
    app = object()
    configs = []
    monkeypatch.setattr(server.settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(
        server.settings, "mcp_bearer_token", SecretStr("secret"),
    )
    monkeypatch.setattr(server.mcp, "streamable_http_app", lambda: app)
    monkeypatch.setattr(server.uvicorn, "Config", lambda value, **kwargs: configs.append(value) or value)
    monkeypatch.setattr(server.uvicorn, "Server", lambda config: type("S", (), {"run": lambda self: None})())
    server.main()
    assert isinstance(configs[0], server.BearerTokenMiddleware)
    assert configs[0].app is app
