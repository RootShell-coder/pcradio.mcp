import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from .normalize import normalize_playlist, normalize_state, normalize_user_playlist


class PCRadioAPIError(RuntimeError):
    """A device API error that keeps its HTTP status and safe response details."""

    def __init__(
        self, method: str, path: str, status_code: int, reason: str,
        *, code: str | None = None, message: str | None = None,
        details: Any = None,
    ) -> None:
        self.method = method
        self.path = path
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        parts = [f"PCRadio API {method} {path} failed: HTTP {status_code} {reason}"]
        if code:
            parts.append(f"code={code}")
        if message:
            parts.append(f"message={message}")
        if details not in (None, "", {}, []):
            parts.append(f"details={details}")
        super().__init__("; ".join(parts))


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
        if response.is_error:
            code = message = None
            details: Any = None
            try:
                error = response.json()
            except ValueError:
                error = None
            if isinstance(error, dict):
                code_value = error.get("code") or error.get("error")
                message_value = error.get("message") or error.get("detail")
                code = str(code_value) if code_value is not None else None
                message = str(message_value) if message_value is not None else None
                details = {
                    key: value for key, value in error.items()
                    if key not in {"code", "error", "message", "detail"}
                }
            else:
                text = response.text.strip()
                message = text[:1000] if text else None
            raise PCRadioAPIError(
                method, path, response.status_code, response.reason_phrase,
                code=code, message=message, details=details,
            )
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

    async def playlist(
        self, query: str | None = None, station_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> dict[str, Any]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        result = normalize_playlist(await self._request("GET", "/api/playlist"))
        stations = result["stations"]
        if station_id is not None:
            stations = [station for station in stations if station.get("id") == station_id]
        if query is not None and query.strip():
            needle = query.strip().casefold()
            stations = [
                station for station in stations
                if needle in str(station.get("name") or "").casefold()
            ]
        total = len(stations)
        return {
            "stations": stations[offset:offset + limit],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def user_playlist(self) -> dict[str, Any]:
        return normalize_user_playlist(
            await self._request("GET", "/api/user-playlist")
        )

    async def top_stations(self, limit: int = 30) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        main = (await self.playlist(limit=500))["stations"]
        user = (await self.user_playlist())["stations"]
        stations = [{**item, "source": "main"} for item in main]
        ids = {item.get("id") for item in stations}
        stations.extend(
            {**item, "source": "user"}
            for item in user
            if item.get("id") not in ids
        )
        ranked = sorted(
            (item for item in stations if (item.get("play_count") or 0) > 0),
            key=lambda item: (-(item.get("play_count") or 0), item.get("number") or 0),
        )[:limit]
        return {"stations": ranked, "total": len(ranked), "limit": limit}

    async def alarms(self) -> dict[str, Any]:
        return await self._request("GET", "/api/alarms?page=1&page_size=100")

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
        if not 0 <= preset <= 9:
            raise ValueError("preset must be between 0 and 9")
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

    async def ui_preferences(self) -> dict[str, Any]:
        return await self._request("GET", "/api/ui/preferences")

    async def set_time_config(self, servers: list[str], timezone: str) -> dict[str, Any]:
        if not servers or any(not item.strip() for item in servers):
            raise ValueError("servers must contain at least one non-empty NTP server")
        if not timezone.strip():
            raise ValueError("timezone must not be empty")
        return await self._request(
            "POST", "/api/time/config", json={"servers": servers, "timezone": timezone},
        )

    async def time_config(self) -> dict[str, Any]:
        return await self._request("GET", "/api/time/config")

    async def save_alarm(self, alarm: dict[str, Any], *, update: bool) -> dict[str, Any]:
        return await self._request("PUT" if update else "POST", "/api/alarms", json=alarm)

    async def create_alarm(self, alarm: dict[str, Any]) -> dict[str, Any]:
        alarm = {**alarm, "revision": (await self.alarms()).get("revision")}
        if not isinstance(alarm["revision"], int):
            raise ValueError("PCRadio alarm list did not return an integer revision")
        return await self.save_alarm(alarm, update=False)

    async def delete_user_station(self, station_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", "/api/user-playlist", json={"id": station_id},
        )

    async def delete_alarm(self, alarm_id: str, revision: int) -> dict[str, Any]:
        path = f"/api/alarms?id={quote(alarm_id, safe='')}&revision={revision}"
        return await self._request("DELETE", path)
