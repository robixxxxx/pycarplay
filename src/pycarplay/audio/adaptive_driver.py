#!/usr/bin/env python3
"""Adaptive audio queue driver for runtime stability tuning."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Any
from ..logging_utils import get_module_logger


LOGGER = get_module_logger(__name__)


@dataclass(frozen=True)
class AdaptiveRecommendation:
    """Dynamic queue and trim recommendations derived from runtime telemetry."""

    min_prebuffer_seconds: float
    target_latency_seconds: float
    hard_latency_seconds: float
    trim_aggressiveness: float
    mode: str


class AdaptiveAudioDriver:
    """Thread-safe adaptive policy for queue behavior and latency targets."""

    def __init__(self):
        self._lock = threading.Lock()

        self._sample_rate = 48000
        self._channels = 2

        self._default_prebuffer_seconds = 0.7
        self._default_target_latency_seconds = 1.0
        self._default_hard_latency_seconds = 1.5

        self._last_input_ts: Optional[float] = None
        self._last_update_ts = time.monotonic()
        self._last_mode_change_ts = self._last_update_ts

        self._ewma_input_fps = 0.0
        self._ewma_input_bitrate_bps = 0.0
        self._ewma_queue_seconds = 0.0

        self._underrun_count_total = 0
        self._overflow_count_total = 0
        self._underrun_events = 0.0
        self._overflow_events = 0.0
        self._stress_score = 0.0

        self._mode = "normal"
        self._recommendation = AdaptiveRecommendation(
            min_prebuffer_seconds=self._default_prebuffer_seconds,
            target_latency_seconds=self._default_target_latency_seconds,
            hard_latency_seconds=self._default_hard_latency_seconds,
            trim_aggressiveness=1.0,
            mode=self._mode,
        )

    def reset(
        self,
        sample_rate: int,
        channels: int,
        min_prebuffer_seconds: float,
        target_latency_seconds: float,
        hard_latency_seconds: float,
    ) -> AdaptiveRecommendation:
        """Reset all runtime statistics and restore baseline recommendations."""
        now = time.monotonic()
        with self._lock:
            self._sample_rate = max(1, int(sample_rate))
            self._channels = max(1, int(channels))

            self._default_prebuffer_seconds = max(0.1, float(min_prebuffer_seconds))
            self._default_target_latency_seconds = max(0.2, float(target_latency_seconds))
            self._default_hard_latency_seconds = max(
                self._default_target_latency_seconds + 0.1,
                float(hard_latency_seconds),
            )

            self._last_input_ts = None
            self._last_update_ts = now
            self._last_mode_change_ts = now

            self._ewma_input_fps = 0.0
            self._ewma_input_bitrate_bps = 0.0
            self._ewma_queue_seconds = 0.0

            self._underrun_count_total = 0
            self._overflow_count_total = 0
            self._underrun_events = 0.0
            self._overflow_events = 0.0
            self._stress_score = 0.0

            self._mode = "normal"
            self._recommendation = AdaptiveRecommendation(
                min_prebuffer_seconds=self._default_prebuffer_seconds,
                target_latency_seconds=self._default_target_latency_seconds,
                hard_latency_seconds=self._default_hard_latency_seconds,
                trim_aggressiveness=1.0,
                mode=self._mode,
            )
            return self._recommendation

    def observe_input(self, frames: int, available_samples: int, now: Optional[float] = None) -> None:
        """Observe incoming writer throughput and queue level."""
        if frames <= 0:
            return
        now = now if now is not None else time.monotonic()

        with self._lock:
            self._decay_counters(now)

            if self._last_input_ts is not None:
                dt = now - self._last_input_ts
                if dt > 1e-6:
                    inst_fps = float(frames) / dt
                    alpha = 0.18
                    if self._ewma_input_fps <= 0.0:
                        self._ewma_input_fps = inst_fps
                    else:
                        self._ewma_input_fps = (1.0 - alpha) * self._ewma_input_fps + alpha * inst_fps
                    self._ewma_input_bitrate_bps = self._ewma_input_fps * self._channels * 16.0

            self._last_input_ts = now
            self._update_queue_ewma(available_samples)
            self._update_recommendation_locked(now)

    def observe_callback(self, requested_frames: int, available_samples: int, underrun: bool, now: Optional[float] = None) -> None:
        """Observe callback-side queue state and underruns."""
        now = now if now is not None else time.monotonic()
        with self._lock:
            self._decay_counters(now)
            self._update_queue_ewma(available_samples)
            if underrun:
                self._underrun_count_total += 1
                self._underrun_events += 1.0
                self._stress_score += 0.9
            elif requested_frames > 0 and available_samples < requested_frames:
                self._stress_score += 0.2
            self._update_recommendation_locked(now)

    def observe_overflow(self, dropped_samples: int, available_samples: int, now: Optional[float] = None) -> None:
        """Observe writer-side overflow or trim events."""
        if dropped_samples <= 0:
            return
        now = now if now is not None else time.monotonic()
        with self._lock:
            self._decay_counters(now)
            self._overflow_count_total += 1
            self._overflow_events += 1.0
            self._stress_score += 0.5
            self._update_queue_ewma(available_samples)
            self._update_recommendation_locked(now)

    def get_recommendation(self) -> AdaptiveRecommendation:
        with self._lock:
            return self._recommendation

    def snapshot(self, queue_samples: Optional[int] = None) -> Dict[str, Any]:
        """Return a lightweight diagnostics snapshot."""
        with self._lock:
            queue_seconds = self._ewma_queue_seconds
            if queue_samples is not None:
                queue_seconds = float(queue_samples) / float(self._sample_rate)

            return {
                "mode": self._mode,
                "estimated_input_fps": round(self._ewma_input_fps, 2),
                "estimated_input_bitrate_bps": round(self._ewma_input_bitrate_bps, 2),
                "queue_seconds": round(queue_seconds, 4),
                "queue_ewma_seconds": round(self._ewma_queue_seconds, 4),
                "underruns_total": int(self._underrun_count_total),
                "overflows_total": int(self._overflow_count_total),
                "stress_score": round(self._stress_score, 3),
                "recommended_min_prebuffer_seconds": round(self._recommendation.min_prebuffer_seconds, 4),
                "recommended_target_latency_seconds": round(self._recommendation.target_latency_seconds, 4),
                "recommended_hard_latency_seconds": round(self._recommendation.hard_latency_seconds, 4),
                "recommended_trim_aggressiveness": round(self._recommendation.trim_aggressiveness, 3),
            }

    def _update_queue_ewma(self, available_samples: int) -> None:
        q_sec = max(0.0, float(available_samples) / float(self._sample_rate))
        alpha = 0.12
        if self._ewma_queue_seconds <= 0.0:
            self._ewma_queue_seconds = q_sec
        else:
            self._ewma_queue_seconds = (1.0 - alpha) * self._ewma_queue_seconds + alpha * q_sec

    def _decay_counters(self, now: float) -> None:
        dt = max(0.0, now - self._last_update_ts)
        self._last_update_ts = now
        if dt <= 0.0:
            return

        tau = 3.5
        decay = math.exp(-dt / tau)
        self._underrun_events *= decay
        self._overflow_events *= decay
        self._stress_score *= decay

    def _update_recommendation_locked(self, now: float) -> None:
        baseline = self._recommendation

        target_mode = "normal"
        if self._underrun_events > self._overflow_events + 0.25 or self._ewma_queue_seconds < max(0.08, baseline.min_prebuffer_seconds * 0.55):
            target_mode = "catch_up"
        elif self._overflow_events > self._underrun_events + 0.35 or self._ewma_queue_seconds > max(0.15, baseline.hard_latency_seconds * 0.85):
            target_mode = "drain"

        # Hysteresis: hold mode to avoid oscillating between states.
        hold_seconds = 1.2
        if target_mode != self._mode and (now - self._last_mode_change_ts) >= hold_seconds:
            self._mode = target_mode
            self._last_mode_change_ts = now

        pre = self._default_prebuffer_seconds
        target = self._default_target_latency_seconds
        hard = self._default_hard_latency_seconds
        trim = 1.0

        if self._mode == "catch_up":
            severity = min(1.0, 0.2 * self._underrun_events + 0.15 * self._stress_score)
            pre = min(max(pre * (1.2 + 0.45 * severity), 0.15), 1.8)
            target = min(max(target * (1.15 + 0.25 * severity), 0.3), 2.8)
            hard = min(max(max(target + 0.15, hard * (1.1 + 0.25 * severity)), 0.45), 3.4)
            trim = max(0.75, 1.0 - 0.2 * severity)
        elif self._mode == "drain":
            severity = min(1.0, 0.2 * self._overflow_events + 0.12 * self._stress_score)
            pre = min(max(pre * (0.95 - 0.25 * severity), 0.1), 1.2)
            target = min(max(target * (0.92 - 0.3 * severity), 0.25), 2.4)
            hard = min(max(max(target + 0.12, hard * (0.9 - 0.25 * severity)), 0.4), 3.2)
            trim = min(1.45, 1.05 + 0.35 * severity)

        smooth = 0.18
        pre = baseline.min_prebuffer_seconds * (1.0 - smooth) + pre * smooth
        target = baseline.target_latency_seconds * (1.0 - smooth) + target * smooth
        hard = baseline.hard_latency_seconds * (1.0 - smooth) + hard * smooth
        trim = baseline.trim_aggressiveness * (1.0 - smooth) + trim * smooth

        hard = max(hard, target + 0.1)

        self._recommendation = AdaptiveRecommendation(
            min_prebuffer_seconds=pre,
            target_latency_seconds=target,
            hard_latency_seconds=hard,
            trim_aggressiveness=trim,
            mode=self._mode,
        )
