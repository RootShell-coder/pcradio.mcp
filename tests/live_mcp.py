"""Destructive-but-reversible live validation for the published MCP tools."""

import asyncio
import json
import os
from datetime import date, timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


URL = os.getenv("PCRADIO_MCP_URL", "http://127.0.0.1:8081/mcp")


def data(result):
    if result.isError:
        text = " ".join(getattr(item, "text", "") for item in result.content)
        raise RuntimeError(text)
    if result.structuredContent is not None:
        return result.structuredContent.get("result", result.structuredContent)
    return json.loads(result.content[0].text)


async def main() -> None:
    passed: list[str] = []
    cleanup: dict[str, object] = {}
    async with streamable_http_client(URL) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()

            async def call(name: str, arguments=None):
                value = data(await session.call_tool(name, arguments or {}))
                passed.append(name)
                return value

            state = await call("get_pcradio_state")
            playlist = await call("get_pcradio_playlist")
            users = await call("get_pcradio_user_playlist")
            audio = state["audio"]
            playback = state["playback"]
            original_id = playback["station_id"]
            original_user = next(
                (item for item in users["stations"] if item["id"] == original_id), None,
            )
            original_main = next(
                (item for item in playlist["stations"] if item["id"] == original_id), None,
            )

            await call("play_pcradio", {"channel": 1})
            await asyncio.sleep(2)
            await call("select_pcradio_channel", {"channel": 2})
            await asyncio.sleep(2)
            await call("select_pcradio_channel", {"delta": 1})
            await asyncio.sleep(2)

            volume = audio["volume_percent"]
            await call("set_pcradio_volume", {"volume_percent": 30 if volume != 30 else 31})
            await call("set_pcradio_volume", {"volume_percent": volume})
            muted = audio["line_output_status"] == "muted"
            await call("set_pcradio_mute", {"muted": not muted})
            await call("set_pcradio_mute", {"muted": muted})

            eq = audio["eq_preset"]
            await call("set_pcradio_eq", {"preset": 1 if eq != 1 else 0})
            await call("set_pcradio_eq", {"preset": eq})
            for effect in ("loudness", "fft_denoise", "stereo_wide"):
                enabled = audio[effect]
                await call("set_pcradio_audio_effect", {
                    "effect": effect, "enabled": not enabled,
                })
                await call("set_pcradio_audio_effect", {
                    "effect": effect, "enabled": enabled,
                })

            existing_user = users["stations"][0]
            await call("play_pcradio_user_station", {"station_id": existing_user["id"]})
            await asyncio.sleep(2)
            await call("update_pcradio_station", {
                "station_id": existing_user["id"],
                "favorite": not existing_user["favorite"],
            })
            await call("update_pcradio_station", {
                "station_id": existing_user["id"],
                "favorite": existing_user["favorite"],
            })

            added = await call("add_pcradio_user_station", {
                "name": "Codex MCP reversible test",
                "url": "https://stream.radioparadise.com/aac-320",
            })
            cleanup["station_id"] = added.get("id")

            await call("set_pcradio_ui_preferences", {
                "collapsed_groups": ["equalizer", "update", "channel"],
            })
            await call("set_pcradio_time_config", {
                "servers": ["pool.ntp.org", "ntp.ix.ru", "ntp0.ntp-servers.net"],
                "timezone": "+0300",
            })

            alarm = await call("create_pcradio_alarm", {
                "title": "Codex MCP reversible test",
                "date": (date.today() + timedelta(days=1)).isoformat(),
                "station_id": existing_user["id"],
                "hour": 10, "minute": 0, "weekdays": 0,
                "fade_seconds": 0, "target_volume": 10, "enabled": False,
            })
            cleanup["alarm_id"] = alarm["id"]
            updated = await call("update_pcradio_alarm", {
                "alarm_id": alarm["id"], "revision": alarm["revision"],
                "title": "Codex MCP reversible test updated",
                "date": (date.today() + timedelta(days=1)).isoformat(),
                "station_id": existing_user["id"],
                "hour": 10, "minute": 1, "weekdays": 0,
                "fade_seconds": 0, "target_volume": 10, "enabled": False,
            })
            cleanup["alarm_revision"] = updated["revision"]

            await call("stop_pcradio")
            await asyncio.sleep(2)
            await call("reload_pcradio_playlist")
            await asyncio.sleep(5)

            if original_user:
                await call("play_pcradio_user_station", {"station_id": original_id})
            elif original_main:
                await call("play_pcradio", {"channel": original_main["number"]})
            elif playback["is_playing"]:
                raise RuntimeError("cannot restore original station")
            await call("get_pcradio_state")

    print(json.dumps({"passed": passed, "cleanup": cleanup}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
