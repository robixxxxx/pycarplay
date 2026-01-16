#!/usr/bin/env python3
"""
PySide6 application with QML for displaying video stream
"""
import sys
from pathlib import Path
from PySide6.QtCore import QUrl, QObject, Slot, Signal, Property, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from carplay_node import CarplayNode, CarplayMessage, MessageType
from dongle_driver import DongleConfig, HandDriveType
from messages import VideoData, AudioData, Plugged, Unplugged, Opened
from video_decoder import VideoDecoder
from video_provider import VideoFrameProvider


class VideoStreamController(QObject):
    """Controller class for managing video stream"""
    
    videoSourceChanged = Signal(str)
    dongleStatusChanged = Signal(str)
    dongleConnected = Signal()
    dongleDisconnected = Signal()
    videoFrameReceived = Signal(int, int, int)  # width, height, data_length
    
    def __init__(self, video_provider: VideoFrameProvider):
        super().__init__()
        self._video_source = ""
        self._dongle_status = "Disconnected"
        self._carplay_node = None
        self._video_decoder = VideoDecoder()
        self._video_provider = video_provider
        
        # Connect decoder to video provider
        self._video_decoder.frameDecoded.connect(self._video_provider.updateFrame)
        
    @Property(str, notify=videoSourceChanged)
    def videoSource(self):
        return self._video_source
    
    @videoSource.setter
    def videoSource(self, value):
        if self._video_source != value:
            self._video_source = value
            self.videoSourceChanged.emit(value)
    
    @Slot(str)
    def loadVideo(self, url):
        """Load video from URL or file path"""
        print(f"Loading video: {url}")
        self._video_source = url
        self.videoSourceChanged.emit(url)
    
    @Slot()
    def playVideo(self):
        """Start video playback"""
        print("Playing video")
    
    @Slot()
    def pauseVideo(self):
        """Pause video playback"""
        print("Pausing video")
    
    @Slot()
    def stopVideo(self):
        """Stop video playback"""
        print("Stopping video")
    
    @Property(str, notify=dongleStatusChanged)
    def dongleStatus(self):
        return self._dongle_status
    
    @dongleStatus.setter
    def dongleStatus(self, value):
        if self._dongle_status != value:
            self._dongle_status = value
            self.dongleStatusChanged.emit(value)
    
    @Slot()
    def connectDongle(self):
        """Connect to USB dongle"""
        try:
            self.dongleStatus = "Connecting..."
            
            # Create CarPlay config
            config = DongleConfig(
                width=1280,
                height=720,
                fps=30,
                dpi=160,
                box_name="pyCarPlay",
                hand=HandDriveType.LHD,
                wifi_type="5ghz",
                mic_type="os"
            )
            
            # Create CarPlay node
            self._carplay_node = CarplayNode(config)
            self._carplay_node.onmessage = self._on_carplay_message
            
            # Start in separate thread to not block UI
            import threading
            thread = threading.Thread(target=self._carplay_node.start, daemon=True)
            thread.start()
            
            self.dongleStatus = "Initializing..."
            print("CarPlay connection initiated")
            
        except Exception as e:
            self.dongleStatus = f"Error: {str(e)}"
            print(f"Failed to connect dongle: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot()
    def disconnectDongle(self):
        """Disconnect from USB dongle"""
        try:
            if self._carplay_node:
                self._carplay_node.stop()
                self._carplay_node = None
            
            self.dongleStatus = "Disconnected"
            self.dongleDisconnected.emit()
            print("Dongle disconnected")
        except Exception as e:
            print(f"Error disconnecting dongle: {e}")
    
    def _on_carplay_message(self, msg: CarplayMessage):
        """Handle messages from CarPlay node"""
        
        if msg.msg_type == MessageType.PLUGGED:
            if isinstance(msg.message, Plugged):
                phone_type = msg.message.phone_type.name
                print(f"Phone plugged: {phone_type}")
                self.dongleStatus = f"Connected - {phone_type}"
                self.dongleConnected.emit()
        
        elif msg.msg_type == MessageType.UNPLUGGED:
            print("Phone unplugged")
            self.dongleStatus = "Connected - No phone"
        
        elif msg.msg_type == MessageType.VIDEO:
            if isinstance(msg.message, VideoData):
                # Decode H264 frame
                self._video_decoder.decode_frame(msg.message.data)
                # Signal is emitted automatically via frameDecoded -> updateFrame
                
                # Emit info signal every 30 frames
                if self._video_provider.frameCount % 30 == 0:
                    self.videoFrameReceived.emit(
                        msg.message.width, 
                        msg.message.height, 
                        len(msg.message.data)
                    )
        
        elif msg.msg_type == MessageType.AUDIO:
            if isinstance(msg.message, AudioData):
                if msg.message.data:
                    print(f"Audio data: {len(msg.message.data)} samples")
                    # TODO: Play audio
        
        elif msg.msg_type == MessageType.FAILURE:
            print("CarPlay communication failed")
            self.dongleStatus = "Failed"
            self.dongleDisconnected.emit()
        
        elif msg.msg_type == MessageType.COMMAND:
            print(f"Command received: {msg.message.value}")
        
        elif msg.msg_type == MessageType.MEDIA:
            print(f"Media data: {msg.message.payload}")
    
    @Slot(str)
    def sendKey(self, action: str):
        """Send key command to CarPlay"""
        if self._carplay_node:
            self._carplay_node.send_key(action)
            print(f"Sent key: {action}")
    
    @Slot(float, float, int)
    def sendTouch(self, x: float, y: float, action: int):
        """Send touch event to CarPlay
        
        Args:
            x: X coordinate in video space (0-1280)
            y: Y coordinate in video space (0-720)
            action: TouchAction value (14=Down, 15=Move, 16=Up)
        """
        if self._carplay_node:
            from sendable import TouchAction
            
            # Normalize coordinates to 0.0-1.0 range
            # Video is 1280x720
            norm_x = x / 1280.0
            norm_y = y / 720.0
            
            # Clamp to valid range
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))
            
            action_name = {14: "DOWN", 15: "MOVE", 16: "UP"}.get(action, f"UNKNOWN({action})")
            self._carplay_node.send_touch(norm_x, norm_y, TouchAction(action))
            print(f"🖱️  Touch {action_name}: screen({int(x)}, {int(y)}) -> normalized({norm_x:.3f}, {norm_y:.3f})")


def main():
    app = QGuiApplication(sys.argv)
    
    # Create video frame provider instance FIRST
    video_provider = VideoFrameProvider()
    
    # Create video controller
    video_controller = VideoStreamController(video_provider)
    
    # Create QML engine
    engine = QQmlApplicationEngine()
    
    # Expose to QML context
    engine.rootContext().setContextProperty("videoController", video_controller)
    engine.rootContext().setContextProperty("videoDisplay", video_provider)
    
    # Load QML file
    qml_file = Path(__file__).parent / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    
    if not engine.rootObjects():
        sys.exit(-1)
    
    # Get root object and find video container
    root = engine.rootObjects()[0]
    video_container = root.findChild(QObject, "videoContainer")
    
    if video_container:
        # Set videoDisplay as child of container
        video_provider.setParentItem(video_container)
        video_provider.setWidth(video_container.property("width"))
        video_provider.setHeight(video_container.property("height"))
        print(f"VideoDisplay attached to container: {video_container.property('width')}x{video_container.property('height')}")
    else:
        print("Warning: videoContainer not found!")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
