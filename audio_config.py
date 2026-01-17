#!/usr/bin/env python3
"""
Audio Configuration for PyCarPlay
Adjust these settings to fix audio stuttering/lag
"""

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
        
        print("=" * 60)
        print("Audio Configuration:")
        print(f"  Sample Rate: {cls.SAMPLE_RATE} Hz")
        print(f"  Channels: {cls.CHANNELS}")
        print(f"  Buffer Size: {cls.BUFFER_SIZE_MS}ms ({buffer_time:.2f}s)")
        print(f"  Min Buffer: {cls.MIN_BUFFER_FRAMES} frames (~{min_buffer_time:.2f}s)")
        print(f"  Max Buffer: {cls.MAX_BUFFER_FRAMES} frames")
        print("=" * 60)
        print()
        print("To reduce stuttering, try increasing:")
        print("  - BUFFER_SIZE_MS (currently {})".format(cls.BUFFER_SIZE_MS))
        print("  - MIN_BUFFER_FRAMES (currently {})".format(cls.MIN_BUFFER_FRAMES))
        print()
        print("Note: Higher values = smoother but more audio delay")
        print("=" * 60)
