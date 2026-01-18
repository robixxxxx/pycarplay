"""
PyCarPlay - CarPlay Integration Module for PyQt6 Applications

This module provides an embeddable widget for integrating CarPlay functionality
into PyQt6 applications.

Example:
    Basic usage - embed in existing window::

        from pycarplay import CarPlayWidget
        from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

        app = QApplication([])
        window = QMainWindow()
        
        # Create central widget
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Add CarPlay widget
        carplay = CarPlayWidget()
        layout.addWidget(carplay)
        
        window.setCentralWidget(central)
        window.show()
        app.exec()
        
    With custom configuration::
    
        config = CarPlayConfig()
        config.video.width = 1920
        config.video.height = 1080
        config.dongle.auto_connect = False
        
        carplay = CarPlayWidget(config=config)
        
    Connect buttons to control::
    
        connect_btn.clicked.connect(carplay.connect)
        disconnect_btn.clicked.connect(carplay.disconnect)
        home_btn.clicked.connect(carplay.send_home)
        
    Listen to signals::
    
        carplay.phoneConnected.connect(on_phone_connected)
        carplay.dongleStatusChanged.connect(on_status_changed)
"""

from .config import CarPlayConfig
from .widget import CarPlayWidget
from .version import __version__

__all__ = [
    'CarPlayWidget',
    'CarPlayConfig',
    '__version__',
]
