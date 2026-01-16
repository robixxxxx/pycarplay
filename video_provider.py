#!/usr/bin/env python3
"""
Video Image Provider for QML
Provides decoded video frames to QML via QQuickPaintedItem
"""
from PySide6.QtCore import QObject, Signal, Slot, Property, Qt, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickPaintedItem
from typing import Optional


class VideoFrameProvider(QQuickPaintedItem):
    """
    QQuickPaintedItem that paints video frames directly in QML
    """
    
    frameCountChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_frame: Optional[QImage] = None
        self._frame_count = 0
        
        # Set flags for better performance
        self.setAntialiasing(True)
        self.setRenderTarget(QQuickPaintedItem.FramebufferObject)
        self.setFillColor(Qt.black)
        
        # Create placeholder
        self._create_placeholder()
    
    def _create_placeholder(self):
        """Create placeholder image"""
        self._current_frame = QImage(1280, 720, QImage.Format_RGB888)
        self._current_frame.fill(Qt.black)
        self.update()
        print("VideoFrameProvider: Placeholder created")
    
    @Slot(QImage)
    def updateFrame(self, frame: QImage):
        """Update with new decoded frame"""
        if frame and not frame.isNull():
            # Keep the frame (no need to copy - it's already copied in decoder)
            self._current_frame = frame
            self._frame_count += 1
            
            # Trigger repaint
            self.update()
            self.frameCountChanged.emit()
            
            if self._frame_count % 30 == 0:
                print(f"VideoFrameProvider: Frame #{self._frame_count} displayed ({frame.width()}x{frame.height()})")
    
    def paint(self, painter: QPainter):
        """Paint the current frame"""
        if not self._current_frame or self._current_frame.isNull():
            # Paint black background
            painter.fillRect(0, 0, self.width(), self.height(), Qt.black)
            return
        
        # Calculate aspect ratio preserving rectangle
        img_width = self._current_frame.width()
        img_height = self._current_frame.height()
        
        if img_width == 0 or img_height == 0:
            return
        
        img_ratio = img_width / img_height
        widget_ratio = self.width() / self.height()
        
        if img_ratio > widget_ratio:
            # Image is wider - fit to width
            scaled_height = self.width() / img_ratio
            y_offset = (self.height() - scaled_height) / 2
            draw_rect = QRectF(0, y_offset, self.width(), scaled_height)
        else:
            # Image is taller - fit to height  
            scaled_width = self.height() * img_ratio
            x_offset = (self.width() - scaled_width) / 2
            draw_rect = QRectF(x_offset, 0, scaled_width, self.height())
        
        # Draw the image with smooth transformation
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(draw_rect, self._current_frame)
    
    @Property(int, notify=frameCountChanged)
    def frameCount(self) -> int:
        """Get total frame count"""
        return self._frame_count
    
    def reset(self):
        """Reset provider"""
        self._create_placeholder()
        self._frame_count = 0
        self.frameCountChanged.emit()
