#!/usr/bin/env python3
"""
Updated: 2025-07-10 - Increased window height for better content visibility
Su Tools Launcher
A simple menu to launch any of the Su tools.
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

class SuLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Su Tools Launcher")
        self.root.geometry("450x450")  # Increased height from 300 to 450
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_label = tk.Label(self.root, text="Su Tools", 
                              font=("Arial", 18, "bold"), pady=10)
        title_label.pack()
        
        subtitle_label = tk.Label(self.root, text="Choose a tool to launch:", 
                                 font=("Arial", 10), pady=5)
        subtitle_label.pack()
        
        # Tools frame
        tools_frame = tk.Frame(self.root)
        tools_frame.pack(expand=True, fill="both", padx=20, pady=10)
        
        # Tool buttons
        tools = [
            ("🔧 Su_Onefile_Builder", "PyInstaller GUI for creating executables", 
             lambda: self.launch_tool("onefile/onefile.pyw")),
            ("💬 Su_Chat", "GPT-4 chatbot with session management", 
             lambda: self.launch_tool("su_chat/su_chat.pyw")),
            ("🎮 Su_Click", "Mouse & keyboard automation tool", 
             lambda: self.launch_tool("su_click/su_click.pyw")),
            ("⏰ Su_Alarm", "Alarm app with task scheduling and pastel notifications", 
             lambda: self.launch_tool("alarm/alarm.pyw"))
        ]
        
        for i, (title, desc, command) in enumerate(tools):
            # Tool button
            btn = tk.Button(tools_frame, text=title, command=command,
                           font=("Arial", 12, "bold"), pady=8,
                           width=30, relief="raised", bd=2)
            btn.grid(row=i*2, column=0, pady=(5, 2), sticky="ew")
            
            # Description
            desc_label = tk.Label(tools_frame, text=desc, 
                                 font=("Arial", 9), fg="gray")
            desc_label.grid(row=i*2+1, column=0, pady=(0, 10))
        
        tools_frame.grid_columnconfigure(0, weight=1)
        
        # Bottom frame
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill="x", padx=20, pady=15)  # Increased padding
        
        # Help and exit buttons
        help_btn = tk.Button(bottom_frame, text="Help & Documentation", 
                           command=self.show_help, width=20)
        help_btn.pack(side="left")
        
        exit_btn = tk.Button(bottom_frame, text="Exit", 
                           command=self.root.quit, width=10)
        exit_btn.pack(side="right")
    
    def launch_tool(self, script_path):
        if not os.path.exists(script_path):
            messagebox.showerror("File Not Found", 
                               f"Could not find {script_path}\n\n"
                               "Please ensure all files are in the correct directories.")
            return
        
        try:
            # Launch the tool in a new process
            subprocess.Popen([sys.executable, script_path], 
                           cwd=os.path.dirname(script_path) or ".")
            messagebox.showinfo("Launched", f"Started {os.path.basename(script_path)}")
        except Exception as e:
            messagebox.showerror("Launch Error", 
                               f"Failed to launch {script_path}:\n\n{str(e)}")
    
    def show_help(self):
        help_text = """Su Tools Collection

Available Tools:
• Su_Onefile_Builder: Create executable files from Python scripts
• Su_Chat: AI chatbot powered by GPT-4
• Su_Click: Record and replay mouse/keyboard actions
• Su_Alarm: Task scheduling with pastel color notifications

Documentation:
• README.md: Complete feature overview
• EXAMPLES.md: Usage examples and tutorials
• requirements.txt: Python dependencies

Quick Setup:
1. Install dependencies: pip install -r requirements.txt
2. For Su_Chat: Create 'ak' file with your OpenAI API key
3. Launch tools from this menu or run directly

Visit the GitHub repository for more information.
"""
        messagebox.showinfo("Su Tools Help", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = SuLauncher(root)
    root.mainloop()