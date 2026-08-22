import httpx
import pytest

from pcradio_mcp.client import PCRadioClient


@pytest.mark.asyncio
async def test_state_is_normalized(monkeypatch):
    payloads = {
        "/api/device/identity": {"device_id": "radio-1", "mode": "normal"},
        "/api/player/state": {
            "status": "playing", "playback_enabled": True, "station_name": "Jazz",
            "audio": {"volume_percent": 42, "muted": False},
            "network": {"wifi_rssi_dbm": -55},
        },
        "/api/time/status": {"synchronized": True},
        "/api/alarms?page=1&page_size=100": {"alarms": [], "total": 0},
        "/api/power": {"state": "on"},
    }

    async def fake_request(self, method, path, *, json=None, content=None):
        return payloads[path]

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    state = await PCRadioClient("http://radio").state()
    assert state["playback"]["configured_station_name"] == "Jazz"
    assert state["playback"]["is_playing"] is True
    assert state["audio"]["volume_percent"] == 42
    assert state["network"]["wifi_rssi_dbm"] == -55


@pytest.mark.asyncio
async def test_volume_validation():
    client = PCRadioClient("http://radio")
    with pytest.raises(ValueError, match="between 0 and 100"):
        await client.set_volume(101)


@pytest.mark.asyncio
async def test_commands_match_device_api(monkeypatch):
    calls = []

    async def fake_request(self, method, path, *, json=None, content=None):
        calls.append((method, path, json, content))
        return {"ok": True}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    client = PCRadioClient("http://radio")
    await client.play(3)
    await client.stop()
    await client.set_volume(25)
    await client.set_mute(True)
    assert calls == [
        ("POST", "/api/player/play", {"channel": 3}, None),
        ("POST", "/api/player/stop", {}, None),
        ("POST", "/api/volume", None, "25"),
        ("POST", "/api/mute", None, "true"),
    ]


@pytest.mark.asyncio
async def test_extended_write_commands_match_openapi(monkeypatch):
    calls = []

    async def fake_request(self, method, path, *, json=None, content=None):
        calls.append((method, path, json, content))
        return {"ok": True}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    client = PCRadioClient("http://radio")
    await client.step(-1)
    await client.set_eq(2)
    await client.set_effect("loudness", True)
    await client.add_user_station("Jazz", "https://radio.example/stream")
    await client.set_time_config(["pool.ntp.org"], "Europe/Moscow")
    assert calls == [
        ("POST", "/api/player/step", {"delta": -1}, None),
        ("POST", "/api/eq", None, "2"),
        ("POST", "/api/loudness", None, "1"),
        ("POST", "/api/user-playlist", {
            "name": "Jazz", "url": "https://radio.example/stream",
        }, None),
        ("POST", "/api/time/config", {
            "servers": ["pool.ntp.org"], "timezone": "Europe/Moscow",
        }, None),
    ]


@pytest.mark.asyncio
async def test_http_error_is_propagated(monkeypatch):
    class FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def request(self, *args, **kwargs):
            return httpx.Response(503, request=httpx.Request("GET", "http://radio/api"))

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeAsyncClient())
    with pytest.raises(httpx.HTTPStatusError):
        await PCRadioClient("http://radio").playlist()
