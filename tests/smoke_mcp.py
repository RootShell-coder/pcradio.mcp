import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with streamable_http_client("http://pcradio-mcp:8080/mcp") as streams:
        async with ClientSession(streams[0], streams[1]) as client:
            await client.initialize()
            result = await client.list_tools()
    names = sorted(tool.name for tool in result.tools)
    expected = {
        "add_pcradio_user_station",
        "create_pcradio_alarm",
        "get_pcradio_playlist",
        "get_pcradio_state",
        "play_pcradio",
        "play_pcradio_user_station",
        "reload_pcradio_playlist",
        "select_pcradio_channel",
        "set_pcradio_audio_effect",
        "set_pcradio_eq",
        "set_pcradio_mute",
        "set_pcradio_time_config",
        "set_pcradio_ui_preferences",
        "set_pcradio_volume",
        "stop_pcradio",
        "update_pcradio_alarm",
        "update_pcradio_station",
    }
    assert set(names) == expected, names
    print("MCP tools:", ", ".join(names))


if __name__ == "__main__":
    asyncio.run(main())
