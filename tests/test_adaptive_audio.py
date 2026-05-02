import numpy as np

from pycarplay.audio.adaptive_driver import AdaptiveAudioDriver, AdaptiveRecommendation
from pycarplay.audio.audio_player import AudioPlayer


def test_adaptive_driver_estimates_bitrate_and_catch_up_mode():
    driver = AdaptiveAudioDriver()
    driver.reset(
        sample_rate=48000,
        channels=2,
        min_prebuffer_seconds=0.5,
        target_latency_seconds=1.0,
        hard_latency_seconds=2.0,
    )

    now = 100.0
    for _ in range(20):
        now += 0.02
        driver.observe_input(frames=960, available_samples=1200, now=now)

    # Inject repeated underrun pressure to trigger catch-up behavior.
    for _ in range(8):
        now += 0.02
        driver.observe_callback(requested_frames=1024, available_samples=200, underrun=True, now=now)

    snapshot = driver.snapshot(queue_samples=1200)
    recommendation = driver.get_recommendation()

    assert snapshot["estimated_input_bitrate_bps"] > 1_000_000
    assert recommendation.mode in ("catch_up", "normal")
    assert recommendation.min_prebuffer_seconds >= 0.5
    assert recommendation.target_latency_seconds >= 1.0


def test_adaptive_driver_overflow_biases_to_drain():
    driver = AdaptiveAudioDriver()
    driver.reset(
        sample_rate=48000,
        channels=2,
        min_prebuffer_seconds=0.6,
        target_latency_seconds=1.2,
        hard_latency_seconds=2.4,
    )

    now = 200.0
    for _ in range(12):
        now += 0.03
        driver.observe_input(frames=960, available_samples=120000, now=now)
        driver.observe_overflow(dropped_samples=4000, available_samples=100000, now=now)

    recommendation = driver.get_recommendation()
    assert recommendation.mode in ("drain", "normal")
    assert recommendation.trim_aggressiveness >= 1.0


def test_audio_player_applies_adaptive_recommendations(monkeypatch):
    monkeypatch.setattr("pycarplay.audio.audio_player.sd.query_devices", lambda: [])

    player = AudioPlayer(target_latency_seconds=1.2, hard_latency_seconds=2.6)
    player._is_playing = True

    forced = AdaptiveRecommendation(
        min_prebuffer_seconds=0.95,
        target_latency_seconds=1.7,
        hard_latency_seconds=2.9,
        trim_aggressiveness=1.25,
        mode="catch_up",
    )

    monkeypatch.setattr(player._adaptive_driver, "get_recommendation", lambda: forced)

    frames = 2048
    pcm = tuple(np.zeros(frames * player.channels, dtype=np.int16))
    player.playAudioData(pcm)

    stats = player.getAdaptiveDiagnostics()
    assert player._min_buffer_samples == int(player.sample_rate * 0.95)
    assert abs(player._target_latency_seconds - 1.7) < 1e-6
    assert abs(player._hard_latency_seconds - 2.9) < 1e-6
    assert abs(player._trim_aggressiveness - 1.25) < 1e-6
    assert stats["adaptive_mode"] == "catch_up"
    assert stats["buffer_samples"] > 0
