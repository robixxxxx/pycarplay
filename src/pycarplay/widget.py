"""
CarPlay Widget for embedding in PyQt6 applications

This module provides a widget component that can be embedded in any PyQt6 application.
It does NOT create its own window - it's meant to be added to existing layouts.
"""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QUrl, QTimer, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickWidgets import QQuickWidget

from .config import CarPlayConfig, DEFAULT_CONFIG
from .video.video_provider import VideoFrameProvider
from .controller import VideoStreamController


class CarPlayWidget(QWidget):
    """
    CarPlay integration widget for PyQt6 applications
    
    This is a COMPONENT widget meant to be embedded in your application.
    It provides CarPlay functionality with video display and touch interaction.
    
    Signals:
        dongleConnected() - Emitted when dongle connects
        dongleDisconnected() - Emitted when dongle disconnects
        dongleStatusChanged(str) - Emitted when connection status changes
        phoneConnected() - Emitted when phone is plugged into dongle
        phoneDisconnected() - Emitted when phone is unplugged
        videoFrameReceived(int, int, int) - Emitted on new video frame (width, height, data_len)
        currentSongChanged(str) - Emitted when song changes
        currentArtistChanged(str) - Emitted when artist changes
        navigationInfoChanged(str) - Emitted when navigation info changes
        connectionFailed() - Emitted when connection fails
        
    Args:
        config: CarPlayConfig instance with custom settings (optional)
        custom_qml_path: Path to custom QML file to replace default UI (optional)
        parent: Parent Qt widget (optional)
        
    Example:
        Embed in existing window::
        
            from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
            from pycarplay import CarPlayWidget
            
            class MyApp(QMainWindow):
                def __init__(self):
                    super().__init__()
                    
                    # Create central widget with layout
                    central = QWidget()
                    layout = QVBoxLayout(central)
                    
                    # Add CarPlay widget
                    self.carplay = CarPlayWidget()
                    layout.addWidget(self.carplay)
                    
                    # Connect to signals
                    self.carplay.phoneConnected.connect(self.on_phone_connected)
                    
                    self.setCentralWidget(central)
                
                def on_phone_connected(self):
                    print("Phone connected!")
            
            app = QApplication([])
            window = MyApp()
            window.show()
            app.exec()
            
        With custom configuration::
        
            config = CarPlayConfig()
            config.video.width = 1920
            config.video.height = 1080
            config.dongle.auto_connect = False
            
            carplay = CarPlayWidget(config=config)
            
        Connect buttons to control::
        
            connect_btn.clicked.connect(self.carplay.connect)
            disconnect_btn.clicked.connect(self.carplay.disconnect)
            home_btn.clicked.connect(self.carplay.send_home)
    """
    
    # Public signals that can be connected from parent application
    dongleConnected = Signal()
    dongleDisconnected = Signal()
    dongleStatusChanged = Signal(str)
    phoneConnected = Signal()
    phoneDisconnected = Signal()
    videoFrameReceived = Signal(int, int, int)  # width, height, data_length
    currentSongChanged = Signal(str)
    currentArtistChanged = Signal(str)
    navigationInfoChanged = Signal(str)
    connectionFailed = Signal()
    
    def __init__(
        self, 
        config: Optional[CarPlayConfig] = None,
        custom_qml_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        # Use provided config or default
        self.config = config if config is not None else DEFAULT_CONFIG
        
        # Override with custom QML path if provided
        if custom_qml_path:
            self.config.ui.custom_qml_path = custom_qml_path
        
        # Setup widget
        self._setup_ui()
        self._setup_controller()
        self._connect_signals()
        
        # Auto-connect if configured
        if self.config.dongle.auto_connect:
            # Delay to allow UI to fully load
            QTimer.singleShot(500, self.connect)
    
    def _setup_ui(self):
        # Register VideoFrameProvider as a QML type (for QML instantiation)
        from PySide6.QtQml import qmlRegisterType
        from .video.video_provider import VideoFrameProvider
        qmlRegisterType(VideoFrameProvider, 'PyCarPlay', 1, 0, 'VideoFrameProvider')
        """Setup the Qt Quick widget with QML UI"""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create video frame provider
        self.video_provider = VideoFrameProvider()
        
        # Create QML widget
        self.qml_widget = QQuickWidget()
        self.qml_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        
        # Get QML path
        qml_path = self._get_qml_path()
        
        # Add import paths for components
        engine = self.qml_widget.engine()
        ui_path = Path(__file__).parent / 'ui'
        components_path = ui_path / 'components'
        engine.addImportPath(str(ui_path))
        engine.addImportPath(str(components_path))
        
        # Register video provider BEFORE loading QML
        self.qml_widget.rootContext().setContextProperty("videoProvider", self.video_provider)
        
        # Create and register controller BEFORE loading QML
        self.controller = VideoStreamController(
            video_provider=self.video_provider,
            config=self.config
        )
        self.qml_widget.rootContext().setContextProperty("videoController", self.controller)
        
        # Load QML (now videoController is available)
        self.qml_widget.setSource(QUrl.fromLocalFile(str(qml_path)))
        
        # Check for QML errors
        if self.qml_widget.status() == QQuickWidget.Error:
            print("QML Errors:")
            for error in self.qml_widget.errors():
                print(f"  {error.toString()}")
        
        # Add to layout
        layout.addWidget(self.qml_widget)
        
        # Set window properties from config
        if self.config.ui.window_title:
            self.setWindowTitle(self.config.ui.window_title)
        
        # Set initial size from video config
        self.resize(self.config.video.width, self.config.video.height)
    
    def _get_qml_path(self) -> Path:
        """Get path to QML file (custom or default)"""
        if self.config.ui.custom_qml_path:
            custom_path = Path(self.config.ui.custom_qml_path)
            if custom_path.exists():
                return custom_path
            else:
                print(f"Warning: Custom QML not found: {custom_path}")
                print("Using default QML")
        
        # Use default QML
        default_qml = Path(__file__).parent / 'ui' / 'default' / 'Main.qml'
        return default_qml
    
    def _setup_controller(self):
        """Apply initial video configuration to controller"""
        # Apply video configuration (controller already created in _setup_ui)
        self.controller.apply_video_config(
            self.config.video.width,
            self.config.video.height,
            self.config.video.dpi
        )
    
    def _connect_signals(self):
        """Connect controller signals to widget signals"""
        # Forward all controller signals to widget signals
        self.controller.dongleConnected.connect(self.dongleConnected)
        self.controller.dongleDisconnected.connect(self.dongleDisconnected)
        self.controller.dongleStatusChanged.connect(self.dongleStatusChanged)
        self.controller.videoFrameReceived.connect(self.videoFrameReceived)
        self.controller.currentSongChanged.connect(self.currentSongChanged)
        self.controller.currentArtistChanged.connect(self.currentArtistChanged)
        self.controller.navigationInfoChanged.connect(self.navigationInfoChanged)
        self.controller.connectionFailed.connect(self.connectionFailed)
        
        # Track phone connection state
        self.controller.dongleConnected.connect(self._on_controller_connected)
        self.controller.dongleDisconnected.connect(self._on_controller_disconnected)
    
    def _on_controller_connected(self):
        """Handle when phone connects to dongle"""
        # Check if it's actually a phone connection (not just dongle)
        status = self.controller.dongleStatus
        if "iPhone" in status or "Android" in status or "phone" in status.lower():
            self.phoneConnected.emit()
    
    def _on_controller_disconnected(self):
        """Handle when phone disconnects"""
        self.phoneDisconnected.emit()
    
    # === Public API - Status Methods ===
    
    def is_connected(self) -> bool:
        """
        Check if CarPlay dongle is connected
        
        Returns:
            bool: True if dongle is connected, False otherwise
            
        Example:
            if carplay.is_connected():
                print("Dongle is connected")
        """
        if not self.controller:
            return False
        status = self.controller.dongleStatus
        return status.startswith("Connected")
    
    def is_phone_connected(self) -> bool:
        """
        Check if phone is connected to CarPlay dongle
        
        Returns:
            bool: True if phone is plugged in and connected, False otherwise
            
        Example:
            if carplay.is_phone_connected():
                print("Phone is ready")
        """
        if not self.controller:
            return False
        status = self.controller.dongleStatus
        # Check if status indicates an actual phone connection
        return ("iPhone" in status or "Android" in status or 
                (status.startswith("Connected") and "No phone" not in status))
    
    def get_status(self) -> str:
        """
        Get current connection status text
        
        Returns:
            str: Status string (e.g., "Connected - iPhone", "Disconnected", etc.)
            
        Example:
            status = carplay.get_status()
            print(f"Status: {status}")
        """
        if not self.controller:
            return "Not initialized"
        return self.controller.dongleStatus
    
    def get_current_song(self) -> str:
        """
        Get currently playing song name
        
        Returns:
            str: Song name or empty string if nothing playing
            
        Example:
            song = carplay.get_current_song()
            if song:
                print(f"Playing: {song}")
        """
        if not self.controller:
            return ""
        return self.controller.currentSong
    
    def get_current_artist(self) -> str:
        """
        Get current artist name
        
        Returns:
            str: Artist name or empty string
            
        Example:
            artist = carplay.get_current_artist()
        """
        if not self.controller:
            return ""
        return self.controller.currentArtist
    
    # === Public Slots - Button Control Methods ===
    
    @Slot()
    def connect(self):
        """
        Connect to CarPlay dongle
        
        This can be connected to a button's clicked signal:
            connect_button.clicked.connect(carplay_widget.connect)
        """
        self.controller.connectDongle()
    
    @Slot()
    def disconnect(self):
        """
        Disconnect from CarPlay dongle
        
        This can be connected to a button's clicked signal:
            disconnect_button.clicked.connect(carplay_widget.disconnect)
        """
        self.controller.disconnectDongle()
    
    @Slot()
    def toggle_audio(self):
        """
        Toggle audio mute/unmute
        
        This can be connected to a button's clicked signal:
            mute_button.clicked.connect(carplay_widget.toggle_audio)
        """
        self.controller.toggleAudio()
    
    @Slot(float)
    def set_volume(self, volume: float):
        """
        Set audio volume (0.0 to 1.0)
        
        This can be connected to a slider's valueChanged signal:
            volume_slider.valueChanged.connect(
                lambda v: carplay_widget.set_volume(v / 100.0)
            )
        
        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (max)
        """
        self.controller.setVolume(volume)
    
    @Slot()
    def send_home(self):
        """
        Send Home button press to CarPlay
        
        This can be connected to a button's clicked signal:
            home_button.clicked.connect(carplay_widget.send_home)
        """
        self.controller.sendKey("home")
    
    @Slot()
    def send_back(self):
        """
        Send Back button press to CarPlay
        
        This can be connected to a button's clicked signal:
            back_button.clicked.connect(carplay_widget.send_back)
        """
        self.controller.sendKey("back")
    
    @Slot()
    def send_play_pause(self):
        """
        Send Play/Pause button press to CarPlay
        
        This can be connected to a button's clicked signal:
            play_button.clicked.connect(carplay_widget.send_play_pause)
        """
        self.controller.sendKey("playOrPause")
    
    @Slot()
    def send_next_track(self):
        """
        Send Next Track button press to CarPlay
        
        This can be connected to a button's clicked signal:
            next_button.clicked.connect(carplay_widget.send_next_track)
        """
        self.controller.sendKey("right")
    
    @Slot()
    def send_previous_track(self):
        """
        Send Previous Track button press to CarPlay
        
        This can be connected to a button's clicked signal:
            prev_button.clicked.connect(carplay_widget.send_previous_track)
        """
        self.controller.sendKey("left")
    
    @Slot()
    def show_settings(self):
        """
        Show CarPlay settings panel
        
        This can be connected to a button's clicked signal:
            settings_button.clicked.connect(carplay_widget.show_settings)
        """
        self.controller.showConfigPanel.emit()
    
    @Slot()
    def hide_settings(self):
        """
        Hide CarPlay settings panel
        
        This can be connected to a button's clicked signal:
            close_settings_button.clicked.connect(carplay_widget.hide_settings)
        """
        self.controller.hideConfigPanel.emit()
    
    # === Legacy methods for compatibility ===
    
    def connect_dongle(self):
        """Legacy method - use connect() instead"""
        self.connect()
    
    def disconnect_dongle(self):
        """Legacy method - use disconnect() instead"""
        self.disconnect()
    
    def get_controller(self) -> VideoStreamController:
        """
        Get the VideoStreamController instance
        
        Returns:
            VideoStreamController for advanced control
        """
        return self.controller
    
    def set_config(self, config: CarPlayConfig):
        """
        Update configuration (requires restart to take effect)
        
        Args:
            config: New CarPlayConfig instance
        """
        self.config = config
        # Note: Full config update requires widget recreation
        # Only video settings can be updated live
        if self.controller:
            self.controller.apply_video_config(
                config.video.width,
                config.video.height,
                config.video.dpi
            )
