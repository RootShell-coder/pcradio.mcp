import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with streamable_http_client("http://pcradio-mcp:8080/mcp") as streams:
        async with ClientSession(streams[0], streams[1]) as client:
            await client.initialize()
            tools = await client.list_tools()
            state = await client.call_tool("get_pcradio_state", {})
            playlist = await client.call_tool("get_pcradio_playlist", {})
            user_playlist = await client.call_tool("get_pcradio_user_playlist", {})

    assert not state.isError, state.content
    assert not playlist.isError, playlist.content
    assert not user_playlist.isError, user_playlist.content
    names = sorted(tool.name for tool in tools.tools)
    print(f"tools/list: OK ({len(names)} tools)")
    print("get_pcradio_state: OK")
    print("get_pcradio_playlist: OK")
    print("get_pcradio_user_playlist: OK")


if __name__ == "__main__":
    asyncio.run(main())
