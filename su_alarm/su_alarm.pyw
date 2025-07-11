#!/usr/bin/env python3
"""
Su Alarm - Simple Alarm and Task Scheduler
A GUI application for managing alarms and tasks with pastel color notifications.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import threading
import time
import os

# Check for required dependencies
try:
    from alarm_config import AlarmConfig
    from alarm_storage import AlarmStorage
except ImportError as e:
    messagebox.showerror("Missing Dependency", 
                        f"Required module not found: {e}\n\n"
                        "Please ensure all files are in the same directory:\n"
                        "- alarm.pyw\n- alarm_config.py\n- alarm_storage.py")
    exit(1)

class AlarmApp:
    VERSION = "1.0.0"
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"Su Alarm v{self.VERSION}")
        self.config = AlarmConfig()
        self.storage = AlarmStorage()
        
        # Set initial geometry
        self.root.geometry(self.config.get('window_geometry', '600x500'))
        
        # Initialize variables
        self.alarm_monitor_thread = None
        self.monitor_running = False
        self.alarm_windows = {}  # Track open alarm notification windows
        
        self.setup_ui()
        self.refresh_alarm_list()
        self.start_alarm_monitor()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup the main user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Su Alarm", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Add task button
        add_btn = ttk.Button(buttons_frame, text="Add Task", command=self.add_task)
        add_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Edit task button
        edit_btn = ttk.Button(buttons_frame, text="Edit Task", command=self.edit_task)
        edit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Delete task button
        delete_btn = ttk.Button(buttons_frame, text="Delete Task", command=self.delete_task)
        delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Refresh button
        refresh_btn = ttk.Button(buttons_frame, text="Refresh", command=self.refresh_alarm_list)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Alarm list frame
        list_frame = ttk.LabelFrame(main_frame, text="Scheduled Alarms", padding="5")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for alarm list
        columns = ('ID', 'Title', 'Date & Time', 'Status', 'Description')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define column headings and widths
        self.tree.heading('ID', text='ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Date & Time', text='Date & Time')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Description', text='Description')
        
        self.tree.column('ID', width=50)
        self.tree.column('Title', width=150)
        self.tree.column('Date & Time', width=150)
        self.tree.column('Status', width=80)
        self.tree.column('Description', width=200)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def add_task(self):
        """Open dialog to add a new task."""
        dialog = TaskDialog(self.root, "Add Task")
        if dialog.result:
            title, description, date_time = dialog.result
            self.storage.add_alarm(title, description, date_time)
            self.refresh_alarm_list()
            self.status_var.set(f"Added task: {title}")
    
    def edit_task(self):
        """Edit the selected task."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a task to edit.")
            return
        
        item = self.tree.item(selected[0])
        alarm_id = int(item['values'][0])
        alarm = self.storage.get_alarm(alarm_id)
        
        if not alarm:
            messagebox.showerror("Error", "Task not found.")
            return
        
        dialog = TaskDialog(self.root, "Edit Task", alarm)
        if dialog.result:
            title, description, date_time = dialog.result
            self.storage.update_alarm(alarm_id, title=title, description=description, date_time=date_time)
            self.refresh_alarm_list()
            self.status_var.set(f"Updated task: {title}")
    
    def delete_task(self):
        """Delete the selected task."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a task to delete.")
            return
        
        item = self.tree.item(selected[0])
        alarm_id = int(item['values'][0])
        title = item['values'][1]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{title}'?"):
            self.storage.delete_alarm(alarm_id)
            self.refresh_alarm_list()
            self.status_var.set(f"Deleted task: {title}")
    
    def refresh_alarm_list(self):
        """Refresh the alarm list display."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add alarms to the tree
        for alarm in self.storage.get_all_alarms():
            status = "Active" if alarm['enabled'] and not alarm['triggered'] else "Inactive"
            if alarm['triggered']:
                status = "Completed"
            
            self.tree.insert('', tk.END, values=(
                alarm['id'],
                alarm['title'],
                alarm['date_time'],
                status,
                alarm['description']
            ))
        
        self.status_var.set(f"Loaded {len(self.storage.get_all_alarms())} tasks")
    
    def start_alarm_monitor(self):
        """Start the alarm monitoring thread."""
        if not self.monitor_running:
            self.monitor_running = True
            self.alarm_monitor_thread = threading.Thread(target=self.monitor_alarms, daemon=True)
            self.alarm_monitor_thread.start()
    
    def monitor_alarms(self):
        """Monitor alarms in a separate thread."""
        while self.monitor_running:
            try:
                current_time = datetime.now()
                pending_alarms = self.storage.get_pending_alarms()
                
                for alarm in pending_alarms:
                    alarm_time = datetime.fromisoformat(alarm['date_time'])
                    if current_time >= alarm_time:
                        self.trigger_alarm(alarm)
                
                time.sleep(1)  # Check every second
            except Exception as e:
                print(f"Error in alarm monitor: {e}")
                time.sleep(5)  # Wait longer on error
    
    def trigger_alarm(self, alarm):
        """Trigger an alarm notification."""
        # Mark alarm as triggered
        self.storage.update_alarm(alarm['id'], triggered=True)
        
        # Create notification window
        self.root.after(0, lambda: self.show_alarm_notification(alarm))
        
        # Refresh the list in the main thread
        self.root.after(0, self.refresh_alarm_list)
    
    def show_alarm_notification(self, alarm):
        """Show pastel color alarm notification."""
        alarm_id = alarm['id']
        
        # Don't show duplicate notifications
        if alarm_id in self.alarm_windows:
            return
        
        # Create notification window
        notification = tk.Toplevel(self.root)
        notification.title(f"Alarm: {alarm['title']}")
        notification.geometry("400x200")
        notification.resizable(False, False)
        
        # Make window stay on top
        notification.attributes('-topmost', True)
        
        # Center the window
        notification.eval('tk::PlaceWindow . center')
        
        # Configure pastel colors
        colors = self.config.get('pastel_colors', {})
        bg_color = colors.get('background', '#FFF8E1')
        text_color = colors.get('text', '#FF6B6B')
        accent_color = colors.get('accent', '#4ECDC4')
        
        notification.configure(bg=bg_color)
        
        # Main frame
        main_frame = tk.Frame(notification, bg=bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text=alarm['title'], 
                              font=("Arial", 18, "bold"), 
                              fg=text_color, bg=bg_color)
        title_label.pack(pady=(0, 10))
        
        # Description
        if alarm['description']:
            desc_label = tk.Label(main_frame, text=alarm['description'], 
                                 font=("Arial", 12), 
                                 fg=text_color, bg=bg_color,
                                 wraplength=350)
            desc_label.pack(pady=(0, 10))
        
        # Time info
        time_label = tk.Label(main_frame, text=f"Scheduled for: {alarm['date_time']}", 
                             font=("Arial", 10), 
                             fg=text_color, bg=bg_color)
        time_label.pack(pady=(0, 20))
        
        # Dismiss button
        dismiss_btn = tk.Button(main_frame, text="Dismiss", 
                               command=lambda: self.dismiss_alarm(alarm_id, notification),
                               bg=accent_color, fg='white', 
                               font=("Arial", 12, "bold"),
                               relief=tk.RAISED, bd=2)
        dismiss_btn.pack()
        
        # Store reference to window
        self.alarm_windows[alarm_id] = notification
        
        # Auto-dismiss after configured duration
        duration = self.config.get('notification_duration', 30) * 1000
        notification.after(duration, lambda: self.dismiss_alarm(alarm_id, notification))
    
    def dismiss_alarm(self, alarm_id, notification):
        """Dismiss an alarm notification."""
        if alarm_id in self.alarm_windows:
            del self.alarm_windows[alarm_id]
        
        try:
            notification.destroy()
        except:
            pass  # Window might already be destroyed
    
    def on_closing(self):
        """Handle application closing."""
        # Save window geometry
        self.config.set('window_geometry', self.root.geometry())
        
        # Stop alarm monitor
        self.monitor_running = False
        if self.alarm_monitor_thread:
            self.alarm_monitor_thread.join(timeout=2)
        
        # Close all alarm windows
        for notification in self.alarm_windows.values():
            try:
                notification.destroy()
            except:
                pass
        
        self.root.destroy()


