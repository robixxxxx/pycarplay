#!/usr/bin/env python3
"""
H264 Video Decoder for CarPlay

Decodes H264 video streams using PyAV (FFmpeg) and provides QImage
frames for Qt display. Features automatic error recovery and
frame statistics.
"""
import av
import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, Signal, QMutex, QMutexLocker
from typing import Optional


class VideoDecoder(QObject):
    """H264 video decoder using PyAV
    
    Features:
    - Thread-safe decoding with mutex protection
    - Automatic error recovery after consecutive failures
    - Frame statistics and logging
    - Direct RGB conversion for Qt display
    """
    
    # === Signals ===
    frameDecoded = Signal(QImage)  # Decoded frame ready for display
    tooManyErrors = Signal()       # Too many consecutive decode errors
    
    def __init__(self):
        super().__init__()
        
        # === Decoder State ===
        self.codec = None
        self._mutex = QMutex()
        
        # === Statistics ===
        self._frame_count = 0
        self._error_count = 0
        self._consecutive_errors = 0
        self._max_consecutive_errors = 10
        
        # Initialize decoder
        self._init_decoder()
    
    # === Initialization ===
    
    def _init_decoder(self):
        """Initialize H264 decoder with FFmpeg
        
        Raises:
            Exception: If decoder initialization fails
        """
        try:
            self.codec = av.CodecContext.create('h264', 'r')
            self.codec.thread_type = 'AUTO'
            print(" H264 decoder initialized")
        except Exception as e:
            print(f" Failed to initialize H264 decoder: {e}")
            raise
    
    # === Public API ===
    
    def decode_frame(self, h264_data: bytes) -> Optional[QImage]:
        """Decode H264 frame data to QImage
        
        Thread-safe decoding with automatic error handling.
        Emits frameDecoded signal on success.
        
        Args:
            h264_data: Raw H264 encoded data
            
        Returns:
            QImage if successful, None otherwise
        """
        with QMutexLocker(self._mutex):
            try:
                # Decode H264 packet
                packet = av.Packet(h264_data)
                frames = self.codec.decode(packet)
                
                for frame in frames:
                    qimage = self._convert_frame_to_qimage(frame)
                    
                    # Success - emit signal and reset error counter
                    self.frameDecoded.emit(qimage)
                    self._consecutive_errors = 0
                    
                    # Log progress
                    self._frame_count += 1
                    if self._frame_count % 30 == 0:
                        print(f" Decoded frame #{self._frame_count}: {qimage.width()}x{qimage.height()}")
                    
                    return qimage
                
                return None
                
            except Exception as e:
                self._handle_decode_error(e)
                return None
    
    def _convert_frame_to_qimage(self, frame) -> QImage:
        """Convert PyAV frame to QImage
        
        Args:
            frame: PyAV video frame
            
        Returns:
            QImage in RGB888 format
        """
        # Convert to RGB numpy array
        frame_rgb = frame.to_rgb().to_ndarray()
        height, width, channels = frame_rgb.shape
        bytes_per_line = channels * width
        
        # Create QImage
        qimage = QImage(
            frame_rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )
        
        # Copy image data (important - frame_rgb will be deallocated!)
        return qimage.copy()
    
    def _handle_decode_error(self, error: Exception):
        """Handle decode error with automatic recovery
        
        Args:
            error: Exception that occurred during decoding
        """
        self._error_count += 1
        self._consecutive_errors += 1
        self._error_count += 1
        self._consecutive_errors += 1
        
        if self._consecutive_errors <= 5:
            print(f" Error decoding frame: {error}")
        elif self._consecutive_errors == self._max_consecutive_errors:
            print(f" TOO MANY DECODE ERRORS ({self._consecutive_errors} in a row)")
            self.tooManyErrors.emit()
    
    def flush(self):
        """Flush decoder buffer
        
        Decodes and emits any remaining frames in the decoder buffer.
        Call this when stream ends or before resetting.
        """
        try:
            if self.codec:
                frames = self.codec.decode(None)
                for frame in frames:
                    qimage = self._convert_frame_to_qimage(frame)
                    self.frameDecoded.emit(qimage)
        except Exception as e:
            print(f" Error flushing decoder: {e}")
    
    def reset(self):
        """Reset decoder state
        
        Closes and reinitializes the decoder, clearing all state
        and statistics.
        """
        with QMutexLocker(self._mutex):
            try:
                self.codec.close()
                self._init_decoder()
                self._frame_count = 0
                self._error_count = 0
                self._consecutive_errors = 0
                print(" Decoder reset")
            except Exception as e:
                print(f" Error resetting decoder: {e}")

