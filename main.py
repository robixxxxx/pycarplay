#!/usr/bin/env python3
"""
PySide6 application with QML for displaying video stream
"""
import sys
from pathlib import Path
from PySide6.QtCore import QUrl, QObject, Slot, Signal, Property, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from carplay_node import CarplayNode, CarplayMessage, MessageType
from dongle_driver import DongleConfig, HandDriveType
from messages import VideoData, AudioData, Plugged, Unplugged, Opened, DECODE_TYPE_MAP
from video_decoder import VideoDecoder
from video_provider import VideoFrameProvider
from audio_player import AudioPlayer
from media_logger import MediaLogger
from microphone import MicrophoneInput


class VideoStreamController(QObject):
    """Controller class for managing video stream"""
    
    videoSourceChanged = Signal(str)
    dongleStatusChanged = Signal(str)
    dongleConnected = Signal()
    dongleDisconnected = Signal()
    videoFrameReceived = Signal(int, int, int)  # width, height, data_length
    audioReceived = Signal(int)  # audio data length
    currentSongChanged = Signal(str)
    currentArtistChanged = Signal(str)
    navigationInfoChanged = Signal(str)
    showConfigPanel = Signal()  # Signal to show CarPlay config panel
    hideConfigPanel = Signal()  # Signal to hide CarPlay config panel
    
    def __init__(self, video_provider: VideoFrameProvider):
        super().__init__()
        self._video_source = ""
        self._dongle_status = "Disconnected"
        self._carplay_node = None
        self._video_decoder = VideoDecoder()
        self._video_provider = video_provider
        self._audio_player = AudioPlayer()
        self._media_logger = MediaLogger()
        self._microphone = MicrophoneInput()
        self._current_song = ""
        self._current_artist = ""
        self._navigation_info = ""
        self._siri_mode = False  # Track if in Siri/voice mode (mono audio)
        
        # Connect decoder to video provider
        self._video_decoder.frameDecoded.connect(self._video_provider.updateFrame)
        
        # Connect decoder errors to reconnect handler
        self._video_decoder.tooManyErrors.connect(self._on_decoder_errors)
        
        # Connect microphone to CarPlay
        self._microphone.micDataReady.connect(self._on_microphone_data)
        
    @Property(str, notify=videoSourceChanged)
    def videoSource(self):
        return self._video_source
    
    @videoSource.setter
    def videoSource(self, value):
        if self._video_source != value:
            self._video_source = value
            self.videoSourceChanged.emit(value)
    
    @Slot(str)
    def loadVideo(self, url):
        """Load video from URL or file path"""
        print(f"Loading video: {url}")
        self._video_source = url
        self.videoSourceChanged.emit(url)
    
    @Slot()
    def playVideo(self):
        """Start video playback"""
        print("Playing video")
    
    @Slot()
    def pauseVideo(self):
        """Pause video playback"""
        print("Pausing video")
    
    @Slot()
    def startMediaLogging(self):
        """Start logging media data to file"""
        self._media_logger.start()
    
    @Slot()
    def stopMediaLogging(self):
        """Stop logging media data"""
        self._media_logger.stop()
    
    @Slot()
    def stopVideo(self):
        """Stop video playback"""
        print("Stopping video")
    
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
            
            # Create CarPlay config
            config = DongleConfig(
                width=1280,
                height=720,
                fps=30,
                dpi=160,
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
        """Handle too many decoder errors - force reconnection"""
        print("🔄 Decoder errors detected - forcing reconnection...")
        
        # Disconnect and reconnect to force fresh stream
        self.disconnectDongle()
        
        # Wait a moment before reconnecting
        QTimer.singleShot(2000, self.connectDongle)  # Reconnect after 2 seconds
    
    def _on_carplay_message(self, msg: CarplayMessage):
        """Handle messages from CarPlay node"""
        
        if msg.msg_type == MessageType.PLUGGED:
            if isinstance(msg.message, Plugged):
                phone_type = msg.message.phone_type.name
                print(f"Phone plugged: {phone_type}")
                self.dongleStatus = f"Connected - {phone_type}"
                self.dongleConnected.emit()
                
                # Send CarPlay icon (which also sets the label)
                self.setCarPlayIcon("/Users/robertburda/dev/python/pycarplay/logo.png")
        
        elif msg.msg_type == MessageType.UNPLUGGED:
            print("Phone unplugged")
            self.dongleStatus = "Connected - No phone"
        
        elif msg.msg_type == MessageType.VIDEO:
            if isinstance(msg.message, VideoData):
                # Decode H264 frame
                self._video_decoder.decode_frame(msg.message.data)
                # Signal is emitted automatically via frameDecoded -> updateFrame
                
                # Emit info signal every 30 frames
                if self._video_provider.frameCount % 30 == 0:
                    self.videoFrameReceived.emit(
                        msg.message.width, 
                        msg.message.height, 
                        len(msg.message.data)
                    )
        
        elif msg.msg_type == MessageType.AUDIO:
            if isinstance(msg.message, AudioData):
                if msg.message.data:
                    try:
                        # Check if we need to update sample rate based on decode type
                        if msg.message.decode_type in DECODE_TYPE_MAP:
                            audio_format = DECODE_TYPE_MAP[msg.message.decode_type]
                            
                            # Siri uses MONO audio, music uses STEREO
                            channels = 1 if self._siri_mode else 2
                            self._audio_player.setSampleRate(audio_format.frequency, channels)
                        
                        # Send PCM audio data to player
                        self._audio_player.playAudioData(msg.message.data)
                        self.audioReceived.emit(len(msg.message.data))
                        
                        # Debug: Show only first few and periodic updates
                        if self._audio_player._frames_received <= 5 or self._audio_player._frames_received % 500 == 0:
                            print(f"🔊 Audio frame #{self._audio_player._frames_received}: "
                                  f"{len(msg.message.data)} samples, format: {audio_format.frequency}Hz")
                    except Exception as e:
                        print(f"🔊 ERROR playing audio: {e}")
                        import traceback
                        traceback.print_exc()
                elif msg.message.command:
                    from messages import AudioCommand
                    command_name = msg.message.command.name if hasattr(msg.message.command, 'name') else msg.message.command
                    print(f"🔊 Audio command: {command_name}")
                    
                    # Handle AudioInputConfig - show config panel
                    if msg.message.command == AudioCommand.AudioInputConfig:
                        print("⚙️  AudioInputConfig - showing config panel")
                        self.showConfigPanel.emit()
                    
                    # Handle Siri mode - uses 16kHz MONO instead of stereo
                    elif msg.message.command == AudioCommand.AudioSiriStart:
                        self._siri_mode = True
                    elif msg.message.command == AudioCommand.AudioSiriStop:
                        self._siri_mode = False
                    
                elif msg.message.volume_duration:
                    print(f"🔊 Volume duration: {msg.message.volume_duration}")
            else:
                print(f"🔊 Audio message but not AudioData type: {type(msg.message)}")
        
        elif msg.msg_type == MessageType.FAILURE:
            print("❌ CarPlay communication failed")
            self.dongleStatus = "Failed"
            self.dongleDisconnected.emit()
        
        elif msg.msg_type == MessageType.COMMAND:
            command_value = msg.message.value
            print(f"⚙️  Command received: {command_value}")
            
            # Command 3 = AudioInputConfig - show config panel
            if command_value == 3:
                print("⚙️  AudioInputConfig (Command 3) - showing config panel")
                self.showConfigPanel.emit()
            # Command 1 = Show config panel, Command 2 = Hide config panel
            elif command_value == 1:
                print("⚙️  Showing CarPlay config panel")
                self.showConfigPanel.emit()
            elif command_value == 2:
                print("⚙️  Hiding CarPlay config panel")
                self.hideConfigPanel.emit()
        
        elif msg.msg_type == MessageType.BLUETOOTH_ADDRESS:
            print(f"📱 Bluetooth Address: {msg.message}")
        
        elif msg.msg_type == MessageType.BLUETOOTH_DEVICE_NAME:
            print(f"📱 Bluetooth Device Name: {msg.message}")
        
        elif msg.msg_type == MessageType.WIFI_DEVICE_NAME:
            print(f"📶 WiFi Device Name: {msg.message}")
        
        elif msg.msg_type == MessageType.HEARTBEAT:
            # Don't log heartbeat every time - too spammy
            pass
        
        elif msg.msg_type == MessageType.PHASE:
            if hasattr(msg.message, 'phase'):
                print(f"🔄 Connection Phase: {msg.message.phase}")

        
        elif msg.msg_type == MessageType.MEDIA:
            if msg.message.payload:
                media_type = msg.message.payload.get('type')
                
                if media_type == 3:  # Album Cover
                    print(f"🎨 Album Cover received (base64 image)")
                
                elif media_type == 1:  # Media Data
                    media = msg.message.payload.get('media', {})
                    
                    # Music metadata
                    if 'MediaSongTitle' in media:
                        song = media.get('MediaSongTitle', 'Unknown')
                        artist = media.get('MediaArtist', 'Unknown')
                        album = media.get('MediaAlbum', 'Unknown')
                        print(f"🎵 Now Playing: {song} - {artist} (Album: {album})")
                        
                        # Update UI properties
                        self.currentSong = song
                        self.currentArtist = f"{artist} • {album}"
                        
                        # Log to file if enabled
                        play_time_ms = media.get('MediaSongPlayTime', 0)
                        duration_ms = media.get('MediaSongDuration', 0)
                        self._media_logger.log_music(song, artist, album, play_time_ms, duration_ms)
                    
                    if 'MediaSongPlayTime' in media and 'MediaSongTitle' not in media:
                        # Just playback position update, don't spam console
                        play_time_ms = media.get('MediaSongPlayTime', 0)
                        duration_ms = media.get('MediaSongDuration', 0)
                        play_time_sec = play_time_ms / 1000
                        duration_sec = duration_ms / 1000
                        # Only log every 10 seconds to avoid spam
                        if int(play_time_sec) % 10 == 0:
                            print(f"⏱️  Playback: {play_time_sec:.1f}s / {duration_sec:.1f}s")
                    
                    # Navigation data
                    if 'NaviCurrentRoad' in media or 'NaviDistance' in media or 'NaviManeuver' in media:
                        current_road = media.get('NaviCurrentRoad', '')
                        next_road = media.get('NaviNextRoad', '')
                        distance = media.get('NaviDistance', 0)
                        distance_unit = media.get('NaviDistanceUnit', '')
                        maneuver = media.get('NaviManeuver', '')
                        eta = media.get('NaviETA', '')
                        
                        # Update UI property
                        nav_text = ""
                        if maneuver:
                            nav_text = f"{maneuver}"
                        if distance:
                            nav_text = f"{nav_text} • {distance} {distance_unit}" if nav_text else f"{distance} {distance_unit}"
                        if current_road:
                            nav_text = f"{nav_text} • {current_road}" if nav_text else current_road
                        self.navigationInfo = nav_text
                        
                        if current_road:
                            print(f"🗺️  Navigation: Current road: {current_road}")
                        if next_road:
                            print(f"🗺️  Navigation: Next road: {next_road}")
                        if distance:
                            print(f"🗺️  Navigation: Distance: {distance} {distance_unit}")
                        if maneuver:
                            print(f"🗺️  Navigation: Maneuver: {maneuver}")
                        if eta:
                            print(f"🗺️  Navigation: ETA: {eta}")
                        
                        # Log to file
                        self._media_logger.log_navigation(current_road, next_road, distance, distance_unit, maneuver, eta)
                    
                    # Phone call info
                    if 'PhoneCallStatus' in media:
                        call_status = media.get('PhoneCallStatus', '')
                        caller = media.get('PhoneCaller', 'Unknown')
                        print(f"📞 Call Status: {call_status} - {caller}")
                        self._media_logger.log_phone_call(call_status, caller)
                    
                    # Show raw data for unknown fields
                    known_fields = {
                        'MediaSongTitle', 'MediaArtist', 'MediaAlbum', 'MediaSongPlayTime', 'MediaSongDuration',
                        'NaviCurrentRoad', 'NaviNextRoad', 'NaviDistance', 'NaviDistanceUnit', 
                        'NaviManeuver', 'NaviETA', 'PhoneCallStatus', 'PhoneCaller'
                    }
                    unknown_fields = {k: v for k, v in media.items() if k not in known_fields}
                    if unknown_fields:
                        print(f"📊 Other media data: {unknown_fields}")
            else:
                print(f"Media data: {msg.message.payload}")
    
    def _on_microphone_data(self, audio_data):
        """Handle microphone data and send to CarPlay"""
        if self._carplay_node:
            try:
                # Convert tuple to bytes
                import struct
                audio_bytes = struct.pack(f'{len(audio_data)}h', *audio_data)
                self._carplay_node.send_audio(audio_bytes)
                
                # Log first few sends
                if not hasattr(self, '_mic_data_count'):
                    self._mic_data_count = 0
                self._mic_data_count += 1
                if self._mic_data_count <= 5 or self._mic_data_count % 100 == 0:
                    print(f"🎤 Sent microphone data #{self._mic_data_count}: {len(audio_bytes)} bytes")
            except Exception as e:
                print(f"🎤 Error sending microphone data: {e}")
    
    def _on_microphone_command(self, action: str, command):
        """Handle microphone start/stop commands from CarPlay"""
        print(f"🎤 Microphone command received: action={action}, command={command}")
        if action == 'start':
            self.startMicrophone()
        elif action == 'stop':
            self.stopMicrophone()
    
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
    
    @Slot(str)
    def setCarPlayLabel(self, label: str):
        """Set CarPlay icon label"""
        if self._carplay_node:
            from sendable import SendIconConfig
            self._carplay_node.dongle_driver.send(SendIconConfig({'label': label}))
            print(f"⚙️  CarPlay label set to: {label}")
    
    @Slot(str)
    def setCarPlayIcon(self, icon_path: str):
        """Set CarPlay icon from PNG file"""
        if not self._carplay_node:
            print("❌ CarPlay not connected - cannot set icon")
            return
        
        try:
            from sendable import SendFile, FileAddress
            import os
            
            # Determine base path and check if we have pre-sized icons
            base_dir = os.path.dirname(icon_path)
            base_name = os.path.splitext(os.path.basename(icon_path))[0]
            
            # Icon paths with different sizes
            icon_120 = os.path.join(base_dir, f"{base_name}_120_120.png")
            icon_180 = os.path.join(base_dir, f"{base_name}_180_180.png")
            icon_256 = os.path.join(base_dir, f"{base_name}_256_256.png")
            
            # Check if pre-sized icons exist, otherwise use the original
            if os.path.exists(icon_120):
                print(f"📁 Using pre-sized 120x120 icon: {icon_120}")
                with open(icon_120, 'rb') as f:
                    icon_data_120 = f.read()
                print(f"📦 Icon 120x120 loaded: {len(icon_data_120)} bytes")
            else:
                print(f"📁 Reading original icon: {icon_path}")
                with open(icon_path, 'rb') as f:
                    icon_data_120 = f.read()
                print(f"⚠️  Warning: Using original icon for 120x120 ({len(icon_data_120)} bytes)")
            
            if os.path.exists(icon_180):
                print(f"📁 Using pre-sized 180x180 icon: {icon_180}")
                with open(icon_180, 'rb') as f:
                    icon_data_180 = f.read()
                print(f"📦 Icon 180x180 loaded: {len(icon_data_180)} bytes")
            else:
                icon_data_180 = icon_data_120
            
            if os.path.exists(icon_256):
                print(f"📁 Using pre-sized 256x256 icon: {icon_256}")
                with open(icon_256, 'rb') as f:
                    icon_data_256 = f.read()
                print(f"📦 Icon 256x256 loaded: {len(icon_data_256)} bytes")
            else:
                icon_data_256 = icon_data_120
            
            # Send icons to all standard locations
            print(f"📤 Sending 256x256 icon to {FileAddress.OEM_ICON}")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.OEM_ICON))
            
            print(f"📤 Sending 120x120 icon to {FileAddress.ICON_120}")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_120, FileAddress.ICON_120))
            
            print(f"📤 Sending 180x180 icon to {FileAddress.ICON_180}")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_180, FileAddress.ICON_180))
            
            print(f"📤 Sending 256x256 icon to {FileAddress.ICON_250}")
            self._carplay_node.dongle_driver.send(SendFile(icon_data_256, FileAddress.ICON_250))
            
            print(f"✅ All icon files sent successfully")
            
            # Delay to ensure icons are written before config
            import time
            time.sleep(0.3)
            
            # Update config to use the icon with label
            from sendable import SendIconConfig
            print(f"📤 Sending icon configuration with label...")
            config = {'label': 'PyCarPlay'}
            self._carplay_node.dongle_driver.send(SendIconConfig(config))
            print(f"✅ Icon configuration sent: {config}")
            
            # Additional delay before refreshing
            time.sleep(0.2)
            
            # Send a command to refresh (optional)
            from sendable import SendCommand
            print(f"📤 Requesting UI refresh...")
            self._carplay_node.dongle_driver.send(SendCommand('requestHostUI'))
            
            print("ℹ️  Note: Icon change may require iPhone reconnection to CarPlay")
            
        except FileNotFoundError as e:
            print(f"❌ Icon file not found: {e}")
        except Exception as e:
            print(f"❌ Error setting icon: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot(str)
    def sendKey(self, action: str):
        """Send key command to CarPlay"""
        if self._carplay_node:
            self._carplay_node.send_key(action)
            print(f"Sent key: {action}")
    
    @Slot(float, float, int)
    def sendTouch(self, x: float, y: float, action: int):
        """Send touch event to CarPlay
        
        Args:
            x: X coordinate in video space (0-1280)
            y: Y coordinate in video space (0-720)
            action: TouchAction value (14=Down, 15=Move, 16=Up)
        """
        if self._carplay_node:
            from sendable import TouchAction
            
            # Normalize coordinates to 0.0-1.0 range
            # Video is 1280x720
            norm_x = x / 1280.0
            norm_y = y / 720.0
            
            # Clamp to valid range
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))
            
            action_name = {14: "DOWN", 15: "MOVE", 16: "UP"}.get(action, f"UNKNOWN({action})")
            self._carplay_node.send_touch(norm_x, norm_y, TouchAction(action))
            print(f"🖱️  Touch {action_name}: screen({int(x)}, {int(y)}) -> normalized({norm_x:.3f}, {norm_y:.3f})")


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
    qml_file = Path(__file__).parent / "main.qml"
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
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
