#!/usr/bin/env python3
"""
PyCarPlay example configuration.

This file contains all available configuration options with descriptions.
Modify values here and the changes will be applied automatically
to all examples.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pycarplay import CarPlayConfig

# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------

config = CarPlayConfig()

# -- VIDEO -------------------------------------------------------------------
# CarPlay render resolution.
# These values tell iPhone/Android what display resolution is used.
# Changing them typically requires reconnecting the phone.
config.video.width  = 1280   # width in pixels | typical: 800, 1024, 1280, 1920
config.video.height = 720    # height in pixels | typical: 480, 600, 720, 1080
config.video.dpi    = 160    # display density (DPI) | typical: 72, 96, 120, 160, 220, 320
config.video.fps    = 60     # target frames per second | typical: 30, 60

# -- AUDIO -------------------------------------------------------------------
# Audio stream parameters received from the phone.
config.audio.sample_rate = 44100  # sample rate in Hz | 44100, 48000
config.audio.channels    = 2      # channels: 1 = mono, 2 = stereo
config.audio.chunk_size  = 2048   # audio buffer size in bytes | 1024, 2048, 4096, 8192

# -- DONGLE ------------------------------------------------------------------
# USB dongle hardware settings.
config.dongle.vendor_id               = 0x1314  # USB Vendor ID; usually should not be changed
config.dongle.product_id              = 0x1520  # USB Product ID; usually should not be changed
config.dongle.auto_connect            = True    # True = auto-connect on startup
                                                # False = manual call to carplay.connect() is required
config.dongle.reconnect_delay         = 5000    # delay before reconnect attempt [ms]
config.dongle.reconnect_max_attempts  = 5       # max reconnect attempts
                                                # 0 = unlimited
config.dongle.decoder_error_delay     = 20000   # restart delay after decoder error [ms]

# -- UI ----------------------------------------------------------------------
# UI appearance and behavior.
config.ui.custom_qml_path    = None             # path to custom .qml file
                                                # None = use default UI
                                                # example: "/home/user/my_ui/Main.qml"
config.ui.window_title       = "PyCarPlay"      # application window title
config.ui.background_color   = "#1e1e1e"        # background color when no video is shown, e.g. "#000000"
config.ui.show_touch_indicator  = True          # True = show touch circle indicator
config.ui.show_media_info       = True          # True = show current song/artist info
config.ui.show_navigation_info  = True          # True = show navigation instruction info
config.ui.waiting_connection_text = "Waiting for phone connection..."  # text shown while waiting for connection
config.ui.custom_button_action    = "log_button_press"  # action key mapped in CUSTOM_BUTTON_ACTIONS

# -- LOGGING -----------------------------------------------------------------
# Logging controls
config.logging.enabled = False  # True = write per-module log files to logs/modules
config.logging.console_enabled = False  # True = print logs to console; False = no console logs
# Empty list means all modules. You can filter by full module name or prefix.
# Example: ["pycarplay.controller", "pycarplay.audio, pycarplay.__init__, pycarplay.audio.__init__, 
# pycarplay.audio.adaptive_driver, pycarplay.audio.audio_player, pycarplay.audio.microphone,
# pycarplay.config, pycarplay.controller, pycarplay.core.__init__, pycarplay.core.carplay_node
# pycarplay.core.dongle_driver, pycarplay.core.media_logger, pycarplay.logging_utils
# pycarplay.protocol.__init__, pycarplay.protocol.messages, pycarplay.protocol.sendable
# pycarplay.ui.__init__, pycarplay.version, pycarplay.video.__init__, pycarplay.video.video_decoder
# pycarplay.video.video_provider, pycarplay.widget"]
config.logging.enabled_modules = []
