"""
CarPlay Configuration

This module provides a flexible configuration system for PyCarPlay.
Users can override default settings by creating their own config object.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class VideoConfig:
    """Video display configuration"""
    width: int = 1280
    height: int = 720
    dpi: int = 160
    fps: int = 60
    
    
@dataclass
class AudioConfig:
    """Audio playback configuration"""
    sample_rate: int = 48000
    channels: int = 2
    chunk_size: int = 4096
    

@dataclass
class DongleConfig:
    """USB Dongle configuration"""
    vendor_id: int = 0x1314
    product_id: int = 0x1520
    auto_connect: bool = True
    reconnect_delay: int = 5000  # milliseconds
    reconnect_max_attempts: int = 5
    decoder_error_delay: int = 15000  # milliseconds
    

@dataclass
class UIConfig:
    """UI customization configuration"""
    custom_qml_path: Optional[str] = None
    window_title: str = "PyCarPlay - Video Stream"
    background_color: str = "#1e1e1e"
    show_touch_indicator: bool = True
    show_media_info: bool = True
    show_navigation_info: bool = True
    

@dataclass
class CarPlayConfig:
    """
    Complete CarPlay configuration
    
    This class holds all configuration options for PyCarPlay.
    Users can create their own instance and override specific values.
    
    Example:
        >>> config = CarPlayConfig()
        >>> config.video.width = 1920
        >>> config.video.height = 1080
        >>> config.dongle.auto_connect = False
        
        Or use from_dict:
        >>> config = CarPlayConfig.from_dict({
        ...     'video': {'width': 1920, 'height': 1080},
        ...     'audio': {'sample_rate': 44100}
        ... })
    """
    video: VideoConfig = field(default_factory=VideoConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    dongle: DongleConfig = field(default_factory=DongleConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CarPlayConfig':
        """
        Create configuration from dictionary
        
        Args:
            config_dict: Dictionary with configuration values
            
        Returns:
            CarPlayConfig instance with values from dictionary
        """
        video_config = VideoConfig(**config_dict.get('video', {}))
        audio_config = AudioConfig(**config_dict.get('audio', {}))
        dongle_config = DongleConfig(**config_dict.get('dongle', {}))
        ui_config = UIConfig(**config_dict.get('ui', {}))
        
        return cls(
            video=video_config,
            audio=audio_config,
            dongle=dongle_config,
            ui=ui_config
        )
    
    @classmethod
    def from_json_file(cls, filepath: str) -> 'CarPlayConfig':
        """
        Load configuration from JSON file
        
        Args:
            filepath: Path to JSON configuration file
            
        Returns:
            CarPlayConfig instance with values from file
        """
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'video': {
                'width': self.video.width,
                'height': self.video.height,
                'dpi': self.video.dpi,
                'fps': self.video.fps,
            },
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'chunk_size': self.audio.chunk_size,
            },
            'dongle': {
                'vendor_id': self.dongle.vendor_id,
                'product_id': self.dongle.product_id,
                'auto_connect': self.dongle.auto_connect,
                'reconnect_delay': self.dongle.reconnect_delay,
                'reconnect_max_attempts': self.dongle.reconnect_max_attempts,
                'decoder_error_delay': self.dongle.decoder_error_delay,
            },
            'ui': {
                'custom_qml_path': self.ui.custom_qml_path,
                'window_title': self.ui.window_title,
                'background_color': self.ui.background_color,
                'show_touch_indicator': self.ui.show_touch_indicator,
                'show_media_info': self.ui.show_media_info,
                'show_navigation_info': self.ui.show_navigation_info,
            }
        }
    
    def to_json_file(self, filepath: str) -> None:
        """
        Save configuration to JSON file
        
        Args:
            filepath: Path where to save JSON configuration
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)


# Default configuration instance
DEFAULT_CONFIG = CarPlayConfig()
