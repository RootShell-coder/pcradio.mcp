from pcradio_mcp.normalize import normalize_state
from pcradio_mcp.normalize import normalize_playlist, normalize_user_playlist


def test_state_preserves_controllable_audio_and_alarm_fields():
    result = normalize_state({
        "player": {"audio": {
            "eq_preset": 3,
            "eq_preset_name": "ROCK",
            "loudness": True,
            "fft_denoise": False,
            "stereo_wide": True,
        }},
        "alarms": {
            "alarms": [{"id": "alarm-1", "station_id": "station-1"}],
            "total": 1,
            "revision": 8,
            "page": 1,
            "page_size": 100,
        },
    })
    assert result["audio"] == {
        "volume_percent": None,
        "line_output_status": None,
        "codec": None,
        "bitrate_kbps": None,
        "eq_preset": 3,
        "eq_preset_name": "ROCK",
        "loudness": True,
        "fft_denoise": False,
        "stereo_wide": True,
    }
    assert result["alarms"]["revision"] == 8
    assert result["alarms"]["items"][0]["id"] == "alarm-1"
    assert result["alarms"]["items"][0]["station_id"] == "station-1"


def test_playlist_normalization_ignores_invalid_items():
    result = normalize_playlist({"stations": [None, {
        "id": "s1", "number": 1, "name": "Radio", "favorite": False,
        "availability_confirmed": True,
    }]})
    assert result == {"stations": [{
        "id": "s1", "number": 1, "name": "Radio", "favorite": False,
        "available": True,
    }], "total": 1}


def test_user_playlist_falls_back_to_filtered_item_count():
    result = normalize_user_playlist({"count": "bad", "stations": [None, {}]})
    assert result["total"] == 1
