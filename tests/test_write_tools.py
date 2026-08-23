import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from pcradio_mcp.write_tools import _alarm_payload, register_write_tools


class FakeClient:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        async def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return {"method": name}
        return method


async def registered():
    client = FakeClient()
    mcp = FastMCP("test")
    register_write_tools(mcp, client)
    return mcp, client


@pytest.mark.asyncio
async def test_registered_write_tools_delegate_every_operation():
    mcp, client = await registered()
    calls = [
        ("select_pcradio_channel", {"delta": -1}),
        ("select_pcradio_channel", {"channel": 2}),
        ("set_pcradio_eq", {"preset": 1}),
        ("set_pcradio_audio_effect", {"effect": "loudness", "enabled": True}),
        ("reload_pcradio_playlist", {}),
        ("add_pcradio_user_station", {"name": "Radio", "url": "https://x"}),
        ("play_pcradio_user_station", {"station_id": "s1"}),
        ("update_pcradio_station", {"station_id": "s1", "favorite": True}),
        ("set_pcradio_ui_preferences", {"collapsed_groups": ["time"]}),
        ("set_pcradio_time_config", {"servers": ["ntp"], "timezone": "UTC"}),
        ("create_pcradio_alarm", {
            "title": "A", "date": "2026-08-23", "station_id": "s1",
            "hour": 1, "minute": 2, "weekdays": 0, "fade_seconds": 3,
            "target_volume": 4, "enabled": False,
        }),
        ("update_pcradio_alarm", {
            "alarm_id": "a1", "revision": 1, "title": "A", "date": "",
            "station_id": "s1", "hour": 1, "minute": 2, "weekdays": 3,
            "fade_seconds": 4, "target_volume": 5, "enabled": True,
        }),
        ("delete_pcradio_alarm", {"alarm_id": "a1", "revision": 2}),
    ]
    for name, arguments in calls:
        assert await mcp.call_tool(name, arguments)
    assert len(client.calls) == len(calls)
    assert client.calls[-1] == ("delete_alarm", ("a1", 2), {})


@pytest.mark.asyncio
async def test_delete_alarm_rejects_invalid_revision():
    mcp, _ = await registered()
    with pytest.raises(ToolError, match="greater than or equal to 0"):
        await mcp.call_tool(
            "delete_pcradio_alarm", {"alarm_id": "a1", "revision": -1},
        )


@pytest.mark.asyncio
async def test_select_requires_exactly_one_selector():
    mcp, _ = await registered()
    for arguments in ({}, {"delta": 1, "channel": 2}):
        with pytest.raises(ToolError, match="exactly one"):
            await mcp.call_tool("select_pcradio_channel", arguments)


@pytest.mark.parametrize("field,value", [
    ("revision", -1), ("hour", 24), ("minute", 60), ("weekdays", 128),
    ("fade_seconds", 3601), ("target_volume", 101),
])
def test_alarm_ranges(field, value):
    values = {
        "revision": 0, "title": "A", "date": "", "station_id": "s",
        "hour": 1, "minute": 2, "weekdays": 3, "fade_seconds": 4,
        "target_volume": 5, "enabled": True,
    }
    values[field] = value
    with pytest.raises(ValueError, match=field):
        _alarm_payload(**values)


@pytest.mark.parametrize("date,weekdays,message", [
    ("", 0, "exactly one schedule"),
    ("2026-08-23", 1, "exactly one schedule"),
    ("2026-02-30", 0, "valid YYYY-MM-DD"),
    ("20260823", 0, "valid YYYY-MM-DD"),
])
def test_alarm_schedule_validation(date, weekdays, message):
    with pytest.raises(ValueError, match=message):
        _alarm_payload(
            0, "A", date, "station", 1, 2, weekdays, 3, 4, True,
        )
