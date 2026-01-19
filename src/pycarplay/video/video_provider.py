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
    fillModeChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_frame: Optional[QImage] = None
        self._frame_count = 0
        self._last_draw_rect = QRectF()  # Initialize draw rect
        self._fill_mode = "fit"  # "fit" or "stretch"
        
        # Set flags for better performance
        self.setAntialiasing(True)
        self.setRenderTarget(QQuickPaintedItem.FramebufferObject)
        self.setFillColor(Qt.black)
        
        # Create placeholder
        self._create_placeholder()
    
    @Property(str, notify=fillModeChanged)
    def fillMode(self):
        """Get fill mode (fit/stretch)"""
        return self._fill_mode
    
    @fillMode.setter
    def fillMode(self, mode: str):
        """Set fill mode (fit/stretch)"""
        if self._fill_mode != mode and mode in ["fit", "stretch"]:
            self._fill_mode = mode
            self.fillModeChanged.emit()
            self.update()  # Redraw with new mode
            print(f"VideoFrameProvider: Fill mode changed to {mode}")
    
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
            # Log first frame and then every 10 frames so we can verify frames are arriving
            if self._frame_count == 1 or (self._frame_count % 10 == 0):
                try:
                    print(f"VideoFrameProvider: Frame #{self._frame_count} displayed ({frame.width()}x{frame.height()})")
                except Exception:
                    # Avoid logging errors from malformed frames
                    print(f"VideoFrameProvider: Frame #{self._frame_count} displayed")
    
    def paint(self, painter: QPainter):
        """Paint the current frame"""
        if not self._current_frame or self._current_frame.isNull():
            # Paint black background
            painter.fillRect(0, 0, self.width(), self.height(), Qt.black)
            return
        
        # Calculate drawing rectangle based on fill mode
        img_width = self._current_frame.width()
        img_height = self._current_frame.height()
        
        if img_width == 0 or img_height == 0:
            return
        
        if self._fill_mode == "stretch":
            # Stretch to fill entire window
            draw_rect = QRectF(0, 0, self.width(), self.height())
        else:
            # Fit - preserve aspect ratio
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
        
        # Store draw_rect for touch coordinate conversion
        self._last_draw_rect = draw_rect
        
        # Draw the image with smooth transformation
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(draw_rect, self._current_frame)
    
    @Slot(float, float, result='QVariantList')
    def mapToVideoCoordinates(self, screen_x: float, screen_y: float):
        """
        Convert screen coordinates to video coordinates (1280x720)
        Returns [x, y] in video space, or [-1, -1] if outside video area
        """
        if not hasattr(self, '_last_draw_rect') or not self._current_frame:
            return [-1, -1]
        
        draw_rect = self._last_draw_rect
        
        # Check if point is inside the actual video area
        if (screen_x < draw_rect.x() or screen_x > draw_rect.x() + draw_rect.width() or
            screen_y < draw_rect.y() or screen_y > draw_rect.y() + draw_rect.height()):
            return [-1, -1]
        
        # Convert to normalized coordinates within the draw rect (0.0 to 1.0)
        norm_x = (screen_x - draw_rect.x()) / draw_rect.width()
        norm_y = (screen_y - draw_rect.y()) / draw_rect.height()
        
        # Scale to video resolution
        video_x = norm_x * self._current_frame.width()
        video_y = norm_y * self._current_frame.height()
        
        return [int(video_x), int(video_y)]
    
    @Property(int, notify=frameCountChanged)
    def frameCount(self) -> int:
        """Get total frame count"""
        return self._frame_count
    
    def reset(self):
        """Reset provider"""
        self._create_placeholder()
        self._frame_count = 0
        self.frameCountChanged.emit()