class TaskDialog:
    """Dialog for adding/editing tasks."""
    
    def __init__(self, parent, title, alarm=None):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.eval('tk::PlaceWindow . center')
        
        # Create form
        self.create_form(alarm)
        
        # Focus on title entry
        self.title_entry.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def create_form(self, alarm):
        """Create the task form."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title field
        ttk.Label(main_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.title_entry = ttk.Entry(main_frame, width=40)
        self.title_entry.grid(row=0, column=1, pady=(0, 5))
        
        # Description field
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.desc_text = tk.Text(main_frame, width=40, height=4)
        self.desc_text.grid(row=1, column=1, pady=(0, 5))
        
        # Date and time fields
        ttk.Label(main_frame, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.date_entry = ttk.Entry(main_frame, width=40)
        self.date_entry.grid(row=2, column=1, pady=(0, 5))
        
        ttk.Label(main_frame, text="Time (HH:MM):").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.time_entry = ttk.Entry(main_frame, width=40)
        self.time_entry.grid(row=3, column=1, pady=(0, 5))
        
        # Fill in existing data if editing
        if alarm:
            self.title_entry.insert(0, alarm['title'])
            self.desc_text.insert(tk.END, alarm['description'])
            
            # Parse date and time
            try:
                dt = datetime.fromisoformat(alarm['date_time'])
                self.date_entry.insert(0, dt.strftime('%Y-%m-%d'))
                self.time_entry.insert(0, dt.strftime('%H:%M'))
            except:
                pass
        else:
            # Default to current date and time + 1 hour
            default_dt = datetime.now() + timedelta(hours=1)
            self.date_entry.insert(0, default_dt.strftime('%Y-%m-%d'))
            self.time_entry.insert(0, default_dt.strftime('%H:%M'))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="Save", command=self.save_task).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
    
    def save_task(self):
        """Save the task."""
        title = self.title_entry.get().strip()
        description = self.desc_text.get(1.0, tk.END).strip()
        date_str = self.date_entry.get().strip()
        time_str = self.time_entry.get().strip()
        
        if not title:
            messagebox.showerror("Error", "Title is required.")
            return
        
        if not date_str or not time_str:
            messagebox.showerror("Error", "Date and time are required.")
            return
        
        try:
            # Parse and validate date/time
            dt = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            date_time_str = dt.isoformat()
            
            # Check if the date/time is in the future
            if dt <= datetime.now():
                messagebox.showwarning("Warning", "The alarm time should be in the future.")
            
            self.result = (title, description, date_time_str)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid date or time format.\nUse YYYY-MM-DD for date and HH:MM for time.")
    
    def cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmApp(root)
    root.mainloop()