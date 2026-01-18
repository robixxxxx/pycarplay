#!/usr/bin/env python3
"""
Embedded Widget with Controls Example

This example shows how to embed CarPlayWidget with control buttons.
Demonstrates connecting buttons to CarPlay widget signals/slots.
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QGroupBox
)
from PySide6.QtCore import Qt
import sys

from pycarplay import CarPlayWidget, CarPlayConfig

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CarPlay with Controls")
        self.resize(1600, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout (horizontal split)
        layout = QHBoxLayout(central)
        
        # Left side - CarPlay widget
        config = CarPlayConfig()
        config.video.width = 1280
        config.video.height = 720
        config.dongle.auto_connect = True
        
        self.carplay = CarPlayWidget(config=config)
        layout.addWidget(self.carplay, stretch=3)
        
        # Right side - Control panel
        controls = self._create_controls()
        layout.addWidget(controls, stretch=1)
        
        # Connect CarPlay signals to UI updates
        self._connect_carplay_signals()
    
    def _create_controls(self):
        """Create control panel widget"""
        controls = QWidget()
        controls.setMaximumWidth(300)
        controls_layout = QVBoxLayout(controls)
        
        # Title
        title = QLabel("CarPlay Controls")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        controls_layout.addWidget(title)
        
        # Connection controls
        connection_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout(connection_group)
        
        connect_btn = QPushButton("Connect Dongle")
        connect_btn.clicked.connect(self.carplay.connect)  # <-- Connect to slot
        conn_layout.addWidget(connect_btn)
        
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self.carplay.disconnect)  # <-- Connect to slot
        conn_layout.addWidget(disconnect_btn)
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 5px; background: #333; border-radius: 3px;")
        conn_layout.addWidget(self.status_label)
        
        controls_layout.addWidget(connection_group)
        
        # Navigation controls
        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout(nav_group)
        
        home_btn = QPushButton("Home")
        home_btn.clicked.connect(self.carplay.send_home)  # <-- Connect to slot
        nav_layout.addWidget(home_btn)
        
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.carplay.send_back)  # <-- Connect to slot
        nav_layout.addWidget(back_btn)
        
        controls_layout.addWidget(nav_group)
        
        # Media controls
        media_group = QGroupBox("Media")
        media_layout = QVBoxLayout(media_group)
        
        play_btn = QPushButton("Play/Pause")
        play_btn.clicked.connect(self.carplay.send_play_pause)  # <-- Connect to slot
        media_layout.addWidget(play_btn)
        
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.carplay.send_previous_track)  # <-- Connect to slot
        media_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.carplay.send_next_track)  # <-- Connect to slot
        media_layout.addWidget(next_btn)
        
        self.song_label = QLabel("No song playing")
        self.song_label.setWordWrap(True)
        self.song_label.setStyleSheet("padding: 5px; background: #333; border-radius: 3px; font-size: 11px;")
        media_layout.addWidget(self.song_label)
        
        controls_layout.addWidget(media_group)
        
        # Volume control
        volume_group = QGroupBox("Volume")
        vol_layout = QVBoxLayout(volume_group)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        # Connect slider to CarPlay volume control
        self.volume_slider.valueChanged.connect(
            lambda v: self.carplay.set_volume(v / 100.0)  # <-- Connect to slot with lambda
        )
        vol_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("80%")
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        vol_layout.addWidget(self.volume_label)
        
        mute_btn = QPushButton("Toggle Mute")
        mute_btn.clicked.connect(self.carplay.toggle_audio)  # <-- Connect to slot
        vol_layout.addWidget(mute_btn)
        
        controls_layout.addWidget(volume_group)
        
        # Settings
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        show_settings_btn = QPushButton(" Show Settings")
        show_settings_btn.clicked.connect(self.carplay.show_settings)  # <-- Connect to slot
        settings_layout.addWidget(show_settings_btn)
        
        controls_layout.addWidget(settings_group)
        
        controls_layout.addStretch()
        
        return controls
    
    def _connect_carplay_signals(self):
        """Connect CarPlay signals to UI updates"""
        # Status updates
        self.carplay.dongleStatusChanged.connect(self.on_status_changed)  # <-- Connect signal
        self.carplay.phoneConnected.connect(self.on_phone_connected)      # <-- Connect signal
        self.carplay.phoneDisconnected.connect(self.on_phone_disconnected) # <-- Connect signal
        
        # Media updates
        self.carplay.currentSongChanged.connect(self.on_song_changed)     # <-- Connect signal
        
        # Connection events
        self.carplay.connectionFailed.connect(self.on_connection_failed)  # <-- Connect signal
    
    def on_status_changed(self, status: str):
        """Handle status change signal"""
        self.status_label.setText(f"Status: {status}")
        
        # Update status color
        if "Connected" in status:
            self.status_label.setStyleSheet("padding: 5px; background: #2d5; border-radius: 3px; color: white;")
        elif "Connecting" in status or "Reconnecting" in status:
            self.status_label.setStyleSheet("padding: 5px; background: #fa0; border-radius: 3px; color: black;")
        elif "Failed" in status:
            self.status_label.setStyleSheet("padding: 5px; background: #d33; border-radius: 3px; color: white;")
        else:
            self.status_label.setStyleSheet("padding: 5px; background: #333; border-radius: 3px;")
    
    def on_phone_connected(self):
        """Handle phone connected signal"""
        print("Phone connected!")
        self.setWindowTitle("CarPlay with Controls - Phone Connected")
    
    def on_phone_disconnected(self):
        """Handle phone disconnected signal"""
        print("Phone disconnected")
        self.setWindowTitle("CarPlay with Controls - No Phone")
    
    def on_song_changed(self, song: str):
        """Handle song change signal"""
        if song:
            self.song_label.setText(f"{song}")
        else:
            self.song_label.setText("No song playing")
    
    def on_connection_failed(self):
        """Handle connection failure signal"""
        print("Connection failed!")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
