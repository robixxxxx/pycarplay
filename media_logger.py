#!/usr/bin/env python3
"""
Media Logger - logs CarPlay media data to file
"""
from datetime import datetime
import json
import os


class MediaLogger:
    """Logs media events to file"""
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.enabled = False
        self.log_file = None
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def start(self):
        """Start logging to file"""
        if self.enabled:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.log_dir, f"carplay_media_{timestamp}.jsonl")
        self.log_file = open(log_path, 'w')
        self.enabled = True
        print(f"📝 Media logging started: {log_path}")
    
    def stop(self):
        """Stop logging"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.enabled = False
        print(f"📝 Media logging stopped")
    
    def log_music(self, song, artist, album, play_time_ms, duration_ms):
        """Log music playback"""
        if not self.enabled:
            return
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'music',
            'song': song,
            'artist': artist,
            'album': album,
            'play_time_ms': play_time_ms,
            'duration_ms': duration_ms
        }
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()
    
    def log_navigation(self, current_road, next_road, distance, distance_unit, maneuver, eta):
        """Log navigation data"""
        if not self.enabled:
            return
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'navigation',
            'current_road': current_road,
            'next_road': next_road,
            'distance': distance,
            'distance_unit': distance_unit,
            'maneuver': maneuver,
            'eta': eta
        }
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()
    
    def log_phone_call(self, status, caller):
        """Log phone call"""
        if not self.enabled:
            return
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'phone_call',
            'status': status,
            'caller': caller
        }
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()
    
    def log_raw(self, data_type, data):
        """Log raw data"""
        if not self.enabled:
            return
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': data_type,
            'data': data
        }
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()
