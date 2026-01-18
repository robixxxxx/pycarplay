#!/usr/bin/env python3
"""
Custom Configuration Example

This example shows how to customize CarPlay settings
and embed the widget in a window.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
import sys

from pycarplay import CarPlayWidget, CarPlayConfig

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create custom configuration
        config = CarPlayConfig()
        
        # Video settings - larger resolution
        config.video.width = 1920
        config.video.height = 1080
        config.video.dpi = 220
        
        # Dongle settings - manual connect
        config.dongle.auto_connect = False
        config.dongle.reconnect_max_attempts = 10
        
        # UI settings
        config.ui.show_touch_indicator = True
        config.ui.show_media_info = True
        
        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create CarPlay widget with custom config
        self.carplay = CarPlayWidget(config=config)
        layout.addWidget(self.carplay)
        
        self.setCentralWidget(central)
        self.setWindowTitle("My Custom CarPlay App")
        self.resize(1920, 1080)
        
        # Manual connect after window is shown
        # (since auto_connect = False)
        print("Window ready. Call carplay.connect() to connect manually")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Manual connect example (optional)
    # window.carplay.connect()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
