"""
Data storage management for alarms and tasks.
"""
import json
import os
from datetime import datetime

class AlarmStorage:
    def __init__(self, storage_file='alarm_data.json'):
        self.storage_file = storage_file
        self.alarms = self.load_alarms()
    
    def load_alarms(self):
        """Load alarms from storage file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            else:
                return []
        except Exception as e:
            print(f"Error loading alarms: {e}")
            return []
    
    def save_alarms(self):
        """Save alarms to storage file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.alarms, f, indent=2)
        except Exception as e:
            print(f"Error saving alarms: {e}")
    
    def add_alarm(self, title, description, date_time, enabled=True):
        """Add a new alarm."""
        alarm = {
            'id': self._generate_id(),
            'title': title,
            'description': description,
            'date_time': date_time,
            'enabled': enabled,
            'created_at': datetime.now().isoformat(),
            'triggered': False
        }
        self.alarms.append(alarm)
        self.save_alarms()
        return alarm
    
    def update_alarm(self, alarm_id, **kwargs):
        """Update an existing alarm."""
        for alarm in self.alarms:
            if alarm['id'] == alarm_id:
                alarm.update(kwargs)
                self.save_alarms()
                return True
        return False
    
    def delete_alarm(self, alarm_id):
        """Delete an alarm."""
        self.alarms = [alarm for alarm in self.alarms if alarm['id'] != alarm_id]
        self.save_alarms()
    
    def get_alarm(self, alarm_id):
        """Get a specific alarm by ID."""
        for alarm in self.alarms:
            if alarm['id'] == alarm_id:
                return alarm
        return None
    
    def get_all_alarms(self):
        """Get all alarms."""
        return self.alarms
    
    def get_pending_alarms(self):
        """Get alarms that are enabled and not yet triggered."""
        return [alarm for alarm in self.alarms if alarm['enabled'] and not alarm['triggered']]
    
    def _generate_id(self):
        """Generate a unique ID for alarms."""
        if not self.alarms:
            return 1
        return max(alarm['id'] for alarm in self.alarms) + 1