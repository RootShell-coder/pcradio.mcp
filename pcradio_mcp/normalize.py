from typing import Any


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    player = state.get("player", {})
    audio = player.get("audio", {})
    network = player.get("network", {})
    time_state = state.get("time", {})
    power = state.get("power", {})
    identity = state.get("identity", {})
    alarm_page = state.get("alarms", {})
    alarms = alarm_page.get("alarms", [])
    icy = player.get("icy") if isinstance(player.get("icy"), dict) else None
    return {
        "identity": {
            "device_id": identity.get("device_id"),
            "operating_mode": identity.get("mode"),
            "provisioning_state": identity.get("provisioning_state"),
        },
        "playback": {
            "status": player.get("status"),
            "is_playing": player.get("status") == "playing"
            and player.get("playback_enabled") is True,
            "configured_station_name": player.get("station_name"),
            "station_id": player.get("station_id"),
            "icy": icy,
            "firmware_version": player.get("firmware_version"),
        },
        "audio": {
            "volume_percent": audio.get("volume_percent"),
            "line_output_status": (
                "muted" if audio.get("muted") is True else
                "active" if audio.get("muted") is False else None
            ),
            "codec": audio.get("codec"),
            "bitrate_kbps": audio.get("bitrate_kbps"),
            "eq_preset": audio.get("eq_preset"),
            "eq_preset_name": audio.get("eq_preset_name"),
            "loudness": audio.get("loudness"),
            "fft_denoise": audio.get("fft_denoise"),
            "stereo_wide": audio.get("stereo_wide"),
        },
        "network": {
            "wifi_rssi_dbm": network.get("wifi_rssi_dbm"),
            "wifi_signal_percent": network.get("wifi_signal_percent"),
            "buffer_fill_percent": network.get("buffer_fill_percent"),
            "reconnect_count": network.get("reconnect_count"),
        },
        "time": {
            "synchronized": time_state.get("synchronized"),
            "local_datetime": time_state.get("local_datetime"),
        },
        "alarms": {
            "items": [
                {key: alarm.get(key) for key in (
                    "id", "title", "date", "station_id", "hour", "minute", "weekdays",
                    "fade_seconds", "target_volume", "enabled",
                )}
                for alarm in alarms if isinstance(alarm, dict)
            ],
            "total": alarm_page.get("total", len(alarms)),
            "revision": alarm_page.get("revision"),
            "page": alarm_page.get("page"),
            "page_size": alarm_page.get("page_size"),
            "active": time_state.get("active_alarm"),
            "next": time_state.get("next_alarm"),
        },
        "power": {
            "state": power.get("state"),
            "amp_power": power.get("amp_power"),
            "speaker_relay": power.get("speaker_relay"),
        },
    }


def normalize_playlist(payload: dict[str, Any]) -> dict[str, Any]:
    stations = payload.get("stations", [])
    items = [
        {
            "id": item.get("id"),
            "number": item.get("number"),
            "name": item.get("name"),
            "favorite": item.get("favorite"),
            "play_count": item.get("play_count"),
            "available": item.get("availability_confirmed"),
        }
        for item in stations if isinstance(item, dict)
    ]
    return {"stations": items, "total": len(items)}

def normalize_user_playlist(payload: dict[str, Any]) -> dict[str, Any]:
    stations = payload.get("stations", [])
    items = [
        {
            "id": item.get("id"),
            "number": item.get("user_number"),
            "name": item.get("name"),
            "favorite": item.get("favorite"),
            "available": item.get("availability_confirmed"),
            "in_main_playlist": item.get("in_main"),
            "main_channel": item.get("main_channel"),
            "play_count": item.get("play_count"),
        }
        for item in stations if isinstance(item, dict)
    ]
    total = payload.get("count")
    return {"stations": items, "total": total if isinstance(total, int) else len(items)}
