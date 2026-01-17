#!/usr/bin/env python3
"""
Audio Player for CarPlay
Plays PCM audio data using sounddevice with continuous ring buffer
"""
import struct
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional
import threading


class AudioPlayer(QObject):
    """
    Audio player for CarPlay audio streams
    Uses continuous ring buffer for glitch-free playback
    """
    
    audioStarted = Signal()
    audioStopped = Signal()
    audioError = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Audio settings - will be set dynamically based on CarPlay stream
        self.sample_rate = 44100  # Default, will be updated
        self.channels = 2
        
        # Ring buffer - continuous memory for smooth playback
        # Larger buffer to handle navigation voice prompts
        self._buffer_size = 960000  # 20 seconds at 48kHz
        self._buffer = np.zeros((self._buffer_size, self.channels), dtype=np.int16)
        self._write_pos = 0
        self._read_pos = 0
        self._buffer_lock = threading.Lock()
        self._stream = None
        self._is_playing = False
        self._current_sample_rate = None  # Track actual sample rate in use
        
        # Pre-buffering - maximum for navigation stability
        self._min_buffer_samples = int(self.sample_rate * 1.5)  # 1.5 seconds pre-buffer
        self._buffering = True
        
        # Statistics
        self._frames_received = 0
        self._underruns = 0
        self._available_samples = 0
        self._last_overflow_log = 0  # Track last overflow log to reduce spam
        
        print(f"AudioPlayer: Initialized (ring buffer, 20s capacity)")
        print(f"AudioPlayer: Available devices:")
        print(sd.query_devices())
    
    
    def _get_available_samples(self):
        """Get number of samples available in buffer (must be called with lock held)"""
        if self._write_pos >= self._read_pos:
            return self._write_pos - self._read_pos
        else:
            return self._buffer_size - self._read_pos + self._write_pos
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status.output_underflow:
            self._underruns += 1
            if self._underruns % 10 == 0:
                print(f'AudioPlayer: Buffer underrun #{self._underruns}')
        
        with self._buffer_lock:
            available = self._get_available_samples()
            
            # Check if we're still buffering
            if self._buffering:
                if available >= self._min_buffer_samples:
                    self._buffering = False
                    self._underruns = 0  # Reset underrun counter after buffering
                    print(f"AudioPlayer: Buffering complete ({available} samples = {available/self.sample_rate:.1f}s)")
                else:
                    # Still buffering - output silence
                    outdata.fill(0)
                    return
            
            if available >= frames:
                # We have enough data
                if self._read_pos + frames <= self._buffer_size:
                    # Simple case - no wrap
                    outdata[:] = self._buffer[self._read_pos:self._read_pos + frames]
                    self._read_pos += frames
                else:
                    # Wrap around
                    first_part = self._buffer_size - self._read_pos
                    outdata[:first_part] = self._buffer[self._read_pos:]
                    outdata[first_part:] = self._buffer[:frames - first_part]
                    self._read_pos = frames - first_part
                
                # Wrap read position
                if self._read_pos >= self._buffer_size:
                    self._read_pos = 0
                    
                # CRITICAL: Simple buffer management - avoid glitches
                # Let buffer grow during navigation, only resync when critical
                # Target: ~1.5s normal
                # Hard max: 5 seconds before emergency resync
                target_buffer = int(self.sample_rate * 1.5)
                hard_max = int(self.sample_rate * 5.0)  # 5 seconds before emergency resync
                
                # Only resync if severely over-buffered (nav finished, buffer still huge)
                if available > hard_max:
                    # Emergency resync - buffer critically large
                    skip_samples = available - target_buffer
                    self._read_pos = (self._read_pos + skip_samples) % self._buffer_size
                    if self._frames_received - self._last_overflow_log > 100:
                        print(f"AudioPlayer: Emergency resync ({available/self.sample_rate:.1f}s → {target_buffer/self.sample_rate:.1f}s)")
                        self._last_overflow_log = self._frames_received
                # NO soft catchup - let buffer grow/shrink naturally
            else:
                # Not enough data - output silence and report underrun
                outdata.fill(0)
                if not self._buffering:
                    self._underruns += 1
                    if self._underruns <= 5 or self._underruns % 10 == 0:
                        print(f"AudioPlayer: UNDERRUN #{self._underruns} - only {available}/{frames} samples available")
    
    def setSampleRate(self, sample_rate: int, channels: int = None):
        """Set sample rate and optionally channels for audio stream"""
        if channels is None:
            channels = self.channels
        
        if self._current_sample_rate == sample_rate and self.channels == channels:
            return  # Already set
        
        # Stop current stream if playing
        was_playing = self._is_playing
        if was_playing:
            self.stop()
        
        # Update sample rate and channels
        self.sample_rate = sample_rate
        self.channels = channels
        self._min_buffer_samples = int(self.sample_rate * 0.8)
        self._current_sample_rate = sample_rate
        
        # Recreate buffer with new channel count
        with self._buffer_lock:
            self._buffer = np.zeros((self._buffer_size, self.channels), dtype=np.int16)
            self._write_pos = 0
            self._read_pos = 0
        
        print(f"AudioPlayer: Format changed to {sample_rate}Hz, {channels}ch")
        
        # Restart if it was playing
        if was_playing:
            self.start()
    
    def start(self):
        """Start audio playback"""
        if self._is_playing:
            return
        
        try:
            # Reset buffer state
            with self._buffer_lock:
                self._write_pos = 0
                self._read_pos = 0
                self._buffering = True
                self._buffer.fill(0)
            
            # Create and start stream - prioritize stability over latency
            # blocksize=0 lets sounddevice choose optimal size
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback,
                blocksize=0,     # Auto - adapt to CarPlay's frame size
                latency='high'   # Maximum latency for maximum stability
            )
            self._stream.start()
            self._is_playing = True
            
            self.audioStarted.emit()
            print(f"AudioPlayer: Started ({self.sample_rate}Hz, {self.channels}ch, ring buffer)")
            
        except Exception as e:
            error_msg = f"Failed to start audio: {e}"
            print(f"AudioPlayer: {error_msg}")
            self.audioError.emit(error_msg)
    
    def stop(self):
        """Stop audio playback"""
        self._is_playing = False
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            # Reset buffer
            with self._buffer_lock:
                self._write_pos = 0
                self._read_pos = 0
                self._buffering = True
            
            self.audioStopped.emit()
            print(f"AudioPlayer: Stopped (received {self._frames_received} frames, underruns: {self._underruns})")
            
        except Exception as e:
            print(f"AudioPlayer: Error stopping: {e}")
    
    
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
            
            # Add to ring buffer
            with self._buffer_lock:
                # Check if we have space
                available = self._get_available_samples()
                free_space = self._buffer_size - available
                
                if free_space < len(audio_array):
                    # Buffer overflow - drop oldest data by moving read pointer
                    overflow = len(audio_array) - free_space
                    self._read_pos = (self._read_pos + overflow) % self._buffer_size
                    if self._frames_received % 100 == 0:
                        print(f"AudioPlayer: Buffer overflow, dropped {overflow} samples")
                
                # Write data to buffer (may wrap around)
                if self._write_pos + len(audio_array) <= self._buffer_size:
                    # Simple case - no wrap
                    self._buffer[self._write_pos:self._write_pos + len(audio_array)] = audio_array
                    self._write_pos += len(audio_array)
                else:
                    # Wrap around
                    first_part = self._buffer_size - self._write_pos
                    self._buffer[self._write_pos:] = audio_array[:first_part]
                    self._buffer[:len(audio_array) - first_part] = audio_array[first_part:]
                    self._write_pos = len(audio_array) - first_part
                
                # Wrap write position
                if self._write_pos >= self._buffer_size:
                    self._write_pos = 0
            
            
            self._frames_received += 1
            
            # More frequent logging to see what's happening
            if self._frames_received % 100 == 0:
                with self._buffer_lock:
                    available = self._get_available_samples()
                buffer_ms = (available / self.sample_rate) * 1000
                print(f"AudioPlayer: Frame #{self._frames_received}, buffer: {available} samples ({buffer_ms:.0f}ms), underruns: {self._underruns}")
                    
        except Exception as e:
            print(f"AudioPlayer: Error playing audio: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set volume (not implemented in sounddevice)"""
        print(f"AudioPlayer: Volume control not available with sounddevice")
    
    def __del__(self):
        """Cleanup"""
        self.stop()


