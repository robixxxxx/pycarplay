#!/usr/bin/env python3
"""
Simple example using CarplayNode high-level API
"""
import time
from carplay_node import CarplayNode, CarplayMessage, MessageType
from dongle_driver import DongleConfig, HandDriveType
from messages import (
    VideoData, AudioData, Plugged, MediaData,
    WifiMacAddress, BluetoothMacAddress, EthernetMacAddress
)


def main():
    """Simple CarPlay example"""
    
    # Configure dongle
    config = DongleConfig(
        width=1280,
        height=720,
        fps=30,
        dpi=160,
        box_name="pyCarPlay-Example",
        hand=HandDriveType.LHD,
        wifi_type="5ghz",
        mic_type="os"
    )
    
    # Create CarPlay node
    carplay = CarplayNode(config)
    
    # Statistics
    video_frames = 0
    audio_packets = 0
    
    def on_message(msg: CarplayMessage):
        """Handle CarPlay messages"""
        nonlocal video_frames, audio_packets
        
        if msg.msg_type == MessageType.PLUGGED:
            if isinstance(msg.message, Plugged):
                print(f"\n📱 Phone connected: {msg.message.phone_type.name}")
                if msg.message.wifi:
                    print(f"   WiFi available: Yes")
        
        elif msg.msg_type == MessageType.UNPLUGGED:
            print("\n📱 Phone disconnected")
            print(f"   Session stats: {video_frames} video frames, {audio_packets} audio packets")
            video_frames = 0
            audio_packets = 0
        
        elif msg.msg_type == MessageType.VIDEO:
            if isinstance(msg.message, VideoData):
                video_frames += 1
                if video_frames % 30 == 0:  # Log every 30 frames (~1 second at 30fps)
                    print(f"📹 Video: {msg.message.width}x{msg.message.height}, "
                          f"{len(msg.message.data)} bytes, "
                          f"flags={msg.message.flags:#x}, "
                          f"frame #{video_frames}")
        
        elif msg.msg_type == MessageType.AUDIO:
            if isinstance(msg.message, AudioData):
                audio_packets += 1
                if msg.message.command:
                    print(f"🎤 Audio command: {msg.message.command.name}")
                elif msg.message.data and audio_packets % 100 == 0:
                    print(f"🔊 Audio: {len(msg.message.data)} samples, "
                          f"volume={msg.message.volume:.2f}, "
                          f"packet #{audio_packets}")
        
        elif msg.msg_type == MessageType.MEDIA:
            if isinstance(msg.message, MediaData) and msg.message.payload:
                if msg.message.payload.get('type') == 1:  # MediaType.Data
                    media = msg.message.payload.get('media', {})
                    print(f"\n🎵 Now playing:")
                    if 'MediaSongName' in media:
                        print(f"   Song: {media['MediaSongName']}")
                    if 'MediaArtistName' in media:
                        print(f"   Artist: {media['MediaArtistName']}")
                    if 'MediaAlbumName' in media:
                        print(f"   Album: {media['MediaAlbumName']}")
                    if 'MediaAPPName' in media:
                        print(f"   App: {media['MediaAPPName']}")
                elif msg.message.payload.get('type') == 3:  # MediaType.AlbumCover
                    print(f"🎨 Album cover received (base64)")
        
        elif msg.msg_type == MessageType.COMMAND:
            print(f"⌨️  Command: {msg.message.value}")
        
        elif msg.msg_type == MessageType.WIFI_MAC:
            if isinstance(msg.message, WifiMacAddress):
                print(f"📡 WiFi MAC: {msg.message.mac}")
        
        elif msg.msg_type == MessageType.BT_MAC:
            if isinstance(msg.message, BluetoothMacAddress):
                print(f"📶 Bluetooth MAC: {msg.message.mac}")
        
        elif msg.msg_type == MessageType.ETH_MAC:
            if isinstance(msg.message, EthernetMacAddress):
                print(f"🔌 Ethernet MAC: {msg.message.mac}")
        
        elif msg.msg_type == MessageType.FAILURE:
            print("\n❌ CarPlay communication failed!")
    
    # Set callback
    carplay.onmessage = on_message
    
    # Start CarPlay
    print("=" * 60)
    print("PyCarPlay Example")
    print("=" * 60)
    print("\nStarting CarPlay...")
    print("1. Make sure dongle is plugged in")
    print("2. Connect your iPhone/Android to the dongle")
    print("3. Watch the magic happen! 🎉\n")
    
    try:
        carplay.start()
        
        print("\n" + "=" * 60)
        print("CarPlay running! Press Ctrl+C to stop")
        print("=" * 60 + "\n")
        
        # Keep running and show stats periodically
        start_time = time.time()
        while True:
            time.sleep(10)
            elapsed = int(time.time() - start_time)
            if video_frames > 0 or audio_packets > 0:
                print(f"\n📊 Stats (after {elapsed}s): "
                      f"{video_frames} video frames, {audio_packets} audio packets")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping CarPlay...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        carplay.stop()
        print("✅ Stopped\n")


if __name__ == "__main__":
    main()
