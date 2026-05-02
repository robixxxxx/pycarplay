#!/usr/bin/env python3
"""
Audio Player for CarPlay

Plays PCM audio streams from CarPlay using sounddevice.
Features continuous ring buffer for glitch-free playback with
dynamic sample rate and channel configuration.
"""
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional, Dict, Any, Set, List
import threading
from time import monotonic as _monotonic
from .adaptive_driver import AdaptiveAudioDriver
from ..logging_utils import get_module_logger, log_received_data


LOGGER = get_module_logger(__name__)


class AudioPlayer(QObject):
    """Audio player with ring buffer for CarPlay streams
    
    Features:
    - Dynamic sample rate and channel switching
    - Low-latency ring buffer
    - Short pre-buffering to prevent underruns
    - Automatic recovery from glitches
    """
    
    # === Signals ===
    audioStarted = Signal()
    audioStopped = Signal()
    audioError = Signal(str)
    STREAM_MEDIA = "media"
    STREAM_NAVI = "navi"
    STREAM_PHONECALL = "phonecall"
    STREAM_SIRI = "siri"
    STREAM_ALERT = "alert"
    STREAM_UNKNOWN = "unknown"
    STREAM_TYPES = (
        STREAM_MEDIA,
        STREAM_NAVI,
        STREAM_PHONECALL,
        STREAM_SIRI,
        STREAM_ALERT,
        STREAM_UNKNOWN,
    )
    # Priority for smart setVolume routing (overlay streams > background media)
    VOLUME_TARGET_PRIORITY = (
        STREAM_NAVI,
        STREAM_PHONECALL,
        STREAM_SIRI,
        STREAM_ALERT,
        STREAM_MEDIA,
        STREAM_UNKNOWN,
    )
    
    def __init__(self, target_latency_seconds: float = 1.2, hard_latency_seconds: float = 2.6):
        super().__init__()
        
        # === Audio Configuration ===
        self.sample_rate = 44100  # Default, updated dynamically
        self.channels = 2
        
        # === Ring Buffer ===
        self._buffer_size = 144000  # ~3 seconds at 48kHz
        self._stream_buffers = self._create_stream_buffers()
        self._active_streams: Set[str] = {self.STREAM_MEDIA}
        self._explicitly_deactivated_streams: Set[str] = set()
        self._stream_volumes: Dict[str, float] = {stream: 1.0 for stream in self.STREAM_TYPES}
        # === Ducking ===
        self._duck_volume: float = 0.15        # media level while overlay active
        self._duck_fade_steps: int = 20        # ~20 callback steps ≈ smooth fade
        self._duck_fade_interval_s: float = 0.02
        self._user_media_volume: float = 1.0   # target when no overlay active
        self._duck_fade_thread: Optional[threading.Thread] = None
        self._duck_fade_cancel = threading.Event()
        # === Auto-deactivation of overlay streams on silence ===
        self._stream_auto_activated: Set[str] = set()
        self._stream_last_write_time: Dict[str, float] = {s: 0.0 for s in self.STREAM_TYPES}
        self._auto_deactivate_timeout_s: float = 0.8
        self._last_selected_stream = self.STREAM_MEDIA
        self._buffer_lock = threading.Lock()
        
        # === Playback State ===
        self._stream = None
        self._is_playing = False
        self._current_sample_rate = None
        self._buffering = True
        self._target_latency_seconds = max(0.1, float(target_latency_seconds))
        self._hard_latency_seconds = max(self._target_latency_seconds + 0.1, float(hard_latency_seconds))
        self._pre_buffer_seconds = 0.7
        self._min_buffer_samples = int(self.sample_rate * self._pre_buffer_seconds)
        self._consecutive_underruns = 0
        self._consecutive_success_reads = 0
        self._underrun_rebuffer_threshold = 4
        self._recovery_reads_required = 8
        self._splice_fade_samples = 384  # ~8ms at 48kHz
        self._pending_splice_smoothing = False
        self._last_output_sample = np.zeros(self.channels, dtype=np.int16)
        self._trim_aggressiveness = 1.0

        # === Adaptive Driver ===
        self._adaptive_driver = AdaptiveAudioDriver()
        self._adaptive_mode = "normal"
        self._adaptive_driver.reset(
            self.sample_rate,
            self.channels,
            self._pre_buffer_seconds,
            self._target_latency_seconds,
            self._hard_latency_seconds,
        )
        
        # === Statistics ===
        self._frames_received = 0
        self._underruns = 0
        self._available_samples = 0
        self._last_overflow_log = 0
        
        LOGGER.info("AudioPlayer initialized: ring buffer with ~2s+ capacity")
        self._log_available_devices()

    def _create_stream_buffers(self) -> Dict[str, Dict[str, Any]]:
        buffers: Dict[str, Dict[str, Any]] = {}
        for stream in self.STREAM_TYPES:
            buffers[stream] = {
                "buffer": np.zeros((self._buffer_size, self.channels), dtype=np.int16),
                "write_pos": 0,
                "read_pos": 0,
            }
        return buffers

    def _normalize_stream_type(self, stream_type: Optional[str]) -> str:
        if not stream_type:
            return self.STREAM_MEDIA
        stream = str(stream_type).lower().strip()
        if stream not in self.STREAM_TYPES:
            return self.STREAM_UNKNOWN
        return stream
    
    def _log_available_devices(self):
        """Log available audio devices"""
        try:
            LOGGER.info("Available audio output devices:")
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_output_channels'] > 0:
                    default = " (DEFAULT)" if i == sd.default.device[1] else ""
                    LOGGER.info("[%d] %s (%s outputs)%s", i, dev['name'], dev['max_output_channels'], default)
        except Exception as e:
            LOGGER.warning("Could not query audio devices: %s", e)
    
    # === Buffer Management ===
    
    def _get_available_samples(self, stream_type: str = STREAM_MEDIA):
        """Get number of samples available in buffer
        
        Must be called with buffer lock held.
        """
        stream = self._normalize_stream_type(stream_type)
        state = self._stream_buffers[stream]
        write_pos = state["write_pos"]
        read_pos = state["read_pos"]
        if write_pos >= read_pos:
            return write_pos - read_pos
        else:
            return self._buffer_size - read_pos + write_pos

    def _get_active_streams_for_mix(self) -> List[str]:
        active = [s for s in self._active_streams if self._get_available_samples(s) > 0]
        if active:
            return active
        # If no explicit active stream has samples, still allow fallback playback.
        for stream in self.STREAM_TYPES:
            if self._get_available_samples(stream) > 0:
                return [stream]
        return []

    def _get_primary_available_samples(self) -> int:
        media_available = self._get_available_samples(self.STREAM_MEDIA)
        if media_available > 0:
            return media_available
        active = self._get_active_streams_for_mix()
        if not active:
            return 0
        return max(self._get_available_samples(stream) for stream in active)
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice output stream
        
        Fills output buffer from ring buffer with automatic buffering
        and overflow recovery.
        
        Args:
            outdata: Output buffer to fill
            frames: Number of frames requested
            time_info: Timing information (unused)
            status: Stream status flags
        """
        had_underrun = bool(status.output_underflow)
        if had_underrun:
            self._underruns += 1
            if self._underruns % 10 == 0:
                LOGGER.warning("Buffer underrun #%d", self._underruns)
        
        with self._buffer_lock:
            available = self._get_primary_available_samples()
            active_for_mix = self._get_active_streams_for_mix()
            
            # Check if we're still buffering
            if self._buffering:
                if available >= self._min_buffer_samples:
                    self._buffering = False
                    self._underruns = 0
                    self._consecutive_underruns = 0
                    self._consecutive_success_reads = 0
                    self._pending_splice_smoothing = True
                    LOGGER.info("Buffering complete (%d samples = %.1fs)", available, available / self.sample_rate)
                else:
                    # Still buffering - output silence
                    outdata.fill(0)
                    self._last_output_sample[:] = 0
                    return
            
            if active_for_mix:
                # Mix active streams into output.
                self._mix_from_streams(outdata, frames, active_for_mix)
                self._consecutive_success_reads += 1
                if self._consecutive_success_reads >= self._recovery_reads_required:
                    self._consecutive_underruns = 0
            else:
                # Not enough data - output silence
                outdata.fill(0)
                had_underrun = True
                self._pending_splice_smoothing = True
                self._last_output_sample[:] = 0
                if not self._buffering:
                    self._underruns += 1
                    if self._underruns <= 5 or self._underruns % 10 == 0:
                        LOGGER.warning("Underrun #%d, only %d/%d samples", self._underruns, available, frames)

            if had_underrun and not self._buffering:
                self._consecutive_success_reads = 0
                self._consecutive_underruns += 1
                if self._consecutive_underruns >= self._underrun_rebuffer_threshold:
                    self._buffering = True
                    LOGGER.warning(
                        f" Rebuffering after {self._consecutive_underruns} underruns "
                        f"(have {available} samples, need {self._min_buffer_samples})"
                    )

            available_after = self._get_primary_available_samples()

        self._adaptive_driver.observe_callback(
            requested_frames=frames,
            available_samples=available_after,
            underrun=had_underrun,
        )
        self._check_auto_deactivate_streams()
    
    def _read_from_stream_buffer(self, stream_type: str, frames: int) -> np.ndarray:
        """Read up to frames from one stream buffer and return an int16 array.
        
        Handles buffer wraparound automatically.
        """
        stream = self._normalize_stream_type(stream_type)
        state = self._stream_buffers[stream]
        available = self._get_available_samples(stream)
        read_len = min(frames, available)
        out = np.zeros((frames, self.channels), dtype=np.int16)
        if read_len <= 0:
            return out

        read_pos = state["read_pos"]
        buffer = state["buffer"]
        if read_pos + read_len <= self._buffer_size:
            out[:read_len] = buffer[read_pos:read_pos + read_len]
            read_pos += read_len
        else:
            first_part = self._buffer_size - read_pos
            out[:first_part] = buffer[read_pos:]
            out[first_part:read_len] = buffer[:read_len - first_part]
            read_pos = read_len - first_part

        if read_pos >= self._buffer_size:
            read_pos = 0
        state["read_pos"] = read_pos
        return out

    def _mix_from_streams(self, outdata, frames: int, streams: List[str]):
        mixed = np.zeros((frames, self.channels), dtype=np.int32)
        contributed = 0
        for stream in streams:
            chunk = self._read_from_stream_buffer(stream, frames)
            if np.any(chunk):
                contributed += 1
            vol = self._stream_volumes.get(stream, 1.0)
            if vol == 0.0:
                continue
            elif vol != 1.0:
                mixed += (chunk.astype(np.float32) * vol).astype(np.int32)
            else:
                mixed += chunk.astype(np.int32)

        outdata[:] = np.clip(mixed, -32768, 32767).astype(np.int16)

        if contributed == 0:
            self._pending_splice_smoothing = True
            self._last_output_sample[:] = 0
            return

        if self._pending_splice_smoothing:
            self._apply_splice_smoothing(outdata, frames)
            self._pending_splice_smoothing = False

        if frames > 0:
            self._last_output_sample = outdata[frames - 1].copy()

    def _apply_splice_smoothing(self, outdata, frames):
        """Apply a short crossfade ramp to hide discontinuity at splice points."""
        fade_len = min(frames, self._splice_fade_samples)
        if fade_len <= 0:
            return

        ramp = (np.arange(fade_len, dtype=np.float32) + 1.0) / float(fade_len)
        start = self._last_output_sample.astype(np.float32)
        head = outdata[:fade_len].astype(np.float32)
        blended = start + (head - start) * ramp[:, None]
        outdata[:fade_len] = np.clip(blended, -32768, 32767).astype(np.int16)
    
    def _check_buffer_overflow(self, available):
        """Check and handle buffer overflow conditions
        
        Performs emergency resync if buffer exceeds hard max.
        Normal target stays close to low-latency range.
        
        Args:
            available: Current number of samples in buffer
        """
        target_buffer = int(self.sample_rate * self._target_latency_seconds)
        hard_max = int(self.sample_rate * self._hard_latency_seconds)
        
        if available > hard_max:
            # Emergency resync - buffer critically large
            skip_samples = available - target_buffer
            media_state = self._stream_buffers[self.STREAM_MEDIA]
            media_state["read_pos"] = (media_state["read_pos"] + skip_samples) % self._buffer_size
            if self._frames_received - self._last_overflow_log > 100:
                LOGGER.warning(
                    f" Emergency resync ({available/self.sample_rate:.2f}s -> "
                    f"{target_buffer/self.sample_rate:.2f}s, dropped {skip_samples} samples)"
                )
                self._last_overflow_log = self._frames_received

    def _auto_activate_stream_on_data(self, stream: str):
        """Activate overlay streams when audio data arrives.

        Some dongles send navigation/alert PCM without matching start commands.
        Keep those overlays audible unless user/device explicitly stopped them.
        """
        if stream in (self.STREAM_MEDIA, self.STREAM_SIRI, self.STREAM_UNKNOWN):
            return
        if stream in self._explicitly_deactivated_streams:
            return
        self._stream_last_write_time[stream] = _monotonic()
        if stream not in self._active_streams:
            self._active_streams.add(stream)
            self._stream_auto_activated.add(stream)
            self._update_media_ducking()
        elif stream not in self._stream_auto_activated:
            # Explicitly started stream – keep it; last-write time already refreshed above.
            pass
        # else: auto-activated and already tracked – last-write time refresh is sufficient.

    def _check_auto_deactivate_streams(self):
        """Deactivate overlay streams that received no data for the timeout period.

        Called after every audio callback so restoration is fast and requires no
        extra thread.  Safe to call outside _buffer_lock.
        """
        if not self._stream_auto_activated:
            return
        now = _monotonic()
        deactivated = False
        for stream in list(self._stream_auto_activated):
            last = self._stream_last_write_time.get(stream, 0.0)
            if (now - last) >= self._auto_deactivate_timeout_s:
                self._active_streams.discard(stream)
                self._stream_auto_activated.discard(stream)
                LOGGER.info("Auto-deactivated silent overlay stream: %s (%.2fs idle)",
                            stream, now - last)
                deactivated = True
        if deactivated:
            self._update_media_ducking()

    def _overlay_streams_active(self) -> bool:
        """Return True if any non-media overlay stream is currently active."""
        overlay = {self.STREAM_NAVI, self.STREAM_PHONECALL, self.STREAM_SIRI, self.STREAM_ALERT}
        return bool(self._active_streams & overlay)

    def _update_media_ducking(self):
        """Start a smooth fade towards duck or restore target based on overlay state.

        Called after any change to _active_streams.  Runs in a daemon thread so
        it never blocks the audio callback.
        """
        target = self._duck_volume if self._overlay_streams_active() else self._user_media_volume
        current = self._stream_volumes.get(self.STREAM_MEDIA, 1.0)
        if abs(target - current) < 0.01:
            return

        # Cancel any ongoing fade before starting a new one.
        self._duck_fade_cancel.set()
        self._duck_fade_cancel = threading.Event()
        cancel = self._duck_fade_cancel

        steps = self._duck_fade_steps
        interval = self._duck_fade_interval_s

        def _fade():
            start_vol = self._stream_volumes.get(self.STREAM_MEDIA, 1.0)
            delta = target - start_vol
            for i in range(1, steps + 1):
                if cancel.is_set():
                    return
                self._stream_volumes[self.STREAM_MEDIA] = max(0.0, min(1.0, start_vol + delta * i / steps))
                threading.Event().wait(interval)
            self._stream_volumes[self.STREAM_MEDIA] = target
            direction = "ducked" if self._overlay_streams_active() else "restored"
            LOGGER.info("Media volume %s to %.3f (overlay active=%s)",
                        direction, target, sorted(self._active_streams))

        t = threading.Thread(target=_fade, daemon=True, name="duck-fade")
        self._duck_fade_thread = t
        t.start()

    def setDuckVolume(self, duck_level: float, fade_steps: int = 20, fade_interval_s: float = 0.02):
        """Configure media ducking behaviour.

        Args:
            duck_level: Media volume (0.0–1.0) while any overlay stream is active.
            fade_steps: Number of incremental steps for the fade transition.
            fade_interval_s: Wall-clock seconds between each fade step.
        """
        self._duck_volume = max(0.0, min(1.0, float(duck_level)))
        self._duck_fade_steps = max(1, int(fade_steps))
        self._duck_fade_interval_s = max(0.005, float(fade_interval_s))
        LOGGER.info("Duck config: level=%.3f steps=%d interval=%.3fs",
                    self._duck_volume, self._duck_fade_steps, self._duck_fade_interval_s)
        self._update_media_ducking()

    def setStreamActive(self, stream_type: str, active: bool):
        stream = self._normalize_stream_type(stream_type)
        with self._buffer_lock:
            if active:
                self._active_streams.add(stream)
                self._explicitly_deactivated_streams.discard(stream)
                self._stream_auto_activated.discard(stream)  # explicit command overrides auto
            else:
                self._active_streams.discard(stream)
                self._explicitly_deactivated_streams.add(stream)
                self._stream_auto_activated.discard(stream)
        self._update_media_ducking()
        LOGGER.info(
            "Audio stream state: %s=%s active=%s deactivated=%s",
            stream_type,
            stream,
            sorted(self._active_streams),
            sorted(self._explicitly_deactivated_streams),
        )
    
    # === Public API ===
    
    def setSampleRate(self, sample_rate: int, channels: Optional[int] = None):
        """Set sample rate and channels for audio stream
        
        Dynamically switches audio format, restarting stream if needed.
        
        Args:
            sample_rate: New sample rate (e.g., 44100, 48000)
            channels: Number of channels (default: keep current)
        """
        if channels is None:
            channels = self.channels
        
        if self._current_sample_rate == sample_rate and self.channels == channels:
            return  # Already set
        
        # Stop current stream if playing
        was_playing = self._is_playing
        if was_playing:
            self.stop()
        
        # Update configuration
        self.sample_rate = sample_rate
        self.channels = channels
        self._current_sample_rate = sample_rate
        self._adaptive_driver.reset(
            self.sample_rate,
            self.channels,
            self._pre_buffer_seconds,
            self._target_latency_seconds,
            self._hard_latency_seconds,
        )
        self._apply_adaptive_recommendation(self._adaptive_driver.get_recommendation(), force=True)
        
        # Recreate buffer with new channel count
        with self._buffer_lock:
            self._stream_buffers = self._create_stream_buffers()
            self._active_streams = {self.STREAM_MEDIA}
            self._explicitly_deactivated_streams.clear()
            self._stream_auto_activated.clear()
            self._buffering = True
            self._consecutive_underruns = 0
            self._consecutive_success_reads = 0
            self._pending_splice_smoothing = True
            self._last_output_sample = np.zeros(self.channels, dtype=np.int16)
        
        LOGGER.info("Format changed to %dHz, %dch", sample_rate, channels)
        
        # Restart if it was playing
        if was_playing:
            self.start()
    
    def start(self):
        """Start audio playback stream
        
        Initializes sounddevice output stream in stable playback mode.
        """
        if self._is_playing:
            return
        
        try:
            # Reset buffer state
            with self._buffer_lock:
                self._stream_buffers = self._create_stream_buffers()
                self._active_streams = {self.STREAM_MEDIA}
                self._explicitly_deactivated_streams.clear()
                self._stream_auto_activated.clear()
                self._buffering = True
                self._consecutive_underruns = 0
                self._consecutive_success_reads = 0
                self._pending_splice_smoothing = True
                self._last_output_sample = np.zeros(self.channels, dtype=np.int16)
            self._adaptive_driver.reset(
                self.sample_rate,
                self.channels,
                self._pre_buffer_seconds,
                self._target_latency_seconds,
                self._hard_latency_seconds,
            )
            self._apply_adaptive_recommendation(self._adaptive_driver.get_recommendation(), force=True)
            
            # Use a more stable stream profile to reduce audible crackle.
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback,
                blocksize=1024,  # Larger callback quantum for smoother playback
                latency='high'
            )
            self._stream.start()
            self._is_playing = True
            
            self.audioStarted.emit()
            LOGGER.info("Audio started (%dHz, %dch, ring buffer)", self.sample_rate, self.channels)
            
        except Exception as e:
            error_msg = f"Failed to start audio: {e}"
            LOGGER.exception("%s", error_msg)
            self.audioError.emit(error_msg)
    
    def stop(self):
        """Stop audio playback stream
        
        Closes stream and resets buffer state.
        """
        self._is_playing = False
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            # Reset buffer
            with self._buffer_lock:
                self._stream_buffers = self._create_stream_buffers()
                self._active_streams = {self.STREAM_MEDIA}
                self._explicitly_deactivated_streams.clear()
                self._stream_auto_activated.clear()
                self._buffering = True
                self._consecutive_underruns = 0
                self._consecutive_success_reads = 0
                self._pending_splice_smoothing = True
                self._last_output_sample = np.zeros(self.channels, dtype=np.int16)

            self._adaptive_driver.reset(
                self.sample_rate,
                self.channels,
                self._pre_buffer_seconds,
                self._target_latency_seconds,
                self._hard_latency_seconds,
            )
            self._apply_adaptive_recommendation(self._adaptive_driver.get_recommendation(), force=True)
            
            self.audioStopped.emit()
            LOGGER.info("Audio stopped (received %d frames, underruns: %d)", self._frames_received, self._underruns)
            
        except Exception as e:
            LOGGER.exception("Error stopping audio: %s", e)
    
    
    @Slot(object)
    def playAudioData(self, audio_data: tuple, stream_type: Optional[str] = None):
        """Write audio data to ring buffer
        
        Automatically starts playback if not already playing.
        Handles buffer overflow by dropping oldest data.
        
        Args:
            audio_data: Tuple of interleaved 16-bit PCM samples
        """
        if not self._is_playing:
            self.start()
        
        try:
            log_received_data(LOGGER, "Audio playback ingress", audio_data)
            # Convert to numpy array
            samples = np.array(audio_data, dtype=np.int16)

            # Keep full interleaved frames only (samples must be divisible by channels)
            remainder = len(samples) % self.channels
            if remainder:
                samples = samples[:-remainder]

            if len(samples) == 0:
                return
            
            # Reshape to (frames, channels)
            frames_count = len(samples) // self.channels
            audio_array = samples[:frames_count * self.channels].reshape(-1, self.channels)
            
            stream = self._normalize_stream_type(stream_type)

            # Write to selected stream ring buffer
            with self._buffer_lock:
                self._write_to_buffer(audio_array, stream)
                self._auto_activate_stream_on_data(stream)
                available_after_write = self._get_primary_available_samples()

            self._last_selected_stream = stream
            if self._frames_received <= 5 or self._frames_received % 300 == 0:
                LOGGER.debug(
                    "Audio routed: stream=%s active=%s",
                    stream,
                    sorted(self._active_streams),
                )

            self._adaptive_driver.observe_input(frames_count, available_after_write)
            self._apply_adaptive_recommendation(self._adaptive_driver.get_recommendation())
            
            self._frames_received += 1
            
            # Log buffer status periodically
            if self._frames_received % 100 == 0:
                with self._buffer_lock:
                    available = self._get_available_samples()
                    buffer_seconds = available / self.sample_rate
                    LOGGER.debug("Buffer: %d samples (%.2fs)", available, buffer_seconds)
                    
        except Exception as e:
            LOGGER.exception("Error playing audio: %s", e)
    
    def _write_to_buffer(self, audio_array, stream_type: str):
        """Write audio array to ring buffer
        
        Handles buffer overflow by dropping oldest data.
        Must be called with buffer lock held.
        
        Args:
            audio_array: Numpy array of shape (frames, channels)
        """
        # Ring buffer uses read==write as empty, so keep at most _buffer_size - 1 samples.
        stream = self._normalize_stream_type(stream_type)
        state = self._stream_buffers[stream]
        if len(audio_array) >= self._buffer_size:
            keep_samples = self._buffer_size - 1
            if keep_samples <= 0:
                return
            audio_array = audio_array[-keep_samples:]

        write_len = len(audio_array)

        # Check if we have space
        available = self._get_available_samples(stream)
        free_space = self._buffer_size - available
        
        if free_space < write_len:
            # Buffer overflow - drop oldest data
            overflow = write_len - free_space
            state["read_pos"] = (state["read_pos"] + overflow) % self._buffer_size
            self._adaptive_driver.observe_overflow(overflow, self._get_primary_available_samples())
            if self._frames_received % 100 == 0:
                LOGGER.warning("Buffer overflow on %s, dropped %d samples", stream, overflow)
        
        # Write data (may wrap around)
        write_pos = state["write_pos"]
        buffer = state["buffer"]
        if write_pos + write_len <= self._buffer_size:
            # Simple case - no wrap
            buffer[write_pos:write_pos + write_len] = audio_array
            write_pos += write_len
        else:
            # Wrap around
            first_part = self._buffer_size - write_pos
            buffer[write_pos:] = audio_array[:first_part]
            buffer[:write_len - first_part] = audio_array[first_part:]
            write_pos = write_len - first_part
        
        # Wrap write position
        if write_pos >= self._buffer_size:
            write_pos = 0
        state["write_pos"] = write_pos

        # Keep live-audio latency bounded even when input briefly outruns playback.
        available_after_write = self._get_available_samples(stream)
        target_buffer = int(self.sample_rate * self._target_latency_seconds)
        hard_max = int(self.sample_rate * self._hard_latency_seconds)
        if available_after_write > hard_max:
            excess_samples = available_after_write - target_buffer
            drop_samples = int(max(1, min(excess_samples, excess_samples * self._trim_aggressiveness)))
            state["read_pos"] = (state["read_pos"] + drop_samples) % self._buffer_size
            self._pending_splice_smoothing = True
            self._adaptive_driver.observe_overflow(drop_samples, self._get_primary_available_samples())
            if self._frames_received - self._last_overflow_log > 100:
                LOGGER.warning(
                    f" Trim backlog on {stream} ({available_after_write/self.sample_rate:.2f}s -> "
                    f"{target_buffer/self.sample_rate:.2f}s, dropped {drop_samples} samples)"
                )
                self._last_overflow_log = self._frames_received

    def _apply_adaptive_recommendation(self, recommendation, force: bool = False):
        """Apply adaptive queue settings with small-change hysteresis."""
        pre = max(0.1, float(recommendation.min_prebuffer_seconds))
        target = max(0.2, float(recommendation.target_latency_seconds))
        hard = max(target + 0.1, float(recommendation.hard_latency_seconds))
        trim = max(0.7, min(1.5, float(recommendation.trim_aggressiveness)))

        changed = force
        if abs(pre - self._pre_buffer_seconds) > 0.02:
            self._pre_buffer_seconds = pre
            changed = True
        if abs(target - self._target_latency_seconds) > 0.04:
            self._target_latency_seconds = target
            changed = True
        if abs(hard - self._hard_latency_seconds) > 0.04:
            self._hard_latency_seconds = hard
            changed = True
        if abs(trim - self._trim_aggressiveness) > 0.03:
            self._trim_aggressiveness = trim
            changed = True

        self._adaptive_mode = recommendation.mode

        if changed:
            self._min_buffer_samples = int(self.sample_rate * self._pre_buffer_seconds)

    def getAdaptiveDiagnostics(self) -> Dict[str, Any]:
        """Return adaptive driver diagnostics and live queue state."""
        with self._buffer_lock:
            available = self._get_primary_available_samples()
            stream_samples = {stream: self._get_available_samples(stream) for stream in self.STREAM_TYPES}

        snapshot = self._adaptive_driver.snapshot(queue_samples=available)
        snapshot.update(
            {
                "sample_rate": int(self.sample_rate),
                "channels": int(self.channels),
                "buffer_samples": int(available),
                "buffer_seconds": round(available / float(self.sample_rate), 4),
                "buffering": bool(self._buffering),
                "adaptive_mode": self._adaptive_mode,
                "stream_samples": stream_samples,
                "active_streams": sorted(self._active_streams),
            }
        )
        return snapshot
    
    def setStreamVolume(self, stream_type: str, volume: float):
        """Set volume for a specific audio stream.

        When setting media volume this also updates the restore target used
        by the ducking engine so the volume is preserved after overlays stop.

        Args:
            stream_type: Stream name ('media', 'navi', 'phonecall', 'siri', 'alert', 'unknown')
            volume: Volume level 0.0–1.0
        """
        stream = self._normalize_stream_type(stream_type)
        vol = max(0.0, min(1.0, float(volume)))
        self._stream_volumes[stream] = vol
        if stream == self.STREAM_MEDIA:
            # Track user intent so ducking engine can restore to this level.
            self._user_media_volume = vol
        LOGGER.info("Stream volume: %s=%.3f  all=%s", stream, vol,
                    {s: round(v, 3) for s, v in self._stream_volumes.items() if v != 1.0} or "(all 1.0)")

    def _get_volume_target_stream(self) -> str:
        """Return the highest-priority currently-active stream for setVolume routing."""
        active = self._active_streams
        for stream in self.VOLUME_TARGET_PRIORITY:
            if stream in active:
                return stream
        return self.STREAM_MEDIA

    @Slot(float)
    def setVolume(self, volume: float):
        """Set volume for the highest-priority currently-active stream.

        Routing logic:
          - Only media active  → adjusts media volume
          - Navi playing       → adjusts navi volume
          - Any other overlay  → adjusts that overlay's volume

        Args:
            volume: Volume level 0.0–1.0
        """
        target = self._get_volume_target_stream()
        self.setStreamVolume(target, volume)
        LOGGER.info("setVolume(%.3f) routed to stream=%s", volume, target)
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()



