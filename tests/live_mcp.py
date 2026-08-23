"""Destructive-but-reversible live validation for the published MCP tools."""

import asyncio
import json
import os
from datetime import date, timedelta
from uuid import uuid4

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from pcradio_mcp.client import PCRadioClient


URL = os.getenv("PCRADIO_MCP_URL", "http://127.0.0.1:8081/mcp")
DEVICE_URL = os.getenv("PCRADIO_BASE_URL")


def data(result):
    if result.isError:
        text = " ".join(getattr(item, "text", "") for item in result.content)
        raise RuntimeError(text)
    if result.structuredContent is not None:
        return result.structuredContent.get("result", result.structuredContent)
    return json.loads(result.content[0].text)


async def main() -> None:
    if not DEVICE_URL:
        raise RuntimeError("PCRADIO_BASE_URL is required for snapshot and cleanup")
    device = PCRadioClient(DEVICE_URL)
    passed: list[str] = []
    temporary_station_id = None
    temporary_alarm_id = None
    test_suffix = uuid4().hex[:8]
    test_station_name = f"Codex MCP test {test_suffix}"
    test_alarm_title = f"Codex MCP test {test_suffix}"
    cleanup_errors: list[str] = []
    async with streamable_http_client(URL) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()

            async def call(name: str, arguments=None):
                value = data(await session.call_tool(name, arguments or {}))
                passed.append(name)
                return value

            state = await call("get_pcradio_state")
            playlist = await call("get_pcradio_playlist", {
                "query": state["playback"]["configured_station_name"],
                "limit": 500,
            })
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
            ui_preferences = await device.ui_preferences()
            time_config = await device.time_config()
            existing_user = users["stations"][0]
            try:
                await call("play_pcradio", {"channel": 1})
                await asyncio.sleep(2)
                await call("select_pcradio_channel", {"channel": 2})
                await asyncio.sleep(2)
                await call("select_pcradio_channel", {"delta": 1})
                await asyncio.sleep(2)

                volume = audio["volume_percent"]
                await call("set_pcradio_volume", {
                    "volume_percent": 30 if volume != 30 else 31,
                })
                await call("set_pcradio_mute", {
                    "muted": audio["line_output_status"] != "muted",
                })
                await call("set_pcradio_eq", {
                    "preset": 1 if audio["eq_preset"] != 1 else 0,
                })
                for effect in ("loudness", "fft_denoise", "stereo_wide"):
                    await call("set_pcradio_audio_effect", {
                        "effect": effect, "enabled": not audio[effect],
                    })

                await call("play_pcradio_user_station", {
                    "station_id": existing_user["id"],
                })
                await asyncio.sleep(2)
                await call("update_pcradio_station", {
                    "station_id": existing_user["id"],
                    "favorite": not existing_user["favorite"],
                })

                added = await call("add_pcradio_user_station", {
                    "name": test_station_name,
                    "url": "https://stream.radioparadise.com/aac-320",
                })
                temporary_station_id = added.get("id")
                await call("set_pcradio_ui_preferences", {
                    "collapsed_groups": ["equalizer", "update", "channel"],
                })
                await call("set_pcradio_time_config", {
                    "servers": ["pool.ntp.org"], "timezone": "+0300",
                })

                local_day = date.fromisoformat(state["time"]["local_datetime"][:10])
                alarm = await call("create_pcradio_alarm", {
                    "title": test_alarm_title,
                    "date": (local_day + timedelta(days=1)).isoformat(),
                    "station_id": existing_user["id"],
                    "hour": 10, "minute": 0, "weekdays": 0,
                    "fade_seconds": 0, "target_volume": 10, "enabled": False,
                })
                temporary_alarm_id = alarm["id"]
                await call("update_pcradio_alarm", {
                    "alarm_id": alarm["id"], "revision": alarm["revision"],
                    "title": test_alarm_title,
                    "date": (local_day + timedelta(days=1)).isoformat(),
                    "station_id": existing_user["id"],
                    "hour": 10, "minute": 1, "weekdays": 0,
                    "fade_seconds": 0, "target_volume": 10, "enabled": False,
                })
                alarms = await device.alarms()
                await call("delete_pcradio_alarm", {
                    "alarm_id": temporary_alarm_id,
                    "revision": alarms["revision"],
                })
                temporary_alarm_id = None
                await call("stop_pcradio")
                await asyncio.sleep(2)
                await call("reload_pcradio_playlist")
                await asyncio.sleep(5)
            finally:
                async def restore(label, operation):
                    try:
                        await operation
                    except Exception as error:
                        cleanup_errors.append(f"{label}: {error}")

                try:
                    alarms = await device.alarms()
                    if not temporary_alarm_id:
                        temporary_alarm_id = next((
                            item.get("id") for item in alarms.get("alarms", [])
                            if item.get("title") == test_alarm_title
                        ), None)
                    if temporary_alarm_id:
                        await device.delete_alarm(
                            temporary_alarm_id, alarms["revision"],
                        )
                except Exception as error:
                    cleanup_errors.append(f"delete alarm: {error}")
                if not temporary_station_id:
                    try:
                        current_users = await device.user_playlist()
                        temporary_station_id = next((
                            item.get("id") for item in current_users["stations"]
                            if item.get("name") == test_station_name
                        ), None)
                    except Exception as error:
                        cleanup_errors.append(f"find station: {error}")
                if temporary_station_id:
                    await restore(
                        "delete station",
                        device.delete_user_station(temporary_station_id),
                    )
                await restore("restore station favorite", call(
                    "update_pcradio_station", {
                        "station_id": existing_user["id"],
                        "favorite": existing_user["favorite"],
                    },
                ))
                await restore("restore UI preferences", device.set_ui_preferences(
                    ui_preferences["collapsed_groups"],
                ))
                await restore("restore time config", device.set_time_config(
                    time_config["servers"], time_config["timezone"],
                ))
                await restore("restore volume", call(
                    "set_pcradio_volume", {"volume_percent": audio["volume_percent"]},
                ))
                await restore("restore mute", call(
                    "set_pcradio_mute", {
                        "muted": audio["line_output_status"] == "muted",
                    },
                ))
                await restore("restore equalizer", call(
                    "set_pcradio_eq", {"preset": audio["eq_preset"]},
                ))
                for effect in ("loudness", "fft_denoise", "stereo_wide"):
                    await restore(f"restore {effect}", call(
                        "set_pcradio_audio_effect", {
                            "effect": effect, "enabled": audio[effect],
                        },
                    ))
                if not playback["is_playing"]:
                    await restore("restore stopped state", call("stop_pcradio"))
                elif original_user:
                    await restore("restore playback", call(
                        "play_pcradio_user_station", {"station_id": original_id},
                    ))
                elif original_main:
                    await restore("restore playback", call(
                        "play_pcradio", {"channel": original_main["number"]},
                    ))
                else:
                    cleanup_errors.append("restore playback: original station not found")

    if cleanup_errors:
        raise RuntimeError("cleanup failed: " + "; ".join(cleanup_errors))
    print(json.dumps({"passed": passed, "cleanup": "complete"}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
