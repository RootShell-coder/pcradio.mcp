from typing import Annotated

import uvicorn
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .auth import BearerTokenMiddleware
from .client import PCRadioClient
from .config import Settings
from .write_tools import register_write_tools

settings = Settings()
client = PCRadioClient(settings.pcradio_base_url, settings.pcradio_timeout)
mcp = FastMCP(
    "PCRadio",
    instructions="""Control one configured PCRadio internet radio.

Use read tools before writes whenever an operation needs an ID, channel number,
alarm revision, current value, or confirmation. The main playlist uses one-based
channel numbers. The user playlist exposes a separate one-based display number,
but play_pcradio_user_station requires its opaque station ID. Alarm create, update,
and delete operations use opaque station/alarm IDs; update and delete also require
the latest alarms revision from get_pcradio_state.

Treat returned `available` as observed metadata only: null means unknown, and a
false value does not prove a later playback attempt will fail. Confirm playback
from a fresh get_pcradio_state response when the outcome matters. For an alarm,
use either a YYYY-MM-DD date with weekdays=0, or date='' with a non-zero weekday
bitmask. Do not invent IDs or revisions.

OTA/firmware update, IR control, shutdown/standby, and deleting user stations are
intentionally unavailable. Never substitute another tool for these operations.
All tools act on the single configured device; no device selector is required.""",
    host=settings.mcp_host,
    port=settings.mcp_port,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
async def get_pcradio_state() -> dict:
    """Read a fresh complete state snapshot.

    Returns identity, playback (including configured station and ICY metadata),
    audio, network, local time, alarms with the current revision, and power data.
    Read this before state-dependent writes and after playback when confirmation
    matters.
    """
    return await client.state()


@mcp.tool()
async def get_pcradio_playlist(
    query: Annotated[str | None, Field(description="Case-insensitive substring of a station name; omit to list all stations.")] = None,
    station_id: Annotated[str | None, Field(description="Exact opaque main-playlist station ID; omit unless resolving a known ID.")] = None,
    offset: Annotated[int, Field(ge=0, description="Zero-based result offset after filtering.")] = 0,
    limit: Annotated[int, Field(ge=1, le=500, description="Maximum stations to return, from 1 to 500.")] = 100,
) -> dict:
    """Search or page the main playlist.

    Each station includes an opaque ID, a one-based `number` used by
    play_pcradio, name, favorite flag, and observed availability. The returned
    total is the filtered count before pagination. If both filters are supplied,
    both must match.
    """
    return await client.playlist(
        query=query, station_id=station_id, offset=offset, limit=limit,
    )


@mcp.tool()
async def get_pcradio_user_playlist() -> dict:
    """List user-added stations without exposing stream URLs.

    Each item includes its opaque ID required by play_pcradio_user_station and a
    separate one-based user-playlist display number. A main channel, when present,
    is not the user display number.
    """
    return await client.user_playlist()


@mcp.tool()
async def play_pcradio(
    channel: Annotated[int, Field(ge=1, description="One-based `number` from get_pcradio_playlist, not a station ID or user-playlist number.")],
) -> dict:
    """Start one main-playlist station. Read fresh state afterward to confirm playback."""
    return await client.play(channel)


@mcp.tool()
async def stop_pcradio() -> dict:
    """Stop current playback without changing the selected station or audio settings."""
    return await client.stop()


@mcp.tool()
async def set_pcradio_volume(
    volume_percent: Annotated[int, Field(ge=0, le=100, description="Absolute target volume percentage from 0 through 100.")],
) -> dict:
    """Set PCRadio volume from 0 to 100 percent."""
    return await client.set_volume(volume_percent)


@mcp.tool()
async def set_pcradio_mute(
    muted: Annotated[bool, Field(description="true mutes the line output; false enables audio output.")],
) -> dict:
    """Set the PCRadio line-output mute state explicitly."""
    return await client.set_mute(muted)


register_write_tools(mcp, client)


def main() -> None:
    if settings.mcp_transport == "stdio":
        mcp.run(transport="stdio")
        return
    app = mcp.streamable_http_app()
    if settings.mcp_bearer_token is not None:
        app = BearerTokenMiddleware(
            app, settings.mcp_bearer_token.get_secret_value(),
        )
    config = uvicorn.Config(
        app, host=settings.mcp_host, port=settings.mcp_port, log_level="info",
    )
    uvicorn.Server(config).run()


if __name__ == "__main__":  # pragma: no cover - process entry point
    main()
