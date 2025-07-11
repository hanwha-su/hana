"""
Configuration management for the alarm application.
"""
import json
import os

class AlarmConfig:
    def __init__(self, config_file='alarm_config.json'):
        self.config_file = config_file
        self.default_config = {
            'window_geometry': '600x500',
            'theme': 'light',
            'alarm_sound': True,
            'notification_duration': 30,
            'pastel_colors': {
                'background': '#FFF8E1',  # Light yellow
                'text': '#FF6B6B',        # Pastel red
                'accent': '#4ECDC4'       # Pastel teal
            }
        }
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key in self.default_config:
                    if key not in config:
                        config[key] = self.default_config[key]
                return config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()