# Updated: Fixed JSON loading error when preset files contain mixed data types (strings and objects)
# Hotkey logic simplified to just trigger the app's functions.
import mouse
import keyboard
import json
import threading
import time
import os
import platform
from collections import namedtuple

CustomMouseEvent = namedtuple('CustomMouseEvent', ['event_type', 'details', 'time', 'x', 'y'])

if platform.system() == "Windows":
    try:
        import win32api, win32con
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False
    
MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'cmd', 'left ctrl', 'right ctrl', 'left alt', 'right alt', 'left shift', 'right shift'}

class Recorder:
    def __init__(self, log_callback, hotkey_actions):
        self.log_callback = log_callback
        self.hotkey_actions = hotkey_actions
        
        self.events = []
        self.is_recording = False
        self.is_playing = False
        
        self.ctrl_pressed = False
        self.recording_start_time = None
        self.recording_end_time = None
        self.hotkey_triggered = False
        self.hotkey_end_time = None
        
        # Cursor position management for playback
        self.playback_start_cursor_position = None

    def start_global_listener(self):
        threading.Thread(target=lambda: keyboard.hook(self._on_key_event), daemon=True).start()

    def _set_cursor_pos(self, x, y):
        if WIN32_AVAILABLE:
            win32api.SetCursorPos((x, y))
        else:
            mouse.move(x, y, absolute=True)

    def _get_cursor_pos(self):
        """Get current cursor position."""
        try:
            if WIN32_AVAILABLE:
                return win32api.GetCursorPos()
            else:
                return mouse.get_position()
        except Exception as e:
            self.log_callback(f"DEBUG: Could not get cursor position: {e}")
            return (0, 0)

    def _save_playback_cursor_position(self):
        """Save current cursor position before playback starts."""
        self.playback_start_cursor_position = self._get_cursor_pos()
        self.log_callback(f"DEBUG: Playback cursor position saved: {self.playback_start_cursor_position}")

    def _restore_playback_cursor_position(self):
        """Restore cursor position after playback ends."""
        if self.playback_start_cursor_position:
            self._set_cursor_pos(self.playback_start_cursor_position[0], self.playback_start_cursor_position[1])
            self.log_callback(f"DEBUG: Playback cursor position restored: {self.playback_start_cursor_position}")
        else:
            self.log_callback("DEBUG: No playback cursor position to restore")

    def _on_key_event(self, event: keyboard.KeyboardEvent):
        key_name = event.name
        is_ctrl = key_name in MODIFIER_KEYS
        current_time = time.time()
        
        if event.event_type == 'down':
            if is_ctrl:
                self.ctrl_pressed = True
            elif self.ctrl_pressed and key_name in self.hotkey_actions:
                self.hotkey_triggered = True
                self.hotkey_end_time = current_time + 0.2
                self.hotkey_actions[key_name]()
                return False
        
        if event.event_type == 'up' and is_ctrl:
            self.ctrl_pressed = False
            if self.hotkey_triggered:
                self.hotkey_end_time = current_time + 0.2

        if is_ctrl: return True

        if self.is_recording:
            if self.hotkey_triggered and current_time < self.hotkey_end_time:
                return True
            
            if self.hotkey_triggered and current_time >= self.hotkey_end_time:
                self.hotkey_triggered = False
                
            if not self.hotkey_triggered:
                self.events.append(event)
        
        return True

    def _on_key_event_with_modifiers(self, event: keyboard.KeyboardEvent):
        key_name = event.name
        is_modifier = key_name in MODIFIER_KEYS
        current_time = time.time()
        
        if event.event_type == 'down':
            if key_name == 'ctrl':
                self.ctrl_pressed = True
            elif self.ctrl_pressed and key_name in self.hotkey_actions:
                self.hotkey_triggered = True
                self.hotkey_end_time = current_time + 0.2
                self.hotkey_actions[key_name]()
                return False
        
        if event.event_type == 'up' and key_name == 'ctrl':
            self.ctrl_pressed = False
            if self.hotkey_triggered:
                self.hotkey_end_time = current_time + 0.2

        if self.is_recording:
            if self.hotkey_triggered and current_time < self.hotkey_end_time:
                return True
            
            if self.hotkey_triggered and current_time >= self.hotkey_end_time:
                self.hotkey_triggered = False
                
            if (not self.hotkey_triggered and 
                self.recording_start_time is not None and 
                current_time >= self.recording_start_time + 0.3):
                self.events.append(event)
        
        return True
            
    def _on_mouse_event(self, event):
        if not self.is_recording: return
        if isinstance(event, mouse.MoveEvent): return

        current_time = time.time()
        
        if self.hotkey_triggered and current_time < self.hotkey_end_time:
            return
            
        if (self.recording_start_time is not None and 
            current_time < self.recording_start_time + 0.3):
            return

        if isinstance(event, (mouse.ButtonEvent, mouse.WheelEvent)):
            try:
                current_pos = mouse.get_position()
                details = {}
                if isinstance(event, mouse.ButtonEvent):
                    if event.event_type not in [mouse.DOWN, mouse.UP, 'double']: return
                    details = {'button': event.button, 'action': event.event_type}
                elif isinstance(event, mouse.WheelEvent):
                    details = {'delta': event.delta}
                
                custom_event = CustomMouseEvent(
                    event_type=type(event).__name__, 
                    details=details, 
                    time=event.time, 
                    x=current_pos[0], 
                    y=current_pos[1]
                )
                self.events.append(custom_event)
            except Exception as e:
                self.log_callback(f"DEBUG: Could not process mouse event: {e}")

    def start_recording(self):
        if self.is_recording: return
        
        self.hotkey_triggered = False
        self.hotkey_end_time = None
        
        self.is_recording = True
        self.recording_start_time = time.time()
        self.events.clear()
        
        keyboard.unhook_all()
        threading.Thread(target=lambda: keyboard.hook(self._on_key_event_with_modifiers), daemon=True).start()
        
        mouse.hook(self._on_mouse_event)

    def stop_recording(self):
        if not self.is_recording: return
        
        self.hotkey_triggered = True
        self.hotkey_end_time = time.time() + 0.2
        
        self.recording_end_time = time.time()
        self.is_recording = False
        mouse.unhook_all()
        
        filtered_events = []
        for event in self.events:
            event_time = event.time
            if event_time < self.recording_end_time - 0.3:
                filtered_events.append(event)
        
        self.events = filtered_events
        
        keyboard.unhook_all()
        threading.Thread(target=lambda: keyboard.hook(self._on_key_event), daemon=True).start()
        
        self.hotkey_triggered = False
        self.hotkey_end_time = None

    def toggle_record(self):
        """Toggle between start and stop recording"""
        if self.is_recording:
            self.stop_recording()
            self.log_callback("Recording stopped.")
        else:
            self.start_recording()
            self.log_callback("Recording started.")

    def toggle_playback(self):
        """Toggle between start and stop playback"""
        if self.is_playing:
            self.stop_playback()
            self.log_callback("Playback stopped.")
        else:
            self.start_playback()

    def _playback_logic(self, speed_factor=1.0):
        self.is_playing = True
        
        try:
            if not self.events: return
            sorted_events = sorted(self.events, key=lambda e: e.time)
            if not sorted_events: return

            start_offset = sorted_events[0].time
            playback_start_time = time.time()

            for event in sorted_events:
                if not self.is_playing:
                    self.log_callback("Playback stopped by user.")
                    break

                relative_time = (event.time - start_offset) / speed_factor
                target_execution_time = playback_start_time + relative_time
                sleep_duration = target_execution_time - time.time()
                
                if sleep_duration > 0:
                    end_sleep = time.time() + sleep_duration
                    while time.time() < end_sleep:
                        if not self.is_playing: break
                        time.sleep(0.01)

                if not self.is_playing: break

                if isinstance(event, keyboard.KeyboardEvent):
                    if event.event_type == keyboard.KEY_DOWN: 
                        keyboard.press(event.name)
                    elif event.event_type == keyboard.KEY_UP: 
                        keyboard.release(event.name)
                elif isinstance(event, CustomMouseEvent):
                    self._set_cursor_pos(event.x, event.y)
                    time.sleep(0.025)
                    
                    if event.event_type == 'ButtonEvent':
                        button, action = event.details['button'], event.details['action']
                        if WIN32_AVAILABLE:
                            down_flag, up_flag = None, None
                            if button == mouse.LEFT: down_flag, up_flag = win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP
                            elif button == mouse.RIGHT: down_flag, up_flag = win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP
                            
                            if action == 'double':
                                if down_flag:
                                    win32api.mouse_event(down_flag, 0, 0, 0, 0); time.sleep(0.01)
                                    win32api.mouse_event(up_flag, 0, 0, 0, 0); time.sleep(0.05)
                                    win32api.mouse_event(down_flag, 0, 0, 0, 0); time.sleep(0.01)
                                    win32api.mouse_event(up_flag, 0, 0, 0, 0)
                            elif down_flag:
                                if action == mouse.DOWN: win32api.mouse_event(down_flag, 0, 0, 0, 0)
                                elif action == mouse.UP: win32api.mouse_event(up_flag, 0, 0, 0, 0)
                        else:
                             if action == 'double': mouse.double_click(button)
                             elif action == mouse.DOWN: mouse.press(button)
                             elif action == mouse.UP: mouse.release(button)
                    elif event.event_type == 'WheelEvent':
                        mouse.wheel(event.details['delta'])
            
            if self.is_playing: 
                self.log_callback("Playback finished naturally.")
        finally:
            self.is_playing = False
            self.reset_all_keys()
            # Restore cursor position after playback completion
            self._restore_playback_cursor_position()
            self.log_callback("UPDATE_STATUS:Idle:lightgrey")

    def reset_all_keys(self):
        try:
            for key in MODIFIER_KEYS:
                 if keyboard.is_pressed(key): keyboard.release(key)
            for button in [mouse.LEFT, mouse.RIGHT, mouse.MIDDLE]: mouse.release(button)
            self.log_callback("DEBUG: All keys and buttons reset.")
        except Exception as e:
            self.log_callback(f"DEBUG: Failed to reset keys: {e}")

    def start_playback(self, speed_factor=1.0):
        if self.is_playing: return
        if not self.get_events():
            self.log_callback("No preset loaded to play.")
            return
        
        # Save cursor position before playback starts
        self._save_playback_cursor_position()
        
        playback_thread = threading.Thread(target=self._playback_logic, args=(speed_factor,), daemon=True)
        playback_thread.start()

    def stop_playback(self):
        if not self.is_playing: return
        self.is_playing = False
        # Restore cursor position when playback is manually stopped
        self._restore_playback_cursor_position()

    def get_events(self):
        return self.events
    
    def clear_events(self):
        self.events.clear()
        # Clear playback cursor position when events are cleared
        self.playback_start_cursor_position = None

    def save_events(self, filename):
        def event_to_dict(event):
            if isinstance(event, keyboard.KeyboardEvent):
                return {'type': 'keyboard', 'event_type': event.event_type, 'scan_code': event.scan_code, 'name': event.name, 'time': event.time}
            elif isinstance(event, CustomMouseEvent):
                return {'type': 'mouse', 'event_type': event.event_type, 'details': event.details, 'time': event.time, 'x': event.x, 'y': event.y}
            return {}
        dict_events = [event_to_dict(e) for e in self.events]
        with open(filename, 'w') as f:
            json.dump(dict_events, f, indent=4)

    def load_events(self, filename):
        self.clear_events()
        try:
            with open(filename, 'r') as f: 
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_callback(f"Error loading preset {filename}: {e}")
            return

        # Handle different data formats
        if isinstance(data, list):
            dict_events = data
        elif isinstance(data, dict):
            dict_events = data.get('events', [])
        else:
            self.log_callback(f"Error: Invalid preset file format in {filename}")
            return

        # Process events with proper type checking
        for d in dict_events:
            # Skip non-dictionary items
            if not isinstance(d, dict):
                self.log_callback(f"DEBUG: Skipping invalid event data: {d}")
                continue
                
            event = None
            event_type = d.get('type')
            
            if event_type == 'keyboard':
                try:
                    event = keyboard.KeyboardEvent(
                        d.get('event_type', 'down'), 
                        d.get('scan_code', 0), 
                        name=d.get('name', ''), 
                        time=d.get('time', 0)
                    )
                except Exception as e:
                    self.log_callback(f"DEBUG: Could not create keyboard event: {e}")
                    continue
                    
            elif event_type == 'mouse':
                try:
                    event = CustomMouseEvent(
                        event_type=d.get('event_type', 'ButtonEvent'), 
                        details=d.get('details', {}), 
                        time=d.get('time', 0), 
                        x=d.get('x', 0), 
                        y=d.get('y', 0)
                    )
                except Exception as e:
                    self.log_callback(f"DEBUG: Could not create mouse event: {e}")
                    continue
            else:
                self.log_callback(f"DEBUG: Unknown event type: {event_type}")
                continue
            
            if event: 
                self.events.append(event)
        
        self.log_callback(f"Successfully loaded {len(self.events)} events from {os.path.basename(filename)}")