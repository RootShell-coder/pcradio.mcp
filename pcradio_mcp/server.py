from mcp.server.fastmcp import FastMCP

from .client import PCRadioClient
from .config import Settings
from .write_tools import register_write_tools

settings = Settings()
client = PCRadioClient(settings.pcradio_base_url, settings.pcradio_timeout)
mcp = FastMCP(
    "PCRadio",
    instructions="Read and control the configured PCRadio internet radio.",
    host=settings.mcp_host,
    port=settings.mcp_port,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
async def get_pcradio_state() -> dict:
    """Get current station, playback, audio, network, time, alarms and power state."""
    return await client.state()


@mcp.tool()
async def get_pcradio_playlist() -> dict:
    """List the stations in the main PCRadio playlist."""
    return await client.playlist()


@mcp.tool()
async def get_pcradio_user_playlist() -> dict:
    """List user-added PCRadio stations without exposing stream URLs."""
    return await client.user_playlist()


@mcp.tool()
async def play_pcradio(channel: int) -> dict:
    """Start a main-playlist station by its one-based channel number."""
    return await client.play(channel)


@mcp.tool()
async def stop_pcradio() -> dict:
    """Stop PCRadio playback."""
    return await client.stop()


@mcp.tool()
async def set_pcradio_volume(volume_percent: int) -> dict:
    """Set PCRadio volume from 0 to 100 percent."""
    return await client.set_volume(volume_percent)


@mcp.tool()
async def set_pcradio_mute(muted: bool) -> dict:
    """Mute or unmute PCRadio audio output."""
    return await client.set_mute(muted)


register_write_tools(mcp, client)


def main() -> None:
    if settings.mcp_transport == "stdio":
        mcp.run(transport="stdio")
        return
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
