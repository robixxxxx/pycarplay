#!/usr/bin/env python3
"""
PyCarPlay - CarPlay/AndroidAuto Video Stream Application

Main application controller connecting CarPlay dongle with QML UI.
Handles video decoding, audio playback, microphone input, and media metadata.
"""
import sys
from pathlib import Path
from PySide6.QtCore import QUrl, QObject, Slot, Signal, Property, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from src.core.carplay_node import CarplayNode, CarplayMessage, MessageType
from src.core.dongle_driver import DongleConfig, HandDriveType
from src.protocol.messages import VideoData, AudioData, Plugged, Unplugged, Opened, DECODE_TYPE_MAP
from src.video.video_decoder import VideoDecoder
from src.video.video_provider import VideoFrameProvider
from src.audio.audio_player import AudioPlayer
from src.core.media_logger import MediaLogger
from src.audio.microphone import MicrophoneInput


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
    dongleConnected = Signal()
    dongleDisconnected = Signal()
    connectionFailed = Signal()  # Thread-safe signal for reconnect
    videoFrameReceived = Signal(int, int, int)  # width, height, data_length
    audioReceived = Signal(int)  # audio data length
    currentSongChanged = Signal(str)
    currentArtistChanged = Signal(str)
    navigationInfoChanged = Signal(str)
    showConfigPanel = Signal()
    hideConfigPanel = Signal()
    videoConfigChanged = Signal(int, int, int)  # width, height, dpi
    
    def __init__(self, video_provider: VideoFrameProvider):
        super().__init__()
        
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
            'width': 1280,
            'height': 720,
            'dpi': 160
        }
        self._reconnect_timer = QTimer()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._phone_connected = False
        self._pending_settings_reload = False
        
        # Load saved config
        self._load_video_config()
        
        # Setup reconnect timer
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._reconnect_timer.setSingleShot(True)
        
        # Setup connection failure handler (thread-safe)
        self.connectionFailed.connect(self._on_connection_failed)
        self._reconnect_timer.setSingleShot(True)
        
        # === Signal Connections ===
        self._video_decoder.frameDecoded.connect(self._video_provider.updateFrame)
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
            # Stop audio playback
            if self._audio_player:
                self._audio_player.stop()
            
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
            
            self.dongleStatus = "Disconnected"
            self.dongleDisconnected.emit()
            print("Dongle disconnected - video/audio reset")
        except Exception as e:
            print(f"Error disconnecting dongle: {e}")
    
    @Slot()
    def toggleAudio(self):
        """Toggle audio playback on/off"""
        if self._audio_player._is_playing:
            self._audio_player.stop()
            print("🔇 Audio muted")
        else:
            self._audio_player.start()
            print("🔊 Audio unmuted")
    
    @Slot(float)
    def setVolume(self, volume: float):
        """Set audio volume (0.0 to 1.0)"""
        if self._audio_player:
            self._audio_player.setVolume(volume)
    
    def _on_decoder_errors(self):
        """Handle too many decoder errors - force reconnection with delay"""
        print("🔄 Decoder errors detected - disconnecting to reset phone...")
        
        # Disconnect
        self.disconnectDongle()
        
        # Wait longer before reconnecting - phone needs time to reset CarPlay connection
        print("⏳ Waiting 15 seconds for phone to fully reset...")
        QTimer.singleShot(15000, self.connectDongle)  # Reconnect after 15 seconds
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to dongle after failure"""
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts > self._max_reconnect_attempts:
            print(f"❌ Max reconnection attempts ({self._max_reconnect_attempts}) reached. Please reconnect manually.")
            self.dongleStatus = "Failed - Manual reconnection needed"
            return
        
        print(f"🔄 Reconnection attempt #{self._reconnect_attempts}/{self._max_reconnect_attempts}...")
        self.dongleStatus = f"Reconnecting... (attempt {self._reconnect_attempts})"
        
        # Disconnect first
        self.disconnectDongle()
        
        # Wait and reconnect
        QTimer.singleShot(1000, self.connectDongle)
    
    def _reload_device(self):
        """Reload device connection to apply new settings"""
        print("🔄 Reloading device with new settings...")
        
        # Store current connection state
        was_connected = self._carplay_node is not None
        
        if was_connected:
            # Disconnect
            self.disconnectDongle()
            
            # Wait and reconnect with new settings
            QTimer.singleShot(2000, self.connectDongle)
        else:
            print("⚠️  Device not connected - settings will apply on next connection")
    
    def _on_carplay_message(self, msg: CarplayMessage):
        """Handle messages from CarPlay node"""
        
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
            print(f"📱 Bluetooth Address: {msg.message}")
        elif msg.msg_type == MessageType.BLUETOOTH_DEVICE_NAME:
            print(f"📱 Bluetooth Device Name: {msg.message}")
        elif msg.msg_type == MessageType.WIFI_DEVICE_NAME:
            print(f"📶 WiFi Device Name: {msg.message}")
        elif msg.msg_type == MessageType.PHASE:
            if hasattr(msg.message, 'phase'):
                print(f"🔄 Connection Phase: {msg.message.phase}")
    
    def _handle_plugged(self, message: Plugged):
        """Handle phone plugged event"""
        phone_type = message.phone_type.name
        print(f"📱 Phone plugged: {phone_type}")
        self._phone_connected = True
        self._reconnect_attempts = 0  # Reset reconnect counter
        self.dongleStatus = f"Connected - {phone_type}"
        self.dongleConnected.emit()
        
        # Send CarPlay icon and label
        icon_path = Path(__file__).parent / "assets" / "icons" / "logo.png"
        self.setCarPlayIcon(str(icon_path))
        
        # If settings were changed while disconnected, reload device
        if self._pending_settings_reload:
            print("🔄 Settings changed - reloading device...")
            self._pending_settings_reload = False
            QTimer.singleShot(1000, self._reload_device)
    
    def _handle_unplugged(self):
        """Handle phone unplugged event"""
        print("📱 Phone unplugged")
        self._phone_connected = False
        self.dongleStatus = "Connected - No phone"
        
        # Start reconnection attempts
        print("🔄 Phone disconnected - will monitor for reconnection")
        self._reconnect_attempts = 0
    
    def _handle_video(self, message: VideoData):
        """Handle video data"""
        # Decode H264 frame
        self._video_decoder.decode_frame(message.data)
        
        # Emit info signal every 30 frames
        if self._video_provider.frameCount % 30 == 0:
            self.videoFrameReceived.emit(message.width, message.height, len(message.data))
    
    def _handle_audio(self, message: AudioData):
        """Handle audio data and commands"""
        if message.data:
            self._handle_audio_data(message)
        elif message.command:
            self._handle_audio_command(message)
        elif message.volume_duration:
            print(f"🔊 Volume duration: {message.volume_duration}")
    
    def _handle_audio_data(self, message: AudioData):
        """Handle audio PCM data"""
        try:
            # Update sample rate if needed
            if message.decode_type in DECODE_TYPE_MAP:
                audio_format = DECODE_TYPE_MAP[message.decode_type]
                channels = 1 if self._siri_mode else 2
                self._audio_player.setSampleRate(audio_format.frequency, channels)
            
            # Play audio
            self._audio_player.playAudioData(message.data)
            self.audioReceived.emit(len(message.data))
            
            # Log periodically
            if self._audio_player._frames_received <= 5 or self._audio_player._frames_received % 500 == 0:
                print(f"🔊 Audio frame #{self._audio_player._frames_received}: "
                      f"{len(message.data)} samples, {audio_format.frequency}Hz")
        except Exception as e:
            print(f"❌ Audio error: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_audio_command(self, message: AudioData):
        """Handle audio commands (Siri, config)"""
        from src.protocol.messages import AudioCommand
        command_name = message.command.name if hasattr(message.command, 'name') else str(message.command)
        print(f"🔊 Audio command: {command_name}")
        
        # Show config panel on AudioInputConfig
        if message.command == AudioCommand.AudioInputConfig:
            print("⚙️  AudioInputConfig - showing config panel")
            self.showConfigPanel.emit()
        # Toggle Siri mode (mono audio)
        elif message.command == AudioCommand.AudioSiriStart:
            self._siri_mode = True
        elif message.command == AudioCommand.AudioSiriStop:
            self._siri_mode = False
    
    def _handle_failure(self):
        """Handle communication failure - emit signal for thread-safe handling"""
        print("❌ CarPlay communication failed")
        self.dongleStatus = "Failed"
        self.dongleDisconnected.emit()
        
        # Trigger reconnect via signal (thread-safe)
        self.connectionFailed.emit()
    
    def _on_connection_failed(self):
        """Handle connection failure in main Qt thread (called via signal)"""
        if self._reconnect_attempts < self._max_reconnect_attempts:
            delay = min(5000 * (2 ** self._reconnect_attempts), 30000)  # Exponential backoff, max 30s
            print(f"🔄 Will attempt reconnection #{self._reconnect_attempts + 1} in {delay/1000}s...")
            self._reconnect_timer.start(delay)
        else:
            print(f"❌ Max reconnection attempts ({self._max_reconnect_attempts}) reached")
    
    def _handle_command(self, message):
        """Handle system commands"""
        command_value = message.value
        
        # Only log commands we actually handle
        if command_value == 3:
            print("⚙️  AudioInputConfig - showing config panel")
            self.showConfigPanel.emit()
        elif command_value == 1:
            print("⚙️  Showing CarPlay config panel")
            self.showConfigPanel.emit()
        elif command_value == 2:
            print("⚙️  Hiding CarPlay config panel")
            self.hideConfigPanel.emit()
    
    def _handle_media(self, message):
        """Handle media metadata (music, navigation, calls)"""
        if not message.payload:
            return
        
        media_type = message.payload.get('type')
        
        if media_type == 3:  # Album Cover
            print(f"🎨 Album Cover received")
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
            print(f"🎵 Now Playing: {song} - {artist} (Album: {album})")
            
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
                print(f"⏱️  Playback: {play_time_sec:.1f}s / {duration_sec:.1f}s")
    
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
            print(f"🗺️  Current: {current_road}")
        if next_road:
            print(f"🗺️  Next: {next_road}")
        if distance:
            print(f"🗺️  Distance: {distance} {distance_unit}")
        if maneuver:
            print(f"🗺️  Maneuver: {maneuver}")
        if eta:
            print(f"🗺️  ETA: {eta}")
        
        self._media_logger.log_navigation(current_road, next_road, distance, distance_unit, maneuver, eta)
    
    def _handle_phone_metadata(self, media: dict):
        """Handle phone call metadata"""
        if 'PhoneCallStatus' in media:
            call_status = media.get('PhoneCallStatus', '')
            caller = media.get('PhoneCaller', 'Unknown')
            print(f"📞 Call: {call_status} - {caller}")
            self._media_logger.log_phone_call(call_status, caller)
    
    def _on_microphone_data(self, audio_data):
        """Handle microphone data and send to CarPlay"""
        if not self._carplay_node:
            return
        
        try:
            # Convert audio tuple to bytes
            import struct
            audio_bytes = struct.pack(f'{len(audio_data)}h', *audio_data)
            self._carplay_node.send_audio(audio_bytes)
            
            # Log periodically
            if not hasattr(self, '_mic_data_count'):
                self._mic_data_count = 0
            self._mic_data_count += 1
            if self._mic_data_count <= 5 or self._mic_data_count % 100 == 0:
                print(f"🎤 Microphone data sent #{self._mic_data_count}: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
    
    def _on_microphone_command(self, action: str, command):
        """Handle microphone start/stop commands from CarPlay"""
        print(f"🎤 Command: {action} ({command.name})")
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
                print(f"⚙️  Loaded video config: {self._video_config['width']}x{self._video_config['height']} @ {self._video_config['dpi']} DPI")
            except Exception as e:
                print(f"⚠️  Failed to load video config: {e}")
    
    def _save_video_config(self):
        """Save video configuration to file"""
        import json
        import os
        
        config_file = os.path.join(os.path.dirname(__file__), 'video_config.json')
        try:
            with open(config_file, 'w') as f:
                json.dump(self._video_config, f, indent=2)
            print(f"💾 Saved video config: {self._video_config['width']}x{self._video_config['height']} @ {self._video_config['dpi']} DPI")
        except Exception as e:
            print(f"⚠️  Failed to save video config: {e}")
    
    @Slot()
    def startMicrophone(self):
        """Start microphone recording (for Siri/calls)"""
        self._microphone.start()
        print("🎤 Microphone started")
    
    @Slot()
    def stopMicrophone(self):
        """Stop microphone recording"""
        self._microphone.stop()
        print("🎤 Microphone stopped")
    
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
            print(f"⚙️  Video settings updated: {width}x{height} @ {dpi} DPI")
            
            # Auto-reload device to apply settings
            if self._phone_connected:
                print(f"🔄 Phone connected - reloading device to apply settings...")
                QTimer.singleShot(500, self._reload_device)
            else:
                print(f"⚠️  No phone connected - settings will apply on next connection")
                self._pending_settings_reload = True
        else:
            print(f"⚙️  Video settings saved: {width}x{height} @ {dpi} DPI")
            print(f"⚠️  Connect dongle first to send settings")
    
    @Slot(str)
    def setCarPlayLabel(self, label: str):
        """Set CarPlay icon label"""
        if self._carplay_node:
            from src.protocol.sendable import SendIconConfig
            self._carplay_node.dongle_driver.send(SendIconConfig({'label': label}))
            print(f"⚙️  CarPlay label set to: {label}")
    
    @Slot(str)
    def setCarPlayIcon(self, icon_path: str):
        """Set CarPlay icon from PNG file
        
        Automatically uses pre-sized icons if available:
        - logo_120_120.png for 120x120
        - logo_180_180.png for 180x180
        - logo_256_256.png for 256x256
        """
        if not self._carplay_node:
            print("❌ CarPlay not connected")
            return
        
        try:
            from src.protocol.sendable import SendFile, FileAddress, SendIconConfig, SendCommand
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
                    print(f"📦 Loaded {os.path.basename(path)}: {len(data)} bytes")
                    return data
                return fallback_data
            
            icon_data_120 = read_icon(icon_120, read_icon(icon_path))
            icon_data_180 = read_icon(icon_180, icon_data_120)
            icon_data_256 = read_icon(icon_256, icon_data_120)
            
            # Send all icon sizes to dongle
            print("📤 Uploading icons to dongle...")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.OEM_ICON))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_120, FileAddress.ICON_120))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_180, FileAddress.ICON_180))
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.ICON_250))
            
            time.sleep(0.3)  # Wait for files to be written
            
            # Send configuration with label
            self._carplay_node.dongle_driver.send(SendIconConfig({'label': 'PyCarPlay'}))
            time.sleep(0.2)
            
            # Request UI refresh
            self._carplay_node.dongle_driver.send(SendCommand('requestHostUI'))
            
            print("✅ CarPlay icon and label updated")
            print("ℹ️  Note: May require iPhone reconnection to see changes")
            
        except Exception as e:
            print(f"❌ Error setting icon: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot(str)
    def sendKey(self, action: str):
        """Send key command to CarPlay
        
        Args:
            action: Command name (home, back, play, pause, etc.)
        """
        if self._carplay_node:
            self._carplay_node.send_key(action)
            print(f"⌨️  Key: {action}")
    
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
        
        from src.protocol.sendable import TouchAction
        
        # Get current resolution from config
        width = self._video_config['width']
        height = self._video_config['height']
        
        # Normalize to 0.0-1.0 range using actual resolution
        norm_x = max(0.0, min(1.0, x / width))
        norm_y = max(0.0, min(1.0, y / height))
        
        action_names = {14: "DOWN", 15: "MOVE", 16: "UP"}
        action_name = action_names.get(action, f"UNKNOWN({action})")
        
        self._carplay_node.send_touch(norm_x, norm_y, TouchAction(action))
        print(f"🖱️  Touch {action_name}: ({int(x)}, {int(y)}) -> ({norm_x:.3f}, {norm_y:.3f}) [{width}x{height}]")


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
    print("🚀 Auto-connecting to dongle...")
    QTimer.singleShot(500, video_controller.connectDongle)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
