import httpx
import pytest

from pcradio_mcp.client import PCRadioAPIError, PCRadioClient


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
    await client.step(1, 63)
    await client.set_eq(2)
    await client.set_effect("loudness", True)
    await client.add_user_station("Jazz", "https://radio.example/stream")
    await client.set_time_config(["pool.ntp.org"], "Europe/Moscow")
    assert calls == [
        ("POST", "/api/player/step", {"delta": -1}, None),
        ("POST", "/api/player/step", {"delta": 1, "channel": 63}, None),
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
async def test_http_error_includes_structured_device_details(monkeypatch):
    class FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def request(self, *args, **kwargs):
            return httpx.Response(
                409,
                json={
                    "error": "revision_conflict",
                    "message": "Expected revision 8, received 0",
                    "current_revision": 8,
                },
                request=httpx.Request("POST", "http://radio/api/alarms"),
            )

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeAsyncClient())
    with pytest.raises(PCRadioAPIError) as caught:
        await PCRadioClient("http://radio").playlist()
    error = caught.value
    assert error.status_code == 409
    assert error.code == "revision_conflict"
    assert error.details == {"current_revision": 8}
    assert "Expected revision 8, received 0" in str(error)
    assert "HTTP 409 Conflict" in str(error)


@pytest.mark.asyncio
async def test_create_alarm_fetches_current_revision(monkeypatch):
    calls = []

    async def fake_request(self, method, path, *, json=None, content=None):
        calls.append((method, path, json))
        if method == "GET":
            return {"alarms": [], "revision": 8}
        return {"status": "success", "id": "alarm-1", "revision": 9}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    result = await PCRadioClient("http://radio").create_alarm({"title": "Test"})
    assert result["revision"] == 9
    assert calls == [
        ("GET", "/api/alarms?page=1&page_size=100", None),
        ("POST", "/api/alarms", {"title": "Test", "revision": 8}),
    ]


@pytest.mark.asyncio
async def test_eq_rejects_unknown_preset():
    with pytest.raises(ValueError, match="between 0 and 9"):
        await PCRadioClient("http://radio").set_eq(10)


@pytest.mark.asyncio
async def test_playlist_can_find_one_station_by_exact_id(monkeypatch):
    async def fake_request(*_args, **_kwargs):
        return {"stations": [
            {"id": "first", "number": 1, "name": "First"},
            {"id": "wanted", "number": 4163, "name": "Romantika"},
        ]}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    result = await PCRadioClient("http://radio").playlist(station_id="wanted", limit=1)

    assert result["total"] == 1
    assert result["stations"] == [{
        "id": "wanted", "number": 4163, "name": "Romantika",
        "favorite": None, "available": None,
    }]


@pytest.mark.asyncio
async def test_all_remaining_successful_client_operations(monkeypatch):
    calls = []

    async def fake_request(self, method, path, *, json=None, content=None):
        calls.append((method, path, json, content))
        return {"revision": 3}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    client = PCRadioClient("http://radio/")
    assert client.base_url == "http://radio"
    await client.alarms()
    await client.reload_playlist()
    await client.play_user_station("station-1")
    await client.update_station(
        "station-1", name="New", favorite=True, play_count=7,
    )
    await client.set_ui_preferences(["time"])
    await client.ui_preferences()
    await client.time_config()
    await client.save_alarm({"id": "alarm-1"}, update=True)
    await client.delete_user_station("station-1")
    await client.delete_alarm("alarm/1", 3)
    assert calls == [
        ("GET", "/api/alarms?page=1&page_size=100", None, None),
        ("POST", "/api/playlist/reload", {}, None),
        ("POST", "/api/user-playlist/play", {"id": "station-1"}, None),
        ("POST", "/api/station/stats", {
            "id": "station-1", "name": "New", "favorite": True,
            "play_count": 7,
        }, None),
        ("POST", "/api/ui/preferences", {"collapsed_groups": ["time"]}, None),
        ("GET", "/api/ui/preferences", None, None),
        ("GET", "/api/time/config", None, None),
        ("PUT", "/api/alarms", {"id": "alarm-1"}, None),
        ("DELETE", "/api/user-playlist", {"id": "station-1"}, None),
        ("DELETE", "/api/alarms?id=alarm%2F1&revision=3", None, None),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation, message", [
    (lambda client: client.play(0), "at least 1"),
    (lambda client: client.step(0), "not zero"),
    (lambda client: client.step(1, 0), "channel must"),
    (lambda client: client.set_effect("unknown", True), "unknown audio effect"),
    (lambda client: client.add_user_station(" ", "https://x"), "name must"),
    (lambda client: client.add_user_station("x", "ftp://x"), "url must"),
    (lambda client: client.update_station(
        "x", name=None, favorite=None, play_count=None,
    ), "at least one"),
    (lambda client: client.update_station(
        "x", name=None, favorite=None, play_count=-1,
    ), "uint32"),
    (lambda client: client.set_ui_preferences(["invalid"]), "unknown UI"),
    (lambda client: client.set_time_config([], "UTC"), "at least one"),
    (lambda client: client.set_time_config(["pool.ntp.org"], " "), "timezone"),
])
async def test_client_validation_errors(operation, message):
    with pytest.raises(ValueError, match=message):
        await operation(PCRadioClient("http://radio"))


