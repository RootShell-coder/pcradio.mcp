import asyncio
from typing import Any

import httpx

from .normalize import normalize_playlist, normalize_state, normalize_user_playlist


class PCRadioClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None,
        content: str | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.request(
                method,
                path,
                json=json,
                content=content,
                headers={"Content-Type": "text/plain"} if content is not None else None,
            )
        response.raise_for_status()
        if not response.content:
            return {"ok": True}
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"PCRadio returned a non-object for {path}")
        return payload

    async def state(self) -> dict[str, Any]:
        paths = {
            "identity": "/api/device/identity",
            "player": "/api/player/state",
            "time": "/api/time/status",
            "alarms": "/api/alarms?page=1&page_size=100",
            "power": "/api/power",
        }
        values = await asyncio.gather(*(self._request("GET", path) for path in paths.values()))
        return normalize_state(dict(zip(paths, values, strict=True)))

    async def playlist(self) -> dict[str, Any]:
        return normalize_playlist(await self._request("GET", "/api/playlist"))

    async def user_playlist(self) -> dict[str, Any]:
        return normalize_user_playlist(
            await self._request("GET", "/api/user-playlist")
        )

    async def play(self, channel: int) -> dict[str, Any]:
        if channel < 1:
            raise ValueError("channel must be at least 1")
        return await self._request("POST", "/api/player/play", json={"channel": channel})

    async def stop(self) -> dict[str, Any]:
        return await self._request("POST", "/api/player/stop", json={})

    async def set_volume(self, volume_percent: int) -> dict[str, Any]:
        if not 0 <= volume_percent <= 100:
            raise ValueError("volume_percent must be between 0 and 100")
        return await self._request("POST", "/api/volume", content=str(volume_percent))

    async def set_mute(self, muted: bool) -> dict[str, Any]:
        return await self._request("POST", "/api/mute", content=str(muted).lower())

    async def step(self, delta: int, channel: int | None = None) -> dict[str, Any]:
        if delta == 0 or not -100000 <= delta <= 100000:
            raise ValueError("delta must be between -100000 and 100000 and not zero")
        body: dict[str, Any] = {"delta": delta}
        if channel is not None:
            if not 1 <= channel <= 100000:
                raise ValueError("channel must be between 1 and 100000")
            body["channel"] = channel
        return await self._request("POST", "/api/player/step", json=body)

    async def set_eq(self, preset: int) -> dict[str, Any]:
        if preset < 0:
            raise ValueError("preset must be non-negative")
        return await self._request("POST", "/api/eq", content=str(preset))

    async def set_effect(self, effect: str, enabled: bool) -> dict[str, Any]:
        paths = {
            "loudness": "/api/loudness",
            "fft_denoise": "/api/fft-denoise",
            "stereo_wide": "/api/stereo-wide",
        }
        if effect not in paths:
            raise ValueError(f"unknown audio effect: {effect}")
        return await self._request("POST", paths[effect], content="1" if enabled else "0")

    async def reload_playlist(self) -> dict[str, Any]:
        return await self._request("POST", "/api/playlist/reload", json={})

    async def add_user_station(self, name: str, url: str) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("name must not be empty")
        if not url.startswith(("http://", "https://")):
            raise ValueError("url must use http or https")
        return await self._request(
            "POST", "/api/user-playlist", json={"name": name, "url": url},
        )

    async def play_user_station(self, station_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/user-playlist/play", json={"id": station_id},
        )

    async def update_station(
        self, station_id: str, *, name: str | None, favorite: bool | None,
        play_count: int | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"id": station_id}
        if name is not None:
            body["name"] = name
        if favorite is not None:
            body["favorite"] = favorite
        if play_count is not None:
            if not 0 <= play_count <= 4294967295:
                raise ValueError("play_count is outside uint32 range")
            body["play_count"] = play_count
        if len(body) == 1:
            raise ValueError("at least one station field must be supplied")
        return await self._request("POST", "/api/station/stats", json=body)

    async def set_ui_preferences(self, collapsed_groups: list[str]) -> dict[str, Any]:
        allowed = {"favorites", "playlist", "top", "equalizer", "update", "channel", "time"}
        if invalid := set(collapsed_groups) - allowed:
            raise ValueError(f"unknown UI groups: {sorted(invalid)}")
        return await self._request(
            "POST", "/api/ui/preferences", json={"collapsed_groups": collapsed_groups},
        )

    async def set_time_config(self, servers: list[str], timezone: str) -> dict[str, Any]:
        if not servers or any(not item.strip() for item in servers):
            raise ValueError("servers must contain at least one non-empty NTP server")
        if not timezone.strip():
            raise ValueError("timezone must not be empty")
        return await self._request(
            "POST", "/api/time/config", json={"servers": servers, "timezone": timezone},
        )

    async def save_alarm(self, alarm: dict[str, Any], *, update: bool) -> dict[str, Any]:
        return await self._request("PUT" if update else "POST", "/api/alarms", json=alarm)
