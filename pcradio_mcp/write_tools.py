from datetime import date as calendar_date
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import PCRadioClient


Channel = Annotated[int, Field(ge=1, le=100000, description="One-based main-playlist channel number.")]
StationId = Annotated[str, Field(min_length=1, description="Opaque station ID returned by a playlist read tool; never use its display number here.")]
AlarmId = Annotated[str, Field(min_length=1, description="Opaque alarm ID from get_pcradio_state alarms.items.")]
Revision = Annotated[int, Field(ge=0, le=2**63 - 1, description="Latest alarms.revision from a fresh get_pcradio_state call.")]
Hour = Annotated[int, Field(ge=0, le=23, description="Local hour in 24-hour time, from 0 through 23.")]
Minute = Annotated[int, Field(ge=0, le=59, description="Minute from 0 through 59.")]
Weekdays = Annotated[int, Field(
    ge=0, le=127,
    description="Recurrence bitmask: Sunday=1, Monday=2, Tuesday=4, Wednesday=8, Thursday=16, Friday=32, Saturday=64. Use 0 for a one-time dated alarm, 62 for weekdays, or 65 for weekends.",
)]
FadeSeconds = Annotated[int, Field(ge=0, le=3600, description="Seconds used to ramp volume up to target_volume.")]
TargetVolume = Annotated[int, Field(ge=0, le=100, description="Final alarm volume percentage.")]
AlarmDate = Annotated[str, Field(description="YYYY-MM-DD for a one-time alarm, or an empty string for a recurring weekday alarm.")]


def register_write_tools(mcp: FastMCP, client: PCRadioClient) -> None:
    @mcp.tool()
    async def select_pcradio_channel(
        delta: Annotated[int | None, Field(ge=-100000, le=100000, description="Non-zero relative step; use 1 for next or -1 for previous. Mutually exclusive with channel.")] = None,
        channel: Annotated[Channel | None, Field(description="Explicit one-based main-playlist channel. Mutually exclusive with delta.")] = None,
    ) -> dict:
        """Move relative to the current main channel or select an explicit one.

        Supply exactly one argument. Prefer play_pcradio for a known absolute
        main-playlist channel; use this tool primarily for next/previous navigation.
        """
        if (delta is None) == (channel is None):
            raise ValueError("provide exactly one of delta or channel")
        if delta is not None:
            return await client.step(delta)
        return await client.step(1, channel)

    @mcp.tool()
    async def set_pcradio_eq(
        preset: Annotated[int, Field(ge=0, le=9, description="Equalizer preset index from 0 through 9.")],
    ) -> dict:
        """Select one PCRadio equalizer preset by its numeric index."""
        return await client.set_eq(preset)

    @mcp.tool()
    async def set_pcradio_audio_effect(
        effect: Annotated[Literal["loudness", "fft_denoise", "stereo_wide"], Field(description="Exact DSP effect identifier.")],
        enabled: Annotated[bool, Field(description="true enables the selected effect; false disables it.")],
    ) -> dict:
        """Enable or disable one PCRadio DSP audio effect."""
        return await client.set_effect(effect, enabled)

    @mcp.tool()
    async def reload_pcradio_playlist() -> dict:
        """Start reloading the main playlist. Playback must be stopped."""
        return await client.reload_playlist()

    @mcp.tool()
    async def add_pcradio_user_station(
        name: Annotated[str, Field(min_length=1, description="Display name for the new user station.")],
        url: Annotated[str, Field(min_length=1, description="Direct HTTP or HTTPS audio stream URL.")],
    ) -> dict:
        """Add an HTTP or HTTPS audio stream to the user playlist."""
        return await client.add_user_station(name, url)

    @mcp.tool()
    async def play_pcradio_user_station(station_id: StationId) -> dict:
        """Start a user-playlist station by opaque ID from get_pcradio_user_playlist.

        Do not pass the one-based user display number. Read fresh state afterward
        to confirm playback when the outcome matters.
        """
        return await client.play_user_station(station_id)

    @mcp.tool()
    async def update_pcradio_station(
        station_id: StationId,
        name: Annotated[str | None, Field(min_length=1, description="New display name; omit to keep the current name.")] = None,
        favorite: Annotated[bool | None, Field(description="New favorite flag; omit to keep it unchanged.")] = None,
        play_count: Annotated[int | None, Field(ge=0, le=4294967295, description="New local play counter; omit to keep it unchanged.")] = None,
    ) -> dict:
        """Change one or more mutable fields of a station identified by opaque ID."""
        return await client.update_station(
            station_id, name=name, favorite=favorite, play_count=play_count,
        )

    @mcp.tool()
    async def set_pcradio_ui_preferences(
        collapsed_groups: Annotated[list[Literal["favorites", "playlist", "top", "equalizer", "update", "channel", "time"]], Field(description="Complete list of WebUI groups that should be collapsed.")],
    ) -> dict:
        """Replace the complete list of collapsed PCRadio WebUI groups."""
        return await client.set_ui_preferences(collapsed_groups)

    @mcp.tool()
    async def set_pcradio_time_config(
        servers: Annotated[list[str], Field(min_length=1, description="Complete non-empty list of NTP hostnames.")],
        timezone: Annotated[str, Field(min_length=1, description="Device-supported timezone, for example Europe/Moscow, UTC, or +0300.")],
    ) -> dict:
        """Replace NTP servers and the PCRadio timezone configuration."""
        return await client.set_time_config(servers, timezone)

    @mcp.tool()
    async def create_pcradio_alarm(
        title: Annotated[str, Field(min_length=1, description="Human-readable alarm name.")],
        date: AlarmDate, station_id: StationId, hour: Hour, minute: Minute,
        weekdays: Weekdays, fade_seconds: FadeSeconds,
        target_volume: TargetVolume,
        enabled: Annotated[bool, Field(description="Whether the alarm is active after creation.")],
    ) -> dict:
        """Create a complete alarm record.

        Use exactly one schedule form: date=YYYY-MM-DD and weekdays=0 for a
        one-time alarm, or date='' and a non-zero weekdays bitmask for recurrence.
        Use a station ID obtained from a playlist tool. The server reads the latest
        optimistic-lock revision immediately before creation.
        """
        alarm = _alarm_payload(
            0, title, date, station_id, hour, minute, weekdays,
            fade_seconds, target_volume, enabled,
        )
        return await client.create_alarm(alarm)

    @mcp.tool()
    async def update_pcradio_alarm(
        alarm_id: AlarmId, revision: Revision,
        title: Annotated[str, Field(min_length=1, description="Complete alarm title, including an unchanged current value.")],
        date: AlarmDate, station_id: StationId, hour: Hour, minute: Minute,
        weekdays: Weekdays, fade_seconds: FadeSeconds,
        target_volume: TargetVolume,
        enabled: Annotated[bool, Field(description="Complete enabled state.")],
    ) -> dict:
        """Replace a complete alarm using its ID and current revision.

        This is not a patch operation. First call get_pcradio_state, copy every
        current alarm field, change only the requested values, and pass the latest
        alarms.revision. Preserve the date-versus-weekdays schedule invariant.
        """
        alarm = _alarm_payload(
            revision, title, date, station_id, hour, minute, weekdays,
            fade_seconds, target_volume, enabled,
        )
        alarm["id"] = alarm_id
        return await client.save_alarm(alarm, update=True)

    @mcp.tool()
    async def delete_pcradio_alarm(alarm_id: AlarmId, revision: Revision) -> dict:
        """Permanently delete one alarm using its opaque ID and latest revision.

        Call get_pcradio_state immediately before deletion. This tool deletes one
        alarm only; deleting all alarms requires explicit repeated calls with a
        freshly read revision after each deletion.
        """
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
