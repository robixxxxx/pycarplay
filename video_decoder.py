#!/usr/bin/env python3
"""
H264 Video Decoder using PyAV
Decodes H264 frames and provides QImage for Qt display
"""
import av
import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, Signal, QMutex, QMutexLocker
from typing import Optional
import io


class VideoDecoder(QObject):
    """H264 video decoder using PyAV (FFmpeg)"""
    
    frameDecoded = Signal(QImage)  # Emits decoded frame as QImage
    
    def __init__(self):
        super().__init__()
        self.codec = None
        self.container = None
        self.stream = None
        self._mutex = QMutex()
        self._frame_count = 0
        
        # Initialize decoder
        self._init_decoder()
    
    def _init_decoder(self):
        """Initialize H264 decoder"""
        try:
            # Create in-memory container for H264 stream
            self.codec = av.CodecContext.create('h264', 'r')
            self.codec.thread_type = 'AUTO'
            print("H264 decoder initialized")
        except Exception as e:
            print(f"Failed to initialize H264 decoder: {e}")
            raise
    
    def decode_frame(self, h264_data: bytes) -> Optional[QImage]:
        """
        Decode H264 frame data
        
        Args:
            h264_data: Raw H264 encoded data
            
        Returns:
            QImage if successful, None otherwise
        """
        with QMutexLocker(self._mutex):
            try:
                # Create packet from H264 data
                packet = av.Packet(h264_data)
                
                # Decode packet
                frames = self.codec.decode(packet)
                
                for frame in frames:
                    self._frame_count += 1
                    
                    # Convert to RGB
                    frame_rgb = frame.to_rgb().to_ndarray()
                    
                    # Create QImage from numpy array
                    height, width, channels = frame_rgb.shape
                    bytes_per_line = channels * width
                    
                    qimage = QImage(
                        frame_rgb.data,
                        width,
                        height,
                        bytes_per_line,
                        QImage.Format_RGB888
                    )
                    
                    # Copy image data (important!)
                    qimage = qimage.copy()
                    
                    # Emit signal
                    self.frameDecoded.emit(qimage)
                    
                    if self._frame_count % 30 == 0:
                        print(f"Decoded frame #{self._frame_count}: {width}x{height}")
                    
                    return qimage
                
                return None
                
            except Exception as e:
                if self._frame_count < 5:  # Only print first few errors
                    print(f"Error decoding frame: {e}")
                return None
    
    def flush(self):
        """Flush decoder buffer"""
        try:
            if self.codec:
                frames = self.codec.decode(None)
                for frame in frames:
                    frame_rgb = frame.to_rgb().to_ndarray()
                    height, width, channels = frame_rgb.shape
                    bytes_per_line = channels * width
                    qimage = QImage(
                        frame_rgb.data,
                        width,
                        height,
                        bytes_per_line,
                        QImage.Format_RGB888
                    ).copy()
                    self.frameDecoded.emit(qimage)
        except Exception as e:
            print(f"Error flushing decoder: {e}")
    
    def reset(self):
        """Reset decoder state"""
        with QMutexLocker(self._mutex):
            try:
                self.codec.close()
                self._init_decoder()
                self._frame_count = 0
                print("Decoder reset")
            except Exception as e:
                print(f"Error resetting decoder: {e}")
