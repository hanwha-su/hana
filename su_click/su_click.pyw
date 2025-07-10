# su_click.pyw
# Restored the missing load_config method.
import tkinter as tk
from tkinter import simpledialog, messagebox
import os
from record import Recorder
from config import ConfigManager

class SuClickApp:
    def __init__(self, root):
        self.root = root
        self.root.title("su_click")
        self.config = ConfigManager()
        
        hotkey_actions = {
            'f8': self.start_recording,
            'f9': self.stop_recording,
            'f10': self.start_playback,
            'f11': self.stop_playback,
            'f12': self.exit_app
        }
        
        self.recorder = Recorder(self.safe_log_callback, hotkey_actions)
        # --- Pinning System ---
        self.pinned_presets = set(self.config.load_pinned_presets())
        
        self.setup_ui()
        self.recorder.start_global_listener()
        
        self.load_presets()
        self.load_config() # This function is now restored
        self.auto_load_last_preset()

    def setup_ui(self):
        self.status_bar = tk.Label(self.root, text="Idle", bg="lightgrey", fg="black", height=2)
        self.status_bar.pack(fill=tk.X)
        self.log_area = tk.Text(self.root, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        left_frame = tk.Frame(bottom_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preset_list = tk.Listbox(left_frame)
        self.preset_list.pack(fill=tk.BOTH, expand=True)
        self.preset_list.bind("<Button-1>", self.on_preset_single_click)
        self.preset_list.bind("<Double-Button-1>", self.on_preset_double_click)
        self.preset_list.bind("<F2>", self.rename_preset)
        self.preset_list.bind("<Delete>", self.delete_preset)
        self.preset_list.bind("<Button-3>", self.show_context_menu)
        
        right_frame = tk.Frame(bottom_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True, padx=5, pady=5)
        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill=tk.X)
        buttons = [
            ("Record (Ctrl+F8)", self.start_recording),
            ("Stop Record (Ctrl+F9)", self.stop_recording),
            ("Play (Ctrl+F10)", self.start_playback),
            ("Stop Play (Ctrl+F11)", self.stop_playback),
            ("Exit (Ctrl+F12)", self.exit_app)
        ]
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command)
            btn.pack(fill=tk.X, padx=5, pady=2)
        speed_frame = tk.Frame(right_frame, pady=10)
        speed_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(speed_frame, text="Playback Speed:").pack(side=tk.LEFT, padx=(0, 5))
        self.speed_var = tk.StringVar(value="1.0")
        self.speed_entry = tk.Entry(speed_frame, textvariable=self.speed_var, width=10)
        self.speed_entry.pack(side=tk.LEFT)

    def show_context_menu(self, event):
        selection_index = self.preset_list.nearest(event.y)
        if selection_index == -1: return

        self.preset_list.selection_clear(0, tk.END)
        self.preset_list.selection_set(selection_index)
        
        selected_item = self.preset_list.get(selection_index)
        if "----" in selected_item: return
        
        raw_preset_name = selected_item.lstrip('📌 ')
        
        context_menu = tk.Menu(self.root, tearoff=0)
        
        if raw_preset_name in self.pinned_presets:
            context_menu.add_command(label="Unpin Preset", command=self.unpin_selected_preset)
        else:
            context_menu.add_command(label="Pin Preset", command=self.pin_selected_preset)
        
        context_menu.tk_popup(event.x_root, event.y_root)

    def pin_selected_preset(self):
        selection_index = self.preset_list.curselection()
        if not selection_index: return
        raw_preset_name = self.preset_list.get(selection_index[0]).lstrip('📌 ')
        
        self.pinned_presets.add(raw_preset_name)
        self.config.save_pinned_presets(list(self.pinned_presets))
        self.load_presets()

    def unpin_selected_preset(self):
        selection_index = self.preset_list.curselection()
        if not selection_index: return
        raw_preset_name = self.preset_list.get(selection_index[0]).lstrip('📌 ')

        self.pinned_presets.discard(raw_preset_name)
        self.config.save_pinned_presets(list(self.pinned_presets))
        self.load_presets()
    
    def safe_log_callback(self, message):
        self.root.after(0, self.log_handler, message)

    def log_handler(self, message):
        if self.root.winfo_exists():
            if message.startswith("UPDATE_STATUS:"):
                try: _, text, color = message.split(":", 2)
                except ValueError: text, color = "Idle", "lightgrey"
                self.update_status(text, color)
            else:
                self.log_area.insert(tk.END, message + "\n")
                self.log_area.see(tk.END)

    def update_status(self, text, color):
        if self.root.winfo_exists():
            self.status_bar.config(text=text, bg=color)

    def start_recording(self):
        if not self.recorder.is_recording and not self.recorder.is_playing:
            self.update_status("Recording...", "red")
            self.log_handler("Recording started.")
            self.recorder.start_recording()

    def stop_recording(self):
        if self.recorder.is_recording:
            self.recorder.stop_recording()
            self.update_status("Idle", "lightgrey")
            self.log_handler("Recording stopped.")
            self.save_preset()
            self.load_presets()
            
            if self.preset_list.size() > 0:
                new_preset_name = os.path.basename(self.config.last_saved_preset)
                items = self.preset_list.get(0, tk.END)
                if new_preset_name in items:
                    new_idx = items.index(new_preset_name)
                    self.preset_list.selection_set(new_idx)
                    self.preset_list.see(new_idx)

    def start_playback(self):
        if self.recorder.is_playing: return
        try:
            speed = float(self.speed_var.get())
            if speed <= 0: raise ValueError
        except ValueError:
            self.log_handler("Error: Invalid playback speed.")
            return
        self.update_status("Playing...", "green")
        self.log_handler(f"Playback started (Speed: {speed}x).")
        self.recorder.start_playback(speed_factor=speed)
    
    def stop_playback(self):
        self.recorder.stop_playback()

    def save_preset(self):
        preset_name_with_path = self.config.get_next_preset_name()
        self.recorder.save_events(preset_name_with_path)
        preset_name = os.path.basename(preset_name_with_path)
        self.log_handler(f"Session saved as {preset_name}")
        self.config.last_saved_preset = preset_name

    def load_presets(self):
        self.preset_list.delete(0, tk.END)
        all_presets = self.config.list_presets()
        
        pinned_list = sorted([p for p in all_presets if p in self.pinned_presets])
        unpinned_list = [p for p in all_presets if p not in self.pinned_presets]
        
        for p in pinned_list:
            self.preset_list.insert(tk.END, f"📌 {p}")
        
        if pinned_list and unpinned_list:
            self.preset_list.insert(tk.END, "------------------------")

        for p in unpinned_list:
            self.preset_list.insert(tk.END, p)
            
    def auto_load_last_preset(self):
        if self.preset_list.size() > 0:
            first_item = self.preset_list.get(0)
            if "----" not in first_item:
                raw_preset_name = first_item.lstrip('📌 ')
                full_path = self.config.get_preset_path(raw_preset_name)
                self.recorder.load_events(full_path)
                self.preset_list.selection_set(0)
                self.preset_list.see(0)

    def on_preset_single_click(self, event):
        selection_index = self.preset_list.curselection()
        if not selection_index: return
        
        selected_item = self.preset_list.get(selection_index[0])
        if "----" in selected_item: return

        raw_preset_name = selected_item.lstrip('📌 ')
        full_path = self.config.get_preset_path(raw_preset_name)
        self.recorder.load_events(full_path)

    def on_preset_double_click(self, event):
        selection_index = self.preset_list.curselection()
        if not selection_index: return

        selected_item = self.preset_list.get(selection_index[0])
        if "----" in selected_item: return
        
        raw_preset_name = selected_item.lstrip('📌 ')
        self.config.open_preset_in_notepad(raw_preset_name)

    def rename_preset(self, event):
        selection_index = self.preset_list.curselection()
        if not selection_index: return
        selected_item = self.preset_list.get(selection_index[0])
        if "----" in selected_item: return

        old_name = selected_item.lstrip('📌 ')
        initial_name = os.path.splitext(old_name)[0]
        new_name = simpledialog.askstring("Rename Preset", "Enter new name:", initialvalue=initial_name)

        if new_name and new_name != initial_name:
            if self.config.rename_preset(old_name, new_name):
                if old_name in self.pinned_presets:
                    self.pinned_presets.remove(old_name)
                    self.pinned_presets.add(f"{new_name}.json")
                    self.config.save_pinned_presets(list(self.pinned_presets))
                self.load_presets()
            else:
                messagebox.showerror("Error", f"Could not rename preset.")

    def delete_preset(self, event):
        selection_index = self.preset_list.curselection()
        if not selection_index: return
        
        selected_item = self.preset_list.get(selection_index[0])
        if "----" in selected_item: return

        preset_name = selected_item.lstrip('📌 ')
        if messagebox.askyesno("Delete Preset", f"Delete {preset_name}?"):
            self.config.delete_preset(preset_name)
            self.pinned_presets.discard(preset_name)
            self.config.save_pinned_presets(list(self.pinned_presets))
            self.load_presets()
            self.recorder.clear_events()
            
    # --- Restored Function ---
    def load_config(self):
        """Loads window geometry from the config file."""
        geometry = self.config.load_geometry()
        if geometry:
            self.root.geometry(geometry)

    def exit_app(self):
        self.recorder.stop_playback()
        self.on_closing()

    def on_closing(self):
        self.config.save_geometry(self.root.geometry())
        if self.recorder.get_events() and not self.recorder.is_recording and not self.recorder.is_playing:
             self.recorder.save_events(self.config.get_last_session_preset_name())
        self.root.destroy()
        os._exit(0) 

if __name__ == "__main__":
    root = tk.Tk()
    app = SuClickApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()