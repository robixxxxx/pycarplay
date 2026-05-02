import types

import numpy as np
import pytest

from pycarplay.audio.audio_player import AudioPlayer
from pycarplay.controller import VideoStreamController
from pycarplay.protocol.messages import AudioCommand


def _stereo_constant_pcm(frames: int, value: int):
    chunk = np.full((frames, 2), value, dtype=np.int16)
    return tuple(chunk.reshape(-1).tolist())


def test_streams_are_buffered_separately(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True

    player.playAudioData(_stereo_constant_pcm(8, 1000), stream_type="media")
    player.playAudioData(_stereo_constant_pcm(8, 2000), stream_type="navi")

    with player._buffer_lock:
        media_samples = player._get_available_samples("media")
        navi_samples = player._get_available_samples("navi")

    assert media_samples == 8
    assert navi_samples == 8


def test_mixed_output_contains_active_streams(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._buffering = False
    player._min_buffer_samples = 0
    player._duck_volume = 1.0  # disable ducking for raw mix test

    player.setStreamActive("media", True)
    player.setStreamActive("navi", True)
    player.playAudioData(_stereo_constant_pcm(6, 1000), stream_type="media")
    player.playAudioData(_stereo_constant_pcm(6, 2000), stream_type="navi")

    out = np.zeros((6, 2), dtype=np.int16)
    status = types.SimpleNamespace(output_underflow=False)
    player._audio_callback(out, 6, None, status)

    assert np.all(out == 3000)


def test_navi_is_mixed_even_without_explicit_start(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._buffering = False
    player._min_buffer_samples = 0
    player._duck_volume = 1.0  # disable ducking for raw mix test

    # Device may omit explicit AudioNaviStart, but navigation PCM still arrives.
    player.setStreamActive("media", True)
    player.playAudioData(_stereo_constant_pcm(4, 1000), stream_type="media")
    player.playAudioData(_stereo_constant_pcm(4, 2000), stream_type="navi")

    out = np.zeros((4, 2), dtype=np.int16)
    status = types.SimpleNamespace(output_underflow=False)
    player._audio_callback(out, 4, None, status)

    assert np.all(out == 3000)


def test_media_and_navi_do_not_overwrite_each_other(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._buffering = False
    player._min_buffer_samples = 0

    player.setStreamActive("media", True)
    player.setStreamActive("navi", False)
    player.playAudioData(_stereo_constant_pcm(4, 1234), stream_type="media")
    player.playAudioData(_stereo_constant_pcm(4, 4321), stream_type="navi")

    out = np.zeros((4, 2), dtype=np.int16)
    status = types.SimpleNamespace(output_underflow=False)
    player._audio_callback(out, 4, None, status)

    # Navi data must remain queued and not replace media data.
    assert np.all(out == 1234)
    with player._buffer_lock:
        assert player._get_available_samples("media") == 0
        assert player._get_available_samples("navi") == 4


def test_stop_command_for_one_stream_keeps_other_active():
    controller = VideoStreamController.__new__(VideoStreamController)

    class FakeAudioPlayer:
        def __init__(self):
            self.calls = []

        def setStreamActive(self, stream, active):
            self.calls.append((stream, active))

    controller._audio_player = FakeAudioPlayer()
    controller._audio_active_streams = {
        "media": False,
        "navi": False,
        "phonecall": False,
        "siri": False,
        "alert": False,
        "unknown": False,
    }
    controller._last_audio_stream = "media"
    controller._siri_mode = False
    controller._audio_format_candidate = None
    controller._audio_format_candidate_count = 0
    controller._audio_last_switch_ts = 0.0

    controller._handle_audio_command(types.SimpleNamespace(command=AudioCommand.AudioMediaStart))
    controller._handle_audio_command(types.SimpleNamespace(command=AudioCommand.AudioNaviStart))
    controller._handle_audio_command(types.SimpleNamespace(command=AudioCommand.AudioNaviStop))

    assert controller._audio_active_streams["media"] is True
    assert controller._audio_active_streams["navi"] is False
    assert ("media", True) in controller._audio_player.calls
    assert ("navi", True) in controller._audio_player.calls
    assert ("navi", False) in controller._audio_player.calls


def test_per_stream_volume_applied_during_mix(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._buffering = False
    player._min_buffer_samples = 0

    player.setStreamActive("media", True)
    player.setStreamActive("navi", True)
    player.setStreamVolume("media", 0.5)
    player.setStreamVolume("navi", 1.0)
    player.playAudioData(_stereo_constant_pcm(4, 2000), stream_type="media")
    player.playAudioData(_stereo_constant_pcm(4, 1000), stream_type="navi")

    out = np.zeros((4, 2), dtype=np.int16)
    status = types.SimpleNamespace(output_underflow=False)
    player._audio_callback(out, 4, None, status)

    # media 2000 * 0.5 = 1000, navi 1000 * 1.0 = 1000, sum = 2000
    assert np.all(out == 2000)


def test_setvol_routes_to_navi_when_navi_active(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._buffering = False
    player._min_buffer_samples = 0
    # Instant fade so ducking is deterministic before we call setVolume.
    player._duck_volume = 0.15
    player._duck_fade_steps = 1
    player._duck_fade_interval_s = 0.001

    player.setStreamActive("media", True)
    player.setStreamActive("navi", True)
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)

    # setVolume targets navi (higher priority), not media.
    player.setVolume(0.25)

    assert player._stream_volumes["navi"] == pytest.approx(0.25)
    # media should be ducked, not at user level
    assert player._stream_volumes["media"] == pytest.approx(0.15)


def test_setvol_routes_to_media_when_only_media_active(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    # only media is active by default
    player.setVolume(0.5)

    assert player._stream_volumes["media"] == pytest.approx(0.5)
    assert player._stream_volumes["navi"] == pytest.approx(1.0)


def test_media_ducked_when_navi_activated(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    # Instant fade (1 step) for deterministic test
    player._duck_volume = 0.15
    player._duck_fade_steps = 1
    player._duck_fade_interval_s = 0.001

    player.setStreamActive("navi", True)
    # Give the daemon fade thread time to finish
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)

    assert player._stream_volumes["media"] == pytest.approx(0.15)


def test_media_restored_when_navi_stops(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._duck_volume = 0.15
    player._duck_fade_steps = 1
    player._duck_fade_interval_s = 0.001
    player._user_media_volume = 0.8
    player._stream_volumes["media"] = 0.8

    # Duck
    player.setStreamActive("navi", True)
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)
    assert player._stream_volumes["media"] == pytest.approx(0.15)

    # Restore
    player.setStreamActive("navi", False)
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)
    assert player._stream_volumes["media"] == pytest.approx(0.8)


def test_setduckvolume_changes_level(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._duck_fade_steps = 1
    player._duck_fade_interval_s = 0.001

    player.setStreamActive("navi", True)
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)

    # Change duck level while overlay still active → immediate re-fade
    player.setDuckVolume(0.3, fade_steps=1, fade_interval_s=0.001)
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)
    assert player._stream_volumes["media"] == pytest.approx(0.3)


def test_media_restored_after_navi_data_stops(monkeypatch):
    """Restore media volume when navi stream goes silent (no AudioNaviStop command)."""
    import time as _time
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer()
    player._is_playing = True
    player._duck_fade_steps = 1
    player._duck_fade_interval_s = 0.001
    player._duck_volume = 0.15
    player._user_media_volume = 1.0
    player._stream_volumes["media"] = 1.0
    player._auto_deactivate_timeout_s = 0.05  # fast timeout for test

    # Navi data arrives → auto-activate → ducking kicks in
    player.playAudioData(_stereo_constant_pcm(4, 2000), stream_type="navi")
    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)
    assert player._stream_volumes["media"] == pytest.approx(0.15)

    # Wait for timeout to expire, then simulate a few audio callbacks
    _time.sleep(0.1)
    import types as _types
    outdata = np.zeros((4, 2), dtype=np.int16)
    status = _types.SimpleNamespace(output_underflow=False)
    player._buffering = False
    player._min_buffer_samples = 0
    player._audio_callback(outdata, 4, None, status)  # triggers _check_auto_deactivate_streams

    if player._duck_fade_thread:
        player._duck_fade_thread.join(timeout=1.0)

    assert "navi" not in player._active_streams
    assert player._stream_volumes["media"] == pytest.approx(1.0)
