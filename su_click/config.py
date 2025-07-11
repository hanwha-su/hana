# Updated: Modified hotkey configuration to support specific Ctrl+key combinations with separate functions
import os
import json
from datetime import datetime
import subprocess

class ConfigManager:
    def __init__(self, config_file="config.json", preset_folder="presets"):
        self.config_file = config_file
        self.preset_folder = preset_folder
        self.last_saved_preset = ""
        if not os.path.exists(self.preset_folder):
            os.makedirs(self.preset_folder)

    def _load_config_data(self):
        """Helper to load the entire config JSON."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config_data(self, data):
        """Helper to save the entire config JSON."""
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)

    def get_default_hotkey_config(self):
        """Get default hotkey configuration."""
        return {
            'start_recording': 'f8',
            'stop_recording_and_playback': 'f9',
            'start_playback': 'f10',
            'exit': 'f12'
        }

    def save_hotkey_config(self, hotkey_config):
        """Save hotkey configuration."""
        config = self._load_config_data()
        config['hotkey_config'] = hotkey_config
        self._save_config_data(config)

    def load_hotkey_config(self):
        """Load hotkey configuration."""
        config = self._load_config_data()
        return config.get('hotkey_config', self.get_default_hotkey_config())

    def save_geometry(self, geometry):
        config = self._load_config_data()
        config['geometry'] = geometry
        self._save_config_data(config)

    def load_geometry(self):
        config = self._load_config_data()
        return config.get('geometry')

    def save_pinned_presets(self, pinned_list):
        config = self._load_config_data()
        config['pinned_presets'] = pinned_list
        self._save_config_data(config)

    def load_pinned_presets(self):
        config = self._load_config_data()
        return config.get('pinned_presets', [])

    def get_preset_path(self, preset_name):
        if not preset_name.endswith('.json'):
            preset_name += '.json'
        return os.path.join(self.preset_folder, preset_name)

    def get_next_preset_name(self):
        today = datetime.now().strftime("%Y%m%d")
        i = 1
        while True:
            preset_name = f"{today}_{i:03d}.json"
            if not os.path.exists(self.get_preset_path(preset_name)):
                return self.get_preset_path(preset_name)
            i += 1
            
    def get_last_session_preset_name(self):
         return self.get_preset_path("last_session.json")

    def list_presets(self):
        files = [f for f in os.listdir(self.preset_folder) if f.endswith('.json')]
        files.sort(key=lambda f: os.path.getmtime(self.get_preset_path(f)), reverse=True)
        return files

    def open_preset_in_notepad(self, preset_name):
        filepath = self.get_preset_path(preset_name)
        try:
            subprocess.Popen(['notepad.exe', filepath])
        except FileNotFoundError:
            print("Notepad not found.")

    def rename_preset(self, old_name, new_name):
        if not new_name.endswith('.json'):
            new_name += '.json'
            
        old_path = self.get_preset_path(old_name)
        new_path = self.get_preset_path(new_name)
        if os.path.exists(new_path):
            return False
        os.rename(old_path, new_path)
        return True

    def delete_preset(self, preset_name):
        os.remove(self.get_preset_path(preset_name))