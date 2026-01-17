#!/usr/bin/env python3
"""
Microphone Input for CarPlay

Captures audio from system microphone for Siri and phone calls.
Converts to PCM16 format (16kHz mono) required by CarPlay.
"""
import sounddevice as sd
import numpy as np
from PySide6.QtCore import QObject, Signal


class MicrophoneInput(QObject):
    """Microphone input handler for CarPlay voice features
    
    Captures audio at 16kHz mono (CarPlay voice standard) and
    emits processed audio data ready for transmission.
    """
    
    # === Signals ===
    micDataReady = Signal(object)  # Emits audio data tuple (int16 PCM)
    micStarted = Signal()
    micStopped = Signal()
    micError = Signal(str)
    
    def __init__(self, sample_rate=16000, channels=1):
        super().__init__()
        
        # === Audio Configuration ===
        self.sample_rate = sample_rate  # CarPlay uses 16kHz for voice
        self.channels = channels  # Mono for voice
        
        # === State ===
        self._stream = None
        self._is_recording = False
        self._frames_captured = 0
        
        # === Initialization ===
        print(f"🎤 Microphone: {self.sample_rate}Hz, {self.channels}ch")
        self._log_available_devices()
    
    def _log_available_devices(self):
        """Log available input devices for debugging"""
        print("🎤 Available input devices:")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                default = " (DEFAULT)" if i == sd.default.device[0] else ""
                print(f"   [{i}] {dev['name']} ({dev['max_input_channels']} inputs){default}")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process audio from sounddevice stream
        
        Converts float32 audio to int16 PCM and emits via signal.
        """
        if status:
            print(f'⚠️  Microphone status: {status}')
        
        try:
            # Convert float32 (-1.0 to 1.0) to int16 PCM
            audio_int16 = (indata * 32767).astype(np.int16)
            
            # Flatten to 1D and convert to tuple for Qt signal
            audio_tuple = tuple(audio_int16.flatten())
            
            # Emit audio data
            self.micDataReady.emit(audio_tuple)
            
            # Statistics
            self._frames_captured += 1
            if self._frames_captured % 100 == 0:
                print(f"🎤 Captured {self._frames_captured} frames")
                
        except Exception as e:
            print(f"❌ Microphone callback error: {e}")
            self.micError.emit(str(e))
    
    # === Public API ===
    
    def start(self):
        """Start microphone recording
        
        Opens audio stream and begins capturing audio.
        Audio is emitted via micDataReady signal.
        """
        if self._is_recording:
            print("⚠️  Microphone already recording")
            return
        
        print("🎤 Starting microphone...")
        
        try:
            # Create and start input stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',  # Will be converted to int16
                callback=self._audio_callback,
                blocksize=1024,  # 64ms at 16kHz
                latency='low'     # Low latency for voice
            )
            self._stream.start()
            self._is_recording = True
            self._frames_captured = 0
            
            self.micStarted.emit()
            print(f"✅ Microphone recording: {self.sample_rate}Hz, {self.channels}ch")
            
        except Exception as e:
            error_msg = f"Failed to start microphone: {e}"
            print(f"❌ {error_msg}")
            self.micError.emit(error_msg)
    
    def stop(self):
        """Stop microphone recording
        
        Closes audio stream and stops capturing.
        """
        if not self._is_recording:
            return
        
        self._is_recording = False
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self.micStopped.emit()
            print(f"🎤 Stopped (captured {self._frames_captured} frames)")
            
        except Exception as e:
            print(f"❌ Error stopping microphone: {e}")
            print(f"MicrophoneInput: Error stopping: {e}")
    
    def __del__(self):
        """Cleanup"""
        self.stop()
