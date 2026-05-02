#!/usr/bin/env python3
"""
Audio Configuration for PyCarPlay
Adjust these settings to fix audio stuttering/lag
"""

from ..logging_utils import get_module_logger


LOGGER = get_module_logger(__name__)

class AudioConfig:
    """Audio playback configuration"""
    
    # Sample rate (Hz) - CarPlay standard is 48000
    SAMPLE_RATE = 48000
    
    # Number of channels - 2 for stereo
    CHANNELS = 2
    
    # Buffer size in milliseconds
    # Increase this value if audio stutters (100-500ms recommended)
    # Lower values = less latency but more likely to stutter
    # Higher values = more latency but smoother playback
    BUFFER_SIZE_MS = 200
    
    # Minimum number of audio frames to buffer before starting playback
    # Increase this if you hear stuttering at the start (3-10 recommended)
    # Each frame is typically ~120ms of audio
    MIN_BUFFER_FRAMES = 3
    
    # Maximum buffer size (frames) - prevents excessive memory usage
    # If buffer grows beyond this, old frames will be dropped
    MAX_BUFFER_FRAMES = 20
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        buffer_time = cls.BUFFER_SIZE_MS / 1000.0
        min_buffer_time = cls.MIN_BUFFER_FRAMES * 0.12  # ~120ms per frame
        
        LOGGER.info("=" * 60)
        LOGGER.info("Audio Configuration:")
        LOGGER.info("Sample Rate: %s Hz", cls.SAMPLE_RATE)
        LOGGER.info("Channels: %s", cls.CHANNELS)
        LOGGER.info("Buffer Size: %sms (%.2fs)", cls.BUFFER_SIZE_MS, buffer_time)
        LOGGER.info("Min Buffer: %s frames (~%.2fs)", cls.MIN_BUFFER_FRAMES, min_buffer_time)
        LOGGER.info("Max Buffer: %s frames", cls.MAX_BUFFER_FRAMES)
        LOGGER.info("=" * 60)
        LOGGER.info("To reduce stuttering, try increasing:")
        LOGGER.info("- BUFFER_SIZE_MS (currently %s)", cls.BUFFER_SIZE_MS)
        LOGGER.info("- MIN_BUFFER_FRAMES (currently %s)", cls.MIN_BUFFER_FRAMES)
        LOGGER.info("Note: Higher values = smoother but more audio delay")
        LOGGER.info("=" * 60)
