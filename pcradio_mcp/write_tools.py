from datetime import date as calendar_date
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .client import PCRadioClient


def register_write_tools(mcp: FastMCP, client: PCRadioClient) -> None:
    @mcp.tool()
    async def select_pcradio_channel(
        delta: int | None = None, channel: int | None = None,
    ) -> dict:
        """Move by a non-zero delta, or select one explicit one-based channel."""
        if (delta is None) == (channel is None):
            raise ValueError("provide exactly one of delta or channel")
        if delta is not None:
            return await client.step(delta)
        return await client.step(1, channel)

    @mcp.tool()
    async def set_pcradio_eq(preset: int) -> dict:
        """Select a non-negative PCRadio equalizer preset index."""
        return await client.set_eq(preset)

    @mcp.tool()
    async def set_pcradio_audio_effect(
        effect: Literal["loudness", "fft_denoise", "stereo_wide"], enabled: bool,
    ) -> dict:
        """Enable or disable one PCRadio DSP audio effect."""
        return await client.set_effect(effect, enabled)

    @mcp.tool()
    async def reload_pcradio_playlist() -> dict:
        """Start reloading the main playlist. Playback must be stopped."""
        return await client.reload_playlist()

    @mcp.tool()
    async def add_pcradio_user_station(name: str, url: str) -> dict:
        """Add an HTTP or HTTPS stream to the user playlist."""
        return await client.add_user_station(name, url)

    @mcp.tool()
    async def play_pcradio_user_station(station_id: str) -> dict:
        """Start a user-playlist station by its ID."""
        return await client.play_user_station(station_id)

    @mcp.tool()
    async def update_pcradio_station(
        station_id: str,
        name: str | None = None,
        favorite: bool | None = None,
        play_count: int | None = None,
    ) -> dict:
        """Change a station name, favorite flag, and/or local play count."""
        return await client.update_station(
            station_id, name=name, favorite=favorite, play_count=play_count,
        )

    @mcp.tool()
    async def set_pcradio_ui_preferences(collapsed_groups: list[str]) -> dict:
        """Save the list of collapsed PCRadio WebUI groups."""
        return await client.set_ui_preferences(collapsed_groups)

    @mcp.tool()
    async def set_pcradio_time_config(servers: list[str], timezone: str) -> dict:
        """Set NTP servers and an IANA timezone such as Europe/Moscow."""
        return await client.set_time_config(servers, timezone)

    @mcp.tool()
    async def create_pcradio_alarm(
        title: str, date: str, station_id: str, hour: int, minute: int,
        weekdays: int, fade_seconds: int, target_volume: int, enabled: bool,
    ) -> dict:
        """Create an alarm using the device's current revision. Date may be empty."""
        alarm = _alarm_payload(
            0, title, date, station_id, hour, minute, weekdays,
            fade_seconds, target_volume, enabled,
        )
        return await client.create_alarm(alarm)

    @mcp.tool()
    async def update_pcradio_alarm(
        alarm_id: str, revision: int, title: str, date: str, station_id: str,
        hour: int, minute: int, weekdays: int, fade_seconds: int,
        target_volume: int, enabled: bool,
    ) -> dict:
        """Update an alarm using its ID and current optimistic-lock revision."""
        alarm = _alarm_payload(
            revision, title, date, station_id, hour, minute, weekdays,
            fade_seconds, target_volume, enabled,
        )
        alarm["id"] = alarm_id
        return await client.save_alarm(alarm, update=True)

    @mcp.tool()
    async def delete_pcradio_alarm(alarm_id: str, revision: int) -> dict:
        """Delete an alarm using its ID and current optimistic-lock revision."""
        if not 0 <= revision <= 2**63 - 1:
            raise ValueError("revision must be between 0 and 9223372036854775807")
        return await client.delete_alarm(alarm_id, revision)


def _alarm_payload(
    revision: int, title: str, date: str, station_id: str, hour: int,
    minute: int, weekdays: int, fade_seconds: int, target_volume: int,
    enabled: bool,
) -> dict:
    ranges = {
        "revision": (revision, 0, 2**63 - 1),
        "hour": (hour, 0, 23),
        "minute": (minute, 0, 59),
        "weekdays": (weekdays, 0, 127),
        "fade_seconds": (fade_seconds, 0, 3600),
        "target_volume": (target_volume, 0, 100),
    }
    for name, (value, minimum, maximum) in ranges.items():
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
    one_time = bool(date)
    recurring = weekdays != 0
    if one_time == recurring:
        raise ValueError(
            "provide exactly one schedule: date or non-zero weekdays",
        )
    if one_time:
        try:
            parsed_date = calendar_date.fromisoformat(date)
        except ValueError as error:
            raise ValueError("date must use a valid YYYY-MM-DD value") from error
        if parsed_date.isoformat() != date:
            raise ValueError("date must use a valid YYYY-MM-DD value")
    return {
        "revision": revision, "title": title, "date": date,
        "station_id": station_id, "hour": hour, "minute": minute,
        "weekdays": weekdays, "fade_seconds": fade_seconds,
        "target_volume": target_volume, "enabled": enabled,
    }