@pytest.mark.asyncio
async def test_playlist_search_and_pagination(monkeypatch):
    async def fake_request(self, method, path, *, json=None, content=None):
        return {"stations": [
            {"id": "1", "name": "Relax FM"},
            {"id": "2", "name": "Rock FM"},
            {"id": "3", "name": None},
        ]}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    client = PCRadioClient("http://radio")
    result = await client.playlist(query=" relax ", offset=0, limit=1)
    assert result == {
        "stations": [{
            "id": "1", "number": None, "name": "Relax FM",
            "favorite": None, "available": None,
        }],
        "total": 1, "offset": 0, "limit": 1,
    }
    assert (await client.playlist(query=" ", offset=1, limit=2))["total"] == 3
    assert (await client.playlist())["total"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments,message", [
    ({"offset": -1}, "non-negative"),
    ({"limit": 0}, "between 1 and 500"),
])
async def test_playlist_pagination_validation(arguments, message):
    with pytest.raises(ValueError, match=message):
        await PCRadioClient("http://radio").playlist(**arguments)


@pytest.mark.asyncio
async def test_create_alarm_requires_revision(monkeypatch):
    async def fake_request(self, method, path, *, json=None, content=None):
        return {"alarms": []}

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    with pytest.raises(ValueError, match="integer revision"):
        await PCRadioClient("http://radio").create_alarm({})


class ResponseClient:
    response = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def request(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_empty_success_response(monkeypatch):
    ResponseClient.response = httpx.Response(
        204, request=httpx.Request("POST", "http://radio/api"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: ResponseClient())
    assert await PCRadioClient("http://radio").stop() == {"ok": True}


@pytest.mark.asyncio
async def test_object_success_response(monkeypatch):
    ResponseClient.response = httpx.Response(
        200, json={"status": "success"},
        request=httpx.Request("POST", "http://radio/api"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: ResponseClient())
    assert await PCRadioClient("http://radio").stop() == {"status": "success"}


@pytest.mark.asyncio
async def test_non_object_success_response_is_rejected(monkeypatch):
    ResponseClient.response = httpx.Response(
        200, json=[], request=httpx.Request("GET", "http://radio/api"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: ResponseClient())
    with pytest.raises(ValueError, match="non-object"):
        await PCRadioClient("http://radio").playlist()


@pytest.mark.asyncio
@pytest.mark.parametrize("body, expected", [
    ("device is busy", "device is busy"),
    ("", None),
])
async def test_plain_text_http_error(monkeypatch, body, expected):
    ResponseClient.response = httpx.Response(
        503, text=body, request=httpx.Request("GET", "http://radio/api"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: ResponseClient())
    with pytest.raises(PCRadioAPIError) as caught:
        await PCRadioClient("http://radio").playlist()
    assert caught.value.message == expected


@pytest.mark.asyncio
async def test_empty_structured_http_error(monkeypatch):
    ResponseClient.response = httpx.Response(
        409, json={}, request=httpx.Request("GET", "http://radio/api"),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: ResponseClient())
    with pytest.raises(PCRadioAPIError) as caught:
        await PCRadioClient("http://radio").playlist()
    assert caught.value.code is None
    assert caught.value.message is None
    assert caught.value.details == {}
    assert str(caught.value) == (
        "PCRadio API GET /api/playlist failed: HTTP 409 Conflict"
    )

@pytest.mark.asyncio
async def test_user_playlist_is_normalized_without_stream_urls(monkeypatch):
    async def fake_request(self, method, path, *, json=None, content=None):
        assert (method, path) == ("GET", "/api/user-playlist")
        return {
            "count": 1,
            "stations": [{
                "id": "user-1",
                "user_number": 7,
                "name": "My Radio",
                "url": "https://secret.example/stream",
                "favorite": True,
                "availability_confirmed": True,
                "in_main": False,
                "main_channel": None,
                "play_count": 3,
            }],
        }

    monkeypatch.setattr(PCRadioClient, "_request", fake_request)
    result = await PCRadioClient("http://radio").user_playlist()

    assert result["total"] == 1
    assert result["stations"] == [{
        "id": "user-1",
        "number": 7,
        "name": "My Radio",
        "favorite": True,
        "available": True,
        "in_main_playlist": False,
        "main_channel": None,
        "play_count": 3,
    }]
