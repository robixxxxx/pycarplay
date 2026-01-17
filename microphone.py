#!/usr/bin/env python3
"""
Microphone input for CarPlay (Siri, phone calls)
"""
import sounddevice as sd
import numpy as np
from PySide6.QtCore import QObject, Signal
import threading
import queue


class MicrophoneInput(QObject):
    """
    Microphone input for CarPlay
    Captures audio and sends to CarPlay for Siri/calls
    """
    
    micDataReady = Signal(object)  # Emits audio data tuple
    micStarted = Signal()
    micStopped = Signal()
    micError = Signal(str)
    
    def __init__(self, sample_rate=16000, channels=1):
        super().__init__()
        
        # Audio settings - CarPlay typically uses 16kHz mono for voice
        self.sample_rate = sample_rate
        self.channels = channels
        
        # Audio queue
        self._audio_queue = queue.Queue()
        self._stream = None
        self._is_recording = False
        
        # Statistics
        self._frames_captured = 0
        
        print(f"MicrophoneInput: Initialized ({self.sample_rate}Hz, {self.channels}ch)")
        print(f"MicrophoneInput: Available input devices:")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"  {i}: {dev['name']} ({dev['max_input_channels']} inputs)")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status:
            print(f'MicrophoneInput: {status}')
        
        try:
            # Convert to int16 (CarPlay expects PCM16)
            audio_int16 = (indata * 32767).astype(np.int16)
            
            # Flatten to 1D array and convert to tuple
            audio_tuple = tuple(audio_int16.flatten())
            
            # Emit signal with audio data
            self.micDataReady.emit(audio_tuple)
            
            self._frames_captured += 1
            
            if self._frames_captured % 100 == 0:
                print(f"MicrophoneInput: Captured {self._frames_captured} frames")
                
        except Exception as e:
            print(f"MicrophoneInput: Error in callback: {e}")
    
    def start(self):
        """Start microphone recording"""
        if self._is_recording:
            print("MicrophoneInput: Already recording")
            return
        
        print("MicrophoneInput: Starting microphone...")
        
        try:
            # Create and start input stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',  # Input as float, convert to int16 in callback
                callback=self._audio_callback,
                blocksize=1024,  # 64ms at 16kHz
                latency='low'    # Low latency for voice
            )
            self._stream.start()
            self._is_recording = True
            
            self.micStarted.emit()
            print(f"MicrophoneInput: Started recording ({self.sample_rate}Hz, {self.channels}ch)")
            
        except Exception as e:
            error_msg = f"Failed to start microphone: {e}"
            print(f"MicrophoneInput: {error_msg}")
            self.micError.emit(error_msg)
    
    def stop(self):
        """Stop microphone recording"""
        self._is_recording = False
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self.micStopped.emit()
            print(f"MicrophoneInput: Stopped (captured {self._frames_captured} frames)")
            
        except Exception as e:
            print(f"MicrophoneInput: Error stopping: {e}")
    
    def __del__(self):
        """Cleanup"""
        self.stop()
