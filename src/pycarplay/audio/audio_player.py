#!/usr/bin/env python3
"""
Audio Player for CarPlay

Plays PCM audio streams from CarPlay using sounddevice.
Features continuous ring buffer for glitch-free playback with
dynamic sample rate and channel configuration.
"""
import struct
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional
import threading


class AudioPlayer(QObject):
    """Audio player with ring buffer for CarPlay streams
    
    Features:
    - Dynamic sample rate and channel switching
    - 20-second ring buffer for stability
    - Pre-buffering to prevent underruns
    - Automatic recovery from glitches
    """
    
    # === Signals ===
    audioStarted = Signal()
    audioStopped = Signal()
    audioError = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # === Audio Configuration ===
        self.sample_rate = 44100  # Default, updated dynamically
        self.channels = 2
        
        # === Ring Buffer ===
        self._buffer_size = 960000  # 20 seconds at 48kHz
        self._buffer = np.zeros((self._buffer_size, self.channels), dtype=np.int16)
        self._write_pos = 0
        self._read_pos = 0
        self._buffer_lock = threading.Lock()
        
        # === Playback State ===
        self._stream = None
        self._is_playing = False
        self._current_sample_rate = None
        self._buffering = True
        self._min_buffer_samples = int(self.sample_rate * 4.0)  # 4.0s pre-buffer
        
        # === Statistics ===
        self._frames_received = 0
        self._underruns = 0
        self._available_samples = 0
        self._last_overflow_log = 0
        
        print(f" AudioPlayer: Ring buffer, 20s capacity")
        self._log_available_devices()
    
    def _log_available_devices(self):
        """Log available audio devices"""
        print(" Available audio devices:")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                default = " (DEFAULT)" if i == sd.default.device[1] else ""
                print(f"   [{i}] {dev['name']} ({dev['max_output_channels']} outputs){default}")
    
    # === Buffer Management ===
    
    def _get_available_samples(self):
        """Get number of samples available in buffer
        
        Must be called with buffer lock held.
        """
        if self._write_pos >= self._read_pos:
            return self._write_pos - self._read_pos
        else:
            return self._buffer_size - self._read_pos + self._write_pos
    
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
        if status.output_underflow:
            self._underruns += 1
            if self._underruns % 10 == 0:
                print(f' AudioPlayer: Buffer underrun #{self._underruns}')
        
        with self._buffer_lock:
            available = self._get_available_samples()
            
            # Check if we're still buffering
            if self._buffering:
                if available >= self._min_buffer_samples:
                    self._buffering = False
                    self._underruns = 0
                    print(f" Buffering complete ({available} samples = {available/self.sample_rate:.1f}s)")
                else:
                    # Still buffering - output silence
                    outdata.fill(0)
                    return
            
            if available >= frames:
                # Read from ring buffer
                self._read_from_buffer(outdata, frames)
                
                # Emergency resync if buffer critically large
                self._check_buffer_overflow(available)
            else:
                # Not enough data - output silence
                outdata.fill(0)
                if not self._buffering:
                    self._underruns += 1
                    if self._underruns <= 5 or self._underruns % 10 == 0:
                        print(f" UNDERRUN #{self._underruns} - only {available}/{frames} samples")
    
    def _read_from_buffer(self, outdata, frames):
        """Read frames from ring buffer into output
        
        Handles buffer wraparound automatically.
        
        Args:
            outdata: Output buffer to fill
            frames: Number of frames to read
        """
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
    
    def _check_buffer_overflow(self, available):
        """Check and handle buffer overflow conditions
        
        Performs emergency resync if buffer exceeds 5 seconds.
        Normal target is 1.5 seconds.
        
        Args:
            available: Current number of samples in buffer
        """
        target_buffer = int(self.sample_rate * 4.0)
        hard_max = int(self.sample_rate * 10.0)
        
        if available > hard_max:
            # Emergency resync - buffer critically large
            skip_samples = available - target_buffer
            self._read_pos = (self._read_pos + skip_samples) % self._buffer_size
            if self._frames_received - self._last_overflow_log > 100:
                print(f" Emergency resync ({available/self.sample_rate:.1f}s  {target_buffer/self.sample_rate:.1f}s)")
                self._last_overflow_log = self._frames_received
    
    # === Public API ===
    
    def setSampleRate(self, sample_rate: int, channels: int = None):
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
        self._min_buffer_samples = int(self.sample_rate * 0.8)
        self._current_sample_rate = sample_rate
        
        # Recreate buffer with new channel count
        with self._buffer_lock:
            self._buffer = np.zeros((self._buffer_size, self.channels), dtype=np.int16)
            self._write_pos = 0
            self._read_pos = 0
        
        print(f" Format changed to {sample_rate}Hz, {channels}ch")
        
        # Restart if it was playing
        if was_playing:
            self.start()
    
    def start(self):
        """Start audio playback stream
        
        Initializes sounddevice output stream with high latency
        for maximum stability.
        """
        if self._is_playing:
            return
        
        try:
            # Reset buffer state
            with self._buffer_lock:
                self._write_pos = 0
                self._read_pos = 0
                self._buffering = True
                self._buffer.fill(0)
            
            # Create stream with high latency for stability
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
            print(f" Started ({self.sample_rate}Hz, {self.channels}ch, ring buffer)")
            
        except Exception as e:
            error_msg = f"Failed to start audio: {e}"
            print(f" AudioPlayer: {error_msg}")
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
                self._write_pos = 0
                self._read_pos = 0
                self._buffering = True
            
            self.audioStopped.emit()
            print(f" Stopped (received {self._frames_received} frames, underruns: {self._underruns})")
            
        except Exception as e:
            print(f" Error stopping: {e}")
    
    
    @Slot(object)
    def playAudioData(self, audio_data: tuple):
        """Write audio data to ring buffer
        
        Automatically starts playback if not already playing.
        Handles buffer overflow by dropping oldest data.
        
        Args:
            audio_data: Tuple of interleaved 16-bit PCM samples
        """
        if not self._is_playing:
            self.start()
        
        try:
            # Convert to numpy array
            samples = np.array(audio_data, dtype=np.int16)
            
            # Reshape to (frames, channels)
            frames_count = len(samples) // self.channels
            audio_array = samples[:frames_count * self.channels].reshape(-1, self.channels)
            
            # Write to ring buffer
            with self._buffer_lock:
                self._write_to_buffer(audio_array)
            
            self._frames_received += 1
            
            # Log buffer status periodically
            if self._frames_received % 100 == 0:
                with self._buffer_lock:
                    available = self._get_available_samples()
                    buffer_seconds = available / self.sample_rate
                    print(f" Buffer: {available} samples ({buffer_seconds:.2f}s)")
                    
        except Exception as e:
            print(f" Error playing audio: {e}")
            import traceback
            traceback.print_exc()
    
    def _write_to_buffer(self, audio_array):
        """Write audio array to ring buffer
        
        Handles buffer overflow by dropping oldest data.
        Must be called with buffer lock held.
        
        Args:
            audio_array: Numpy array of shape (frames, channels)
        """
        # Check if we have space
        available = self._get_available_samples()
        free_space = self._buffer_size - available
        
        if free_space < len(audio_array):
            # Buffer overflow - drop oldest data
            overflow = len(audio_array) - free_space
            self._read_pos = (self._read_pos + overflow) % self._buffer_size
            if self._frames_received % 100 == 0:
                print(f" Buffer overflow, dropped {overflow} samples")
        
        # Write data (may wrap around)
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
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set playback volume
        
        Note: Not implemented - sounddevice doesn't support per-stream volume.
        
        Args:
            volume: Volume level 0.0-1.0 (unused)
        """
        print(f" Volume control not available with sounddevice")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()



