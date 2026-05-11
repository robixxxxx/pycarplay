#!/usr/bin/env python3
"""
Microphone Input for CarPlay

Captures audio from system microphone for Siri and phone calls.
Converts to PCM16 format (16kHz mono) required by CarPlay.
"""
import sounddevice as sd
import numpy as np
from PySide6.QtCore import QObject, Signal
from ..logging_utils import get_module_logger, log_received_data


LOGGER = get_module_logger(__name__)


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
        LOGGER.info("Microphone initialized: %dHz, %dch", self.sample_rate, self.channels)
        self._log_available_devices()
    
    def _log_available_devices(self):
        """Log available input devices for debugging"""
        LOGGER.info("Available input devices:")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                default = " (DEFAULT)" if i == sd.default.device[0] else ""
                LOGGER.info("[%d] %s (%s inputs)%s", i, dev['name'], dev['max_input_channels'], default)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process audio from sounddevice stream
        
        Converts float32 audio to int16 PCM and emits via signal.
        """
        if status:
            LOGGER.warning("Microphone status: %s", status)
        
        try:
            # Convert float32 (-1.0 to 1.0) to int16 PCM
            audio_int16 = (indata * 32767).astype(np.int16)
            log_received_data(LOGGER, "Microphone captured frame", audio_int16.tobytes())
            
            # Flatten to 1D and convert to tuple for Qt signal
            audio_tuple = tuple(audio_int16.flatten())
            
            # Emit audio data
            self.micDataReady.emit(audio_tuple)
            
            # Statistics
            self._frames_captured += 1
            if self._frames_captured % 100 == 0:
                LOGGER.debug("Captured %d frames", self._frames_captured)
                
        except Exception as e:
            LOGGER.exception("Microphone callback error: %s", e)
            self.micError.emit(str(e))
    
    # === Public API ===
    
    def start(self):
        """Start microphone recording
        
        Opens audio stream and begins capturing audio.
        Audio is emitted via micDataReady signal.
        """
        if self._is_recording:
            LOGGER.info("Microphone already recording")
            return
        
        LOGGER.info("Starting microphone")
        
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
            LOGGER.info("Microphone recording: %dHz, %dch", self.sample_rate, self.channels)
            
        except Exception as e:
            error_msg = f"Failed to start microphone: {e}"
            LOGGER.exception("%s", error_msg)
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
            LOGGER.info("Microphone stopped (captured %d frames)", self._frames_captured)
            
        except Exception as e:
            LOGGER.exception("Error stopping microphone: %s", e)
    
    def __del__(self):
        """Cleanup"""
        self.stop()
