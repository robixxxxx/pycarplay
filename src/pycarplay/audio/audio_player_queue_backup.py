#!/usr/bin/env python3
"""
Audio Player for CarPlay
Plays PCM audio data using sounddevice with continuous buffer
"""
import struct
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional
import threading
from ..logging_utils import get_module_logger


LOGGER = get_module_logger(__name__)


class AudioPlayer(QObject):
    """
    Audio player for CarPlay audio streams
    Uses continuous buffer for glitch-free playback
    """
    
    audioStarted = Signal()
    audioStopped = Signal()
    audioError = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Audio settings
        self.sample_rate = 48000
        self.channels = 2
        
        # Continuous buffer
        self._buffer = np.zeros((0, self.channels), dtype=np.int16)
        self._buffer_lock = threading.Lock()
        self._stream = None
        self._is_playing = False
        
        # Statistics
        self._frames_played = 0
        self._underruns = 0
        
        LOGGER.info("AudioPlayer initialized (sounddevice with continuous buffer)")
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status.output_underflow:
            self._underruns += 1
            if self._underruns % 10 == 0:
                LOGGER.warning("AudioPlayer buffer underrun #%d", self._underruns)
        
        with self._buffer_lock:
            available = len(self._buffer)
            
            if available >= frames:
                # We have enough data
                outdata[:] = self._buffer[:frames]
                self._buffer = self._buffer[frames:]
            elif available > 0:
                # Partial data available
                outdata[:available] = self._buffer
                outdata[available:] = 0  # Silence for the rest
                self._buffer = np.zeros((0, self.channels), dtype=np.int16)
            else:
                # No data - silence
                outdata.fill(0)
    
    def start(self):
        """Start audio playback"""
        if self._is_playing:
            return
        
        try:
            # Create and start stream with larger buffer
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback,
                blocksize=0,  # Let sounddevice choose optimal size
                latency=0.2   # 200ms latency for stability
            )
            self._stream.start()
            self._is_playing = True
            
            self.audioStarted.emit()
            LOGGER.info("AudioPlayer started (%dHz, %dch, latency=200ms)", self.sample_rate, self.channels)
            
        except Exception as e:
            error_msg = f"Failed to start audio: {e}"
            LOGGER.exception("AudioPlayer: %s", error_msg)
            self.audioError.emit(error_msg)
    
    def stop(self):
        """Stop audio playback"""
        self._is_playing = False
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            # Clear buffer
            with self._buffer_lock:
                self._buffer = np.zeros((0, self.channels), dtype=np.int16)
            
            self.audioStopped.emit()
            LOGGER.info("AudioPlayer stopped (played %d frames, underruns: %d)", self._frames_played, self._underruns)
            
        except Exception as e:
            LOGGER.exception("AudioPlayer: Error stopping: %s", e)
    
    @Slot(object)
    def playAudioData(self, audio_data: tuple):
        """
        Play audio data
        
        Args:
            audio_data: Tuple of 16-bit PCM samples
        """
        if not self._is_playing:
            self.start()
        
        try:
            # Convert to numpy array (samples are interleaved stereo)
            samples = np.array(audio_data, dtype=np.int16)
            
            # Reshape to (frames, channels) for stereo
            frames_count = len(samples) // self.channels
            audio_array = samples[:frames_count * self.channels].reshape(-1, self.channels)
            
            # Add to continuous buffer
            with self._buffer_lock:
                self._buffer = np.vstack([self._buffer, audio_array])
                
                # Limit buffer size to prevent excessive lag (max ~5 seconds)
                max_frames = self.sample_rate * 5  # 5 seconds
                if len(self._buffer) > max_frames:
                    # Keep only the newest data
                    self._buffer = self._buffer[-max_frames:]
                    if self._frames_played % 100 == 0:
                        LOGGER.warning("AudioPlayer buffer overflow, trimmed to %d frames", max_frames)
            
            self._frames_played += 1
            
            if self._frames_played % 500 == 0:
                with self._buffer_lock:
                    buffer_size = len(self._buffer)
                buffer_ms = (buffer_size / self.sample_rate) * 1000
                LOGGER.debug("AudioPlayer frame #%d, buffer: %d frames (%.0fms)", self._frames_played, buffer_size, buffer_ms)
                    
        except Exception as e:
            LOGGER.exception("AudioPlayer: Error playing audio: %s", e)
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set volume (not implemented in sounddevice)"""
        LOGGER.info("AudioPlayer volume control not available with sounddevice")
    
    def __del__(self):
        """Cleanup"""
        self.stop()
