"""
PyCarPlay - CarPlay Controller

Main controller connecting CarPlay dongle with QML UI.
Handles video decoding, audio playback, microphone input, and media metadata.
"""
import sys
import time
import threading
from pathlib import Path
from PySide6.QtCore import QUrl, QObject, Slot, Signal, Property, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem

from .core.carplay_node import CarplayNode, CarplayMessage, MessageType
from .core.dongle_driver import DongleConfig, HandDriveType
from .protocol.messages import VideoData, AudioData, Plugged, Unplugged, Opened, DECODE_TYPE_MAP, AudioCommand
from .video.video_decoder import VideoDecoder
from .video.video_provider import VideoFrameProvider
from .audio.audio_player import AudioPlayer
from .core.media_logger import MediaLogger
from .audio.microphone import MicrophoneInput
from .config import CarPlayConfig, DEFAULT_CONFIG
from .logging_utils import get_module_logger, log_received_data


LOGGER = get_module_logger(__name__)


class VideoStreamController(QObject):
    """Main controller for CarPlay video stream and UI
    
    Manages:
    - USB dongle connection
    - Video decoding (H264)
    - Audio playback (PCM)
    - Microphone input (Siri/calls)
    - Media metadata (music, navigation, calls)
    - Touch/keyboard input
    - CarPlay icon and configuration
    """
    
    # === Qt Signals ===
    videoSourceChanged = Signal(str)
    dongleStatusChanged = Signal(str)
    scheduleReconnect = Signal(int)
    dongleConnected = Signal()
    dongleDisconnected = Signal()
    connectionFailed = Signal()  # Thread-safe signal for reconnect
    videoFrameReceived = Signal(int, int, int)  # width, height, data_length
    audioReceived = Signal(int)  # audio data length
    currentSongChanged = Signal(str)
    currentArtistChanged = Signal(str)
    navigationInfoChanged = Signal(str)
    configurableButtonPressed = Signal(str)
    videoConfigChanged = Signal(int, int, int)  # width, height, dpi
    
    def __init__(self, video_provider: VideoFrameProvider, config: CarPlayConfig = None):
        super().__init__()
        
        # Configuration
        self._config = config if config is not None else DEFAULT_CONFIG
        
        # === Core Components ===
        self._video_decoder = VideoDecoder()
        self._video_provider = video_provider
        self._audio_player = AudioPlayer()
        self._media_logger = MediaLogger()
        self._microphone = MicrophoneInput()
        self._carplay_node = None
        
        # === State Variables ===
        self._video_source = ""
        self._dongle_status = "Disconnected"
        self._current_song = ""
        self._current_artist = ""
        self._navigation_info = ""
        self._siri_mode = False  # Mono audio for Siri/calls
        self._video_config = {
            'width': self._config.video.width,
            'height': self._config.video.height,
            'dpi': self._config.video.dpi
        }
        self._carplay_icon_path = self._config.ui.custom_button_icon_path or str(
            Path(__file__).parent / "assets" / "icons" / "logo.png"
        )
        self._carplay_icon_label = self._config.ui.custom_button_label or "PyCarPlay"
        self._carplay_button_action = (self._config.ui.custom_button_action or "home").lower()
        self._reconnect_timer = QTimer()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = self._config.dongle.reconnect_max_attempts
        self._phone_connected = False
        self._pending_settings_reload = False
        self._audio_format_candidate = None
        self._audio_format_candidate_count = 0
        self._audio_format_stability_frames = 3
        self._audio_format_switch_cooldown_s = 0.35
        self._audio_last_switch_ts = 0.0
        self._voice_transition_ts = 0.0
        self._voice_settings_guard_s = 1.5
        self._audio_active_streams = {
            "media": False,
            "navi": False,
            "phonecall": False,
            "siri": False,
            "alert": False,
            "unknown": False,
        }
        self._last_audio_stream = "media"
        self._shutdown_lock = threading.Lock()
        self._shutdown_started = False
        self._shutdown_completed = False
        
        # Load saved config (if exists, otherwise use config values)
        self._load_video_config()
        
        # Setup reconnect timer
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._reconnect_timer.setSingleShot(True)

        # Connect scheduleReconnect signal to slot that uses QTimer in the main thread
        self.scheduleReconnect.connect(self._do_schedule_reconnect)
        
        # Setup connection failure handler (thread-safe)
        self.connectionFailed.connect(self._on_connection_failed)
        self._reconnect_timer.setSingleShot(True)
        
        # === Signal Connections ===
        # Connect decoder to provider (may be adjusted by UI to prefer QML provider)
        self._video_decoder.frameDecoded.connect(self._video_provider.updateFrame)
        # Also log decoded frames for debugging
        try:
            self._video_decoder.frameDecoded.connect(self._log_frame_decoded)
        except Exception:
            pass
        self._video_decoder.tooManyErrors.connect(self._on_decoder_errors)
        self._microphone.micDataReady.connect(self._on_microphone_data)
    
    # === Qt Properties ===
        
    @Property(str, notify=videoSourceChanged)
    def videoSource(self):
        return self._video_source
    
    @videoSource.setter
    def videoSource(self, value):
        if self._video_source != value:
            self._video_source = value
            self.videoSourceChanged.emit(value)
    
    @Slot()
    def startMediaLogging(self):
        """Start logging media data to file"""
        self._media_logger.start()

    @Slot(object)
    def _log_frame_decoded(self, frame):
        """Debug helper: log when frames are decoded"""
        try:
            if hasattr(frame, 'width') and hasattr(frame, 'height'):
                LOGGER.debug("Decoder emitted frame (%dx%d)", frame.width(), frame.height())
            else:
                LOGGER.debug("Decoder emitted a frame")
        except Exception:
            LOGGER.debug("Decoder emitted a frame (logging failed)")
    
    @Slot()
    def stopMediaLogging(self):
        """Stop logging media data"""
        self._media_logger.stop()
    
    @Property(str, notify=dongleStatusChanged)
    def dongleStatus(self):
        return self._dongle_status
    
    @dongleStatus.setter
    def dongleStatus(self, value):
        if self._dongle_status != value:
            self._dongle_status = value
            self.dongleStatusChanged.emit(value)
    
    @Property(str, notify=currentSongChanged)
    def currentSong(self):
        return self._current_song
    
    @currentSong.setter
    def currentSong(self, value):
        if self._current_song != value:
            self._current_song = value
            self.currentSongChanged.emit(value)
    
    @Property(str, notify=currentArtistChanged)
    def currentArtist(self):
        return self._current_artist
    
    @currentArtist.setter
    def currentArtist(self, value):
        if self._current_artist != value:
            self._current_artist = value
            self.currentArtistChanged.emit(value)
    
    @Property(str, notify=navigationInfoChanged)
    def navigationInfo(self):
        return self._navigation_info
    
    @navigationInfo.setter
    def navigationInfo(self, value):
        if self._navigation_info != value:
            self._navigation_info = value
            self.navigationInfoChanged.emit(value)
    
    @Slot()
    def connectDongle(self):
        """Connect to USB dongle"""
        try:
            self.dongleStatus = "Connecting..."
            
            # Create CarPlay config with saved video settings
            config = DongleConfig(
                width=self._video_config['width'],
                height=self._video_config['height'],
                fps=30,
                dpi=self._video_config['dpi'],
                box_name="pyCarPlay",
                hand=HandDriveType.LHD,
                wifi_type="5ghz",
                mic_type="os"
            )
            
            # Create CarPlay node
            self._carplay_node = CarplayNode(config)
            self._carplay_node.onmessage = self._on_carplay_message
            self._carplay_node._microphone_callback = self._on_microphone_command
            
            # Start in separate thread to not block UI
            import threading
            thread = threading.Thread(target=self._carplay_node.start, daemon=True)
            thread.start()
            
            self.dongleStatus = "Initializing..."
            LOGGER.info("CarPlay connection initiated")
            
        except Exception as e:
            self.dongleStatus = f"Error: {str(e)}"
            LOGGER.exception("Failed to connect dongle: %s", e)
            import traceback
            traceback.print_exc()
    
    @Slot()
    def disconnectDongle(self):
        """Disconnect from USB dongle"""
        try:
            if self._reconnect_timer.isActive():
                self._reconnect_timer.stop()

            # Stop audio playback
            if self._audio_player:
                self._audio_player.stop()
                self._audio_format_candidate = None
                self._audio_format_candidate_count = 0
                self._audio_last_switch_ts = 0.0
                for stream in self._audio_active_streams:
                    self._audio_active_streams[stream] = False
                self._last_audio_stream = "media"

            # Stop microphone capture
            if self._microphone:
                self._microphone.stop()
            
            # Reset video decoder
            if self._video_decoder:
                self._video_decoder = VideoDecoder()
                self._video_decoder.frameDecoded.connect(self._video_provider.updateFrame)
                self._video_decoder.tooManyErrors.connect(self._on_decoder_errors)
            
            # Reset video provider
            if self._video_provider:
                self._video_provider.reset()
            
            if self._carplay_node:
                self._carplay_node.stop()
                self._carplay_node = None

            # Stop media logging if active
            if self._media_logger:
                self._media_logger.stop()
            
            self.dongleStatus = "Disconnected"
            self.dongleDisconnected.emit()
            LOGGER.info("Dongle disconnected - video/audio reset")
        except Exception as e:
            LOGGER.exception("Error disconnecting dongle: %s", e)

    @Slot()
    def shutdown(self):
        """Stop background activity and release resources safely.

        This method is idempotent and safe to call multiple times from
        window close events and application quit hooks.
        """
        with self._shutdown_lock:
            if self._shutdown_completed:
                LOGGER.debug("Controller shutdown already completed")
                return
            if self._shutdown_started:
                LOGGER.debug("Controller shutdown already in progress")
                return
            self._shutdown_started = True

        LOGGER.info("Controller shutdown started")
        try:
            if self._reconnect_timer.isActive():
                self._reconnect_timer.stop()

            self.disconnectDongle()
            self._phone_connected = False
            self._pending_settings_reload = False

            LOGGER.info("Controller shutdown finished")
        except Exception as e:
            LOGGER.exception("Controller shutdown failed: %s", e)
        finally:
            with self._shutdown_lock:
                self._shutdown_completed = True
    
    @Slot()
    def toggleAudio(self):
        """Toggle audio playback on/off"""
        if self._audio_player._is_playing:
            self._audio_player.stop()
            LOGGER.info("Audio muted")
        else:
            self._audio_player.start()
            LOGGER.info("Audio unmuted")
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set audio volume (0.0 to 1.0)"""
        if self._audio_player:
            self._audio_player.setVolume(volume)
    
    def _on_decoder_errors(self):
        """Handle too many decoder errors - force reconnection with delay"""
        LOGGER.warning("Decoder errors detected - disconnecting to reset phone")
        
        # Disconnect
        self.disconnectDongle()
        
        # Wait longer before reconnecting - phone needs time to reset CarPlay connection
        LOGGER.info("Waiting 15 seconds for phone to fully reset")
        # Schedule reconnect via main-thread-safe signal
        self.scheduleReconnect.emit(15000)
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to dongle after failure"""
        self._reconnect_attempts += 1
        
        LOGGER.info("Reconnection attempt #%d", self._reconnect_attempts)
        self.dongleStatus = f"Reconnecting... (attempt {self._reconnect_attempts})"
        
        # Disconnect first
        self.disconnectDongle()
        
        # Wait and reconnect
        # Schedule reconnect via main-thread-safe signal
        self.scheduleReconnect.emit(1000)
    
    def _reload_device(self):
        """Reload device connection to apply new settings"""
        LOGGER.info("Reloading device with new settings")
        
        # Store current connection state
        was_connected = self._carplay_node is not None
        
        if was_connected:
            # Disconnect
            self.disconnectDongle()
            
            # Wait and reconnect with new settings
            # Schedule reconnect via main-thread-safe signal
            self.scheduleReconnect.emit(2000)
        else:
            LOGGER.info("Device not connected - settings will apply on next connection")
    
    def _on_carplay_message(self, msg: CarplayMessage):
        """Handle messages from CarPlay node"""
        LOGGER.debug("Received CarplayMessage type=%s", msg.msg_type.name)
        
        if msg.msg_type == MessageType.PLUGGED:
            self._handle_plugged(msg.message)
        elif msg.msg_type == MessageType.UNPLUGGED:
            self._handle_unplugged()
        elif msg.msg_type == MessageType.VIDEO:
            self._handle_video(msg.message)
        elif msg.msg_type == MessageType.AUDIO:
            self._handle_audio(msg.message)
        elif msg.msg_type == MessageType.FAILURE:
            self._handle_failure()
        elif msg.msg_type == MessageType.COMMAND:
            self._handle_command(msg.message)
        elif msg.msg_type == MessageType.MEDIA:
            self._handle_media(msg.message)
        elif msg.msg_type == MessageType.BLUETOOTH_ADDRESS:
            print(f"Bluetooth Address: {msg.message}")
        elif msg.msg_type == MessageType.BLUETOOTH_DEVICE_NAME:
            print(f"Bluetooth Device Name: {msg.message}")
        elif msg.msg_type == MessageType.WIFI_DEVICE_NAME:
            print(f"WiFi Device Name: {msg.message}")
        elif msg.msg_type == MessageType.PHASE:
            if hasattr(msg.message, 'phase'):
                print(f"Connection Phase: {msg.message.phase}")
    
    def _handle_plugged(self, message: Plugged):
        """Handle phone plugged event"""
        phone_type = message.phone_type.name
        print(f"Phone plugged: {phone_type}")
        self._phone_connected = True
        self._reconnect_attempts = 0  # Reset reconnect counter
        self.dongleStatus = f"Connected - {phone_type}"
        self.dongleConnected.emit()
        
        # Apply configurable button appearance/action when phone connects.
        self.setCarPlayIcon(self._carplay_icon_path)
        self.setCarPlayLabel(self._carplay_icon_label)
        self.setCarPlayButtonAction(self._carplay_button_action)
        
        # If settings were changed while disconnected, reload device
        if self._pending_settings_reload:
            print("Settings changed - reloading device...")
            self._pending_settings_reload = False
            QTimer.singleShot(1000, self._reload_device)
    
    def _handle_unplugged(self):
        """Handle phone unplugged event"""
        print("Phone unplugged")
        self._phone_connected = False

        # Fully disconnect current session and reset state so we can search for phone again
        try:
            self.disconnectDongle()
        except Exception as e:
            print(f"Error while disconnecting after unplug: {e}")

        # Update status and reset reconnect counter
        self.dongleStatus = "Disconnected - searching for phone..."
        print("Phone disconnected - restarting search for phone/dongle")
        self._reconnect_attempts = 0

        # Start a reconnect attempt shortly to begin scanning/searching again (main-thread-safe)
        self.scheduleReconnect.emit(1000)

    @Slot(int)
    def _do_schedule_reconnect(self, delay_ms: int):
        """Slot run in controller's thread (main thread) to schedule a QTimer singleShot safely."""
        try:
            QTimer.singleShot(int(delay_ms), self.connectDongle)
        except Exception as e:
            print(f"_do_schedule_reconnect failed: {e}")
    
    def _handle_video(self, message: VideoData):
        """Handle video data"""
        log_received_data(LOGGER, "Controller video ingress", message.data)
        # Decode H264 frame
        self._video_decoder.decode_frame(message.data)
        
        # Emit info signal every 30 frames
        if self._video_provider.frameCount % 30 == 0:
            self.videoFrameReceived.emit(message.width, message.height, len(message.data))
    
    def _handle_audio(self, message: AudioData):
        """Handle audio data and commands"""
        if message.data:
            log_received_data(LOGGER, "Controller audio ingress", message.data)
        if message.data:
            self._handle_audio_data(message)
        elif message.command:
            self._handle_audio_command(message)
        elif message.volume_duration:
            LOGGER.debug("Volume duration: %s", message.volume_duration)
    
    def _handle_audio_data(self, message: AudioData):
        """Handle audio PCM data"""
        try:
            stream_type = self._classify_stream_for_audio_data(message)
            fallback_frequency = self._audio_player.sample_rate or 48000
            fallback_channels = 1 if stream_type in ("siri", "phonecall") else (self._audio_player.channels or 2)
            channels = fallback_channels
            frequency = fallback_frequency

            # Update sample rate if needed
            if message.decode_type in DECODE_TYPE_MAP:
                audio_format = DECODE_TYPE_MAP[message.decode_type]
                frequency = audio_format.frequency
                channels = audio_format.channel
                self._maybe_apply_audio_format(frequency, channels)
            else:
                # Keep playback alive even for unknown codec metadata noise.
                self._maybe_apply_audio_format(fallback_frequency, fallback_channels)
                LOGGER.warning(
                    f" Unknown audio decode_type: {message.decode_type}, "
                    f"using fallback {fallback_frequency}Hz/{fallback_channels}ch"
                )
            
            # Play audio on stream-specific ring buffer.
            self._audio_player.playAudioData(message.data, stream_type=stream_type)
            self.audioReceived.emit(len(message.data))

            if self._audio_player._frames_received <= 5 or self._audio_player._frames_received % 400 == 0:
                LOGGER.info(
                    "Audio route: stream=%s audio_type=%s decode_type=%s active=%s",
                    stream_type,
                    message.audio_type,
                    message.decode_type,
                    sorted([name for name, is_active in self._audio_active_streams.items() if is_active]),
                )
            
            # Log periodically
            if self._audio_player._frames_received <= 5 or self._audio_player._frames_received % 500 == 0:
                LOGGER.debug(
                    "Audio frame #%d: %d samples, %dHz",
                    self._audio_player._frames_received,
                    len(message.data),
                    self._audio_player.sample_rate,
                )
        except Exception as e:
            LOGGER.exception("Audio error: %s", e)

    def _maybe_apply_audio_format(self, frequency: int, channels: int):
        """Apply format changes only after short stability to ignore transient metadata noise."""
        requested = (int(frequency), int(channels))
        current = (int(self._audio_player.sample_rate), int(self._audio_player.channels))

        if requested == current:
            self._audio_format_candidate = None
            self._audio_format_candidate_count = 0
            return

        if self._audio_format_candidate != requested:
            self._audio_format_candidate = requested
            self._audio_format_candidate_count = 1
        else:
            self._audio_format_candidate_count += 1

        required_frames = 1 if not self._audio_player._is_playing else self._audio_format_stability_frames
        if self._audio_format_candidate_count < required_frames:
            return

        now = time.monotonic()
        if self._audio_player._is_playing and (now - self._audio_last_switch_ts) < self._audio_format_switch_cooldown_s:
            return

        self._audio_player.setSampleRate(requested[0], requested[1])
        self._audio_last_switch_ts = now
        self._audio_format_candidate = None
        self._audio_format_candidate_count = 0
        LOGGER.info("Applied audio format %dHz/%dch", requested[0], requested[1])
    
    def _handle_audio_command(self, message: AudioData):
        """Handle audio commands (Siri, config)"""
        command_name = message.command.name if message.command and hasattr(message.command, 'name') else str(message.command)
        LOGGER.info("Audio command: %s", command_name)
        
        # Legacy command; ignore to avoid accidental triggers (e.g. Siri path noise).
        if message.command == AudioCommand.AudioInputConfig:
            LOGGER.info("Ignoring legacy AudioInputConfig command")
            return
        # Toggle Siri mode (mono audio)
        elif message.command == AudioCommand.AudioSiriStart:
            self._siri_mode = True
            self._voice_transition_ts = time.monotonic()
            self._audio_format_candidate = None
            self._audio_format_candidate_count = 0
            self._audio_last_switch_ts = 0.0
            self._set_stream_active("siri", True)
        elif message.command == AudioCommand.AudioSiriStop:
            self._siri_mode = False
            self._voice_transition_ts = time.monotonic()
            self._audio_format_candidate = None
            self._audio_format_candidate_count = 0
            self._audio_last_switch_ts = 0.0
            self._set_stream_active("siri", False)
        elif message.command == AudioCommand.AudioMediaStart:
            self._set_stream_active("media", True)
        elif message.command == AudioCommand.AudioMediaStop:
            self._set_stream_active("media", False)
        elif message.command == AudioCommand.AudioNaviStart:
            self._set_stream_active("navi", True)
        elif message.command == AudioCommand.AudioNaviStop:
            self._set_stream_active("navi", False)
        elif message.command == AudioCommand.AudioPhonecallStart:
            self._voice_transition_ts = time.monotonic()
            self._set_stream_active("phonecall", True)
        elif message.command == AudioCommand.AudioPhonecallStop:
            self._voice_transition_ts = time.monotonic()
            self._set_stream_active("phonecall", False)
        elif message.command == AudioCommand.AudioAlertStart:
            self._set_stream_active("alert", True)
        elif message.command == AudioCommand.AudioAlertStop:
            self._set_stream_active("alert", False)

    def _set_stream_active(self, stream: str, active: bool):
        stream_name = str(stream).lower().strip()
        if stream_name not in self._audio_active_streams:
            stream_name = "unknown"

        self._audio_active_streams[stream_name] = bool(active)
        if active:
            self._last_audio_stream = stream_name

        if self._audio_player:
            self._audio_player.setStreamActive(stream_name, bool(active))

        LOGGER.info(
            "Audio stream active update: %s=%s active=%s",
            stream_name,
            active,
            sorted([name for name, is_active in self._audio_active_streams.items() if is_active]),
        )

    def _classify_stream_for_audio_data(self, message: AudioData) -> str:
        # Prefer explicit metadata when available.
        by_audio_type = {
            1: "media",
            2: "phonecall",
            3: "navi",
            4: "siri",
            5: "alert",
        }
        stream = by_audio_type.get(int(message.audio_type), "unknown")

        # Fall back to currently active stream hints when metadata is ambiguous.
        if stream == "unknown":
            for candidate in ("siri", "phonecall", "navi", "alert", "media"):
                if self._audio_active_streams.get(candidate, False):
                    stream = candidate
                    break

        if stream == "unknown":
            stream = self._last_audio_stream if self._last_audio_stream else "unknown"

        self._last_audio_stream = stream
        return stream
    
    def _handle_failure(self):
        """Handle communication failure - emit signal for thread-safe handling"""
        LOGGER.error("CarPlay communication failed")
        self.dongleStatus = "Failed"
        self.dongleDisconnected.emit()
        
        # Trigger reconnect via signal (thread-safe)
        self.connectionFailed.emit()
    
    def _on_connection_failed(self):
        """Handle connection failure in main Qt thread (called via signal)"""
        delay = 5000  # Exponential backoff, max 30s
        LOGGER.info("Will attempt reconnection #%d in %ss", self._reconnect_attempts + 1, delay / 1000)
        self._reconnect_timer.start(delay)
    
    def _handle_command(self, message):
        """Handle system commands"""
        command_value = message.value

        if command_value == 1:
            LOGGER.info("Ignoring legacy show-config command (1)")
        elif command_value == 2:
            LOGGER.info("Ignoring legacy hide-config command (2)")
        elif command_value == 3:
            LOGGER.info("Configurable button pressed (cmd=3), action=%s", self._carplay_button_action)
            self.configurableButtonPressed.emit(self._carplay_button_action)
        else:
            LOGGER.debug("Unhandled system command value: %s", command_value)
    
    def _handle_media(self, message):
        """Handle media metadata (music, navigation, calls)"""
        if not message.payload:
            return
        
        media_type = message.payload.get('type')
        
        if media_type == 3:  # Album Cover
            LOGGER.debug("Album Cover received")
        elif media_type == 1:  # Media Data
            media = message.payload.get('media', {})
            self._handle_music_metadata(media)
            self._handle_navigation_metadata(media)
            self._handle_phone_metadata(media)
    
    def _handle_music_metadata(self, media: dict):
        """Handle music/media metadata"""
        # Song change
        if 'MediaSongTitle' in media:
            song = media.get('MediaSongTitle', 'Unknown')
            artist = media.get('MediaArtist', 'Unknown')
            album = media.get('MediaAlbum', 'Unknown')
            LOGGER.info("Now Playing: %s - %s (Album: %s)", song, artist, album)
            
            self.currentSong = song
            self.currentArtist = f"{artist} • {album}"
            
            play_time_ms = media.get('MediaSongPlayTime', 0)
            duration_ms = media.get('MediaSongDuration', 0)
            self._media_logger.log_music(song, artist, album, play_time_ms, duration_ms)
        
        # Playback position update (log periodically)
        elif 'MediaSongPlayTime' in media:
            play_time_sec = media.get('MediaSongPlayTime', 0) / 1000
            duration_sec = media.get('MediaSongDuration', 0) / 1000
            if int(play_time_sec) % 10 == 0:
                LOGGER.debug("Playback: %.1fs / %.1fs", play_time_sec, duration_sec)
    
    def _handle_navigation_metadata(self, media: dict):
        """Handle navigation metadata"""
        if not any(k in media for k in ['NaviCurrentRoad', 'NaviDistance', 'NaviManeuver']):
            return
        
        current_road = media.get('NaviCurrentRoad', '')
        next_road = media.get('NaviNextRoad', '')
        distance = media.get('NaviDistance', 0)
        distance_unit = media.get('NaviDistanceUnit', '')
        maneuver = media.get('NaviManeuver', '')
        eta = media.get('NaviETA', '')
        
        # Build UI text
        nav_parts = []
        if maneuver:
            nav_parts.append(maneuver)
        if distance:
            nav_parts.append(f"{distance} {distance_unit}")
        if current_road:
            nav_parts.append(current_road)
        self.navigationInfo = " • ".join(nav_parts)
        
        # Log details
        if current_road:
            LOGGER.info("Current road: %s", current_road)
        if next_road:
            LOGGER.info("Next road: %s", next_road)
        if distance:
            LOGGER.info("Distance: %s %s", distance, distance_unit)
        if maneuver:
            LOGGER.info("Maneuver: %s", maneuver)
        if eta:
            LOGGER.info("ETA: %s", eta)
        
        self._media_logger.log_navigation(current_road, next_road, distance, distance_unit, maneuver, eta)
    
    def _handle_phone_metadata(self, media: dict):
        """Handle phone call metadata"""
        if 'PhoneCallStatus' in media:
            call_status = media.get('PhoneCallStatus', '')
            caller = media.get('PhoneCaller', 'Unknown')
            LOGGER.info("Call: %s - %s", call_status, caller)
            self._media_logger.log_phone_call(call_status, caller)
    
    def _on_microphone_data(self, audio_data):
        """Handle microphone data and send to CarPlay"""
        if not self._carplay_node:
            return
        
        try:
            # Convert audio tuple to bytes
            import struct
            audio_bytes = struct.pack(f'{len(audio_data)}h', *audio_data)
            log_received_data(LOGGER, "Microphone callback ingress", audio_bytes)
            self._carplay_node.send_audio(audio_bytes)
            
            # Log periodically
            if not hasattr(self, '_mic_data_count'):
                self._mic_data_count = 0
            self._mic_data_count += 1
            if self._mic_data_count <= 5 or self._mic_data_count % 100 == 0:
                LOGGER.debug("Microphone data sent #%d: %d bytes", self._mic_data_count, len(audio_bytes))
        except Exception as e:
            LOGGER.exception("Microphone error: %s", e)
    
    def _on_microphone_command(self, action: str, command):
        """Handle microphone start/stop commands from CarPlay"""
        LOGGER.info("Microphone command: %s (%s)", action, command.name)
        if action == 'start':
            self.startMicrophone()
        elif action == 'stop':
            self.stopMicrophone()
    
    # === Configuration Management ===
    
    def _load_video_config(self):
        """Load video configuration from file"""
        import json
        import os
        
        config_file = os.path.join(os.path.dirname(__file__), 'video_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self._video_config = json.load(f)
                print(f"  Loaded video config: {self._video_config['width']}x{self._video_config['height']} @ {self._video_config['dpi']} DPI")
            except Exception as e:
                print(f"  Failed to load video config: {e}")
    
    def _save_video_config(self):
        """Save video configuration to file"""
        import json
        import os
        
        config_file = os.path.join(os.path.dirname(__file__), 'video_config.json')
        try:
            with open(config_file, 'w') as f:
                json.dump(self._video_config, f, indent=2)
            print(f" Saved video config: {self._video_config['width']}x{self._video_config['height']} @ {self._video_config['dpi']} DPI")
        except Exception as e:
            print(f"  Failed to save video config: {e}")
    
    @Slot()
    def startMicrophone(self):
        """Start microphone recording (for Siri/calls)"""
        self._microphone.start()
        print(" Microphone started")
    
    @Slot()
    def stopMicrophone(self):
        """Stop microphone recording"""
        self._microphone.stop()
        print(" Microphone stopped")
    
    # === Public API ===
    
    @Slot(result=int)
    def getVideoWidth(self):
        """Get current video width"""
        return self._video_config['width']
    
    @Slot(result=int)
    def getVideoHeight(self):
        """Get current video height"""
        return self._video_config['height']
    
    @Slot(result=int)
    def getVideoDpi(self):
        """Get current video DPI"""
        return self._video_config['dpi']

    @Slot(result=str)
    def getWaitingConnectionText(self):
        """Get configurable waiting text shown while not connected."""
        return self._config.ui.waiting_connection_text

    @Slot(result=str)
    def getCarPlayIconPath(self):
        """Get current configurable button icon path."""
        return self._carplay_icon_path

    @Slot(result=str)
    def getCarPlayLabel(self):
        """Get current configurable button label."""
        return self._carplay_icon_label

    @Slot(result=str)
    def getCarPlayButtonAction(self):
        """Get current configurable button action (home/siri)."""
        return self._carplay_button_action
    
    def apply_video_config(self, width: int, height: int, dpi: int):
        """
        Apply video configuration programmatically
        
        This method is called by CarPlayWidget to apply config values.
        It's separate from setVideoSettings which is called from QML.
        """
        self._video_config['width'] = width
        self._video_config['height'] = height
        self._video_config['dpi'] = dpi
        self.videoConfigChanged.emit(width, height, dpi)
        print(f"  Applied video config: {width}x{height} @ {dpi} DPI")
    
    @Slot(int, int, int)
    def setVideoSettings(self, width: int, height: int, dpi: int):
        """Set video resolution and DPI
        
        Args:
            width: Video width in pixels
            height: Video height in pixels
            dpi: DPI value
        """
        # Save config
        self._video_config = {
            'width': width,
            'height': height,
            'dpi': dpi
        }
        self._save_video_config()
        
        # Emit signal to update UI window size and touch scaling
        self.videoConfigChanged.emit(width, height, dpi)
        
        if self._carplay_node:
            # Update dongle settings
            self._carplay_node.dongle_driver.update_video_settings(width, height, dpi)
            print(f"  Video settings updated: {width}x{height} @ {dpi} DPI")
            
            # Auto-reload device to apply settings
            if self._phone_connected:
                print(f" Phone connected - reloading device to apply settings...")
                QTimer.singleShot(500, self._reload_device)
            else:
                print(f"  No phone connected - settings will apply on next connection")
                self._pending_settings_reload = True
        else:
            print(f"  Video settings saved: {width}x{height} @ {dpi} DPI")
            print(f"  Connect dongle first to send settings")
    
    @Slot(str)
    def setCarPlayLabel(self, label: str):
        """Set CarPlay icon label"""
        self._carplay_icon_label = (label or "").strip() or "PyCarPlay"
        self._config.ui.custom_button_label = self._carplay_icon_label
        if self._carplay_node:
            from .protocol.sendable import SendIconConfig
            self._carplay_node.dongle_driver.send(SendIconConfig({'label': self._carplay_icon_label}))
            print(f"  CarPlay label set to: {self._carplay_icon_label}")
    
    @Slot(str)
    def setCarPlayIcon(self, icon_path: str):
        """Set CarPlay icon from PNG file
        
        Automatically uses pre-sized icons if available:
        - logo_120_120.png for 120x120
        - logo_180_180.png for 180x180
        - logo_256_256.png for 256x256
        """
        if icon_path:
            self._carplay_icon_path = icon_path
            self._config.ui.custom_button_icon_path = icon_path

        if not self._carplay_node:
            print(" CarPlay not connected")
            return
        
        try:
            from .protocol.sendable import SendFile, FileAddress, SendIconConfig, SendCommand
            import os
            import time
            
            # Determine base path for pre-sized icons
            base_dir = os.path.dirname(icon_path)
            base_name = os.path.splitext(os.path.basename(icon_path))[0]
            
            # Load pre-sized icons (or fall back to original)
            icon_120 = os.path.join(base_dir, f"{base_name}_120_120.png")
            icon_180 = os.path.join(base_dir, f"{base_name}_180_180.png")
            icon_256 = os.path.join(base_dir, f"{base_name}_256_256.png")
            
            # Read icon data
            def read_icon(path, fallback_data=None):
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        data = f.read()
                    print(f" Loaded {os.path.basename(path)}: {len(data)} bytes")
                    return data
                return fallback_data
            
            icon_data_120 = read_icon(icon_120, read_icon(icon_path))
            icon_data_180 = read_icon(icon_180, icon_data_120)
            icon_data_256 = read_icon(icon_256, icon_data_120)
            
            # Send all icon sizes to dongle
            print(" Uploading icons to dongle...")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.OEM_ICON))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_120, FileAddress.ICON_120))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_180, FileAddress.ICON_180))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.ICON_250))
            
            time.sleep(0.3)  # Wait for files to be written
            
            # Send configuration with currently configured label
            self._carplay_node.dongle_driver.send(SendIconConfig({'label': self._carplay_icon_label}))
            time.sleep(0.2)
            
            # Request UI refresh
            self._carplay_node.dongle_driver.send(SendCommand('requestHostUI'))
            
            print(" CarPlay icon and label updated")
            print("  Note: May require iPhone reconnection to see changes")
            
        except Exception as e:
            print(f" Error setting icon: {e}")
            import traceback
            traceback.print_exc()

    @Slot(str)
    def setCarPlayButtonAction(self, action: str):
        """Set configurable button action: 'home' or 'siri'."""
        normalized = (action or "home").strip().lower()
        self._carplay_button_action = normalized
        self._config.ui.custom_button_action = normalized

        if normalized not in {"home", "siri"}:
            print(
                f"  Stored custom button action key: {normalized} "
                "(dongle supports only 'home'/'siri')"
            )
            return

        if not self._carplay_node:
            return

        try:
            from .protocol.sendable import SendLogoType, LogoType
            logo_type = LogoType.HomeButton if normalized == "home" else LogoType.Siri
            self._carplay_node.dongle_driver.send(SendLogoType(logo_type))
            print(f"  CarPlay configurable button action set to: {normalized}")
        except Exception as e:
            print(f" Error setting configurable button action: {e}")
    
    @Slot(str)
    def sendKey(self, action: str):
        """Send key command to CarPlay
        
        Args:
            action: Command name (home, back, play, pause, etc.)
        """
        if self._carplay_node:
            self._carplay_node.send_key(action)
            print(f"  Key: {action}")
    
    @Slot(float, float, int)
    def sendTouch(self, x: float, y: float, action: int):
        """Send touch event to CarPlay
        
        Args:
            x: X coordinate in video space (based on current resolution)
            y: Y coordinate in video space (based on current resolution)
            action: TouchAction value (14=Down, 15=Move, 16=Up)
        """
        if not self._carplay_node:
            return
        
        from .protocol.sendable import TouchAction
        
        # Get current resolution from config
        width = self._video_config['width']
        height = self._video_config['height']
        
        # Accept either pixel coordinates or normalized 0.0-1.0 coordinates.
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            # Already normalized
            norm_x = x
            norm_y = y
        else:
            # Normalize pixel coordinates to 0.0-1.0
            norm_x = max(0.0, min(1.0, x / width))
            norm_y = max(0.0, min(1.0, y / height))
        
        action_names = {14: "DOWN", 15: "MOVE", 16: "UP"}
        action_name = action_names.get(action, f"UNKNOWN({action})")
        
        self._carplay_node.send_touch(norm_x, norm_y, TouchAction(action))
        print(f"  Touch {action_name}: ({x}, {y}) -> ({norm_x:.3f}, {norm_y:.3f}) [{width}x{height}]")

    @Slot(float, float, str)
    def handleTouchNormalized(self, nx: float, ny: float, action: str):
        """Handle normalized touch coordinates from QML (0.0 - 1.0)."""
        try:
            action_map = {'down': 14, 'move': 15, 'up': 16}
            code = action_map.get(str(action).lower(), 15)
            # Call sendTouch which accepts normalized values
            self.sendTouch(float(nx), float(ny), code)
        except Exception as e:
            print(f"handleTouchNormalized error: {e}")

    @Slot(float, float, str)
    def handleTouch(self, screen_x: float, screen_y: float, action: str):
        """Handle touch calls from QML: map screen coords to video coords and send touch."""
        try:
            # Ask provider to map to video coordinates
            coords = None
            if self._video_provider is None:
                print("handleTouch: no video provider available")
                return

            try:
                coords = self._video_provider.mapToVideoCoordinates(float(screen_x), float(screen_y))
            except Exception:
                # Some providers (QML objects) may return QVariantList via method call differently
                try:
                    coords = self._video_provider.mapToVideoCoordinates(screen_x, screen_y)
                except Exception as e:
                    print(f"handleTouch: failed to map coords: {e}")
                    return

            if not coords or len(coords) < 2:
                return

            vx, vy = int(coords[0]), int(coords[1])

            # Map action string to TouchAction codes
            action_map = {'down': 14, 'move': 15, 'up': 16}
            action_code = action_map.get(str(action).lower(), 15)

            # Send touch to CarPlay
            self.sendTouch(vx, vy, action_code)
        except Exception as e:
            print(f"handleTouch error: {e}")


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
    qml_file = Path(__file__).parent / "src" / "ui" / "main.qml"
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
    
    # Auto-connect to dongle on startup
    print(" Auto-connecting to dongle...")
    QTimer.singleShot(500, video_controller.connectDongle)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
