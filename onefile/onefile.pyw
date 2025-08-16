# Full-featured PyInstaller GUI onefile builder for Tkinter apps
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import shutil
import threading
import time

# For icon conversion
from PIL import Image

# Pastel yellow for terminal input cursor
PASTEL_YELLOW = "#fff9ae"

def get_tkinter_data_dirs():
    # Returns [(src1, dest1), (src2, dest2)] to be used in --add-data
    tk_root = tk.Tk()
    tk_root.withdraw()
    tcl_dir = tk_root.tk.exprstring('$tcl_library')
    tk_dir = tk_root.tk.exprstring('$tk_library')
    tk_root.destroy()
    return [
        (tcl_dir, 'tcl'),
        (tk_dir, 'tk')
    ]

def png_to_ico(png_path):
    # Convert PNG to multi-size ICO for Windows compatibility
    import tempfile
    im = Image.open(png_path).convert('RGBA')
    icon_sizes = [(256,256), (128,128), (64,64), (48,48), (32,32), (24,24), (16,16)]
    images = [im.resize(size, Image.LANCZOS) for size in icon_sizes]
    ico_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.ico')
    ico_file = ico_temp.name
    ico_temp.close()
    images[0].save(ico_file, format='ICO', sizes=icon_sizes)
    return ico_file

def select_file():
    filepath = filedialog.askopenfilename(
        filetypes=[("Python Files", "*.py;*.pyw")],
        title="Select a Python script"
    )
    if filepath:
        entry_file.delete(0, tk.END)
        entry_file.insert(0, filepath)
        os.chdir(os.path.dirname(filepath))
        update_terminal_prompt()

def set_status(text, color):
    status_line.config(text=text, fg=color)

def select_add_data():
    paths = filedialog.askopenfilenames(
        title="Select data files/folders to add (Ctrl+Click for multiple)"
    )
    if not paths:
        return
    data_strs = []
    for path in paths:
        rel_path = os.path.relpath(path, os.getcwd())
        data_strs.append(f'{rel_path};.')
    entry_add_data.delete(0, tk.END)
    entry_add_data.insert(0, '|'.join(data_strs))

def select_icon():
    # Allow user to select .ico/.png file (first filter is All Supported)
    filetypes = [
        ("All Supported", "*.ico;*.png"),
        ("Icon Files", "*.ico"),
        ("PNG Files", "*.png"),
        ("All Files", "*.*")
    ]
    icon_path = filedialog.askopenfilename(
        filetypes=filetypes,
        title="Select icon file for EXE"
    )
    if icon_path:
        ext = os.path.splitext(icon_path)[1].lower()
        if ext == ".png":
            try:
                ico_path = png_to_ico(icon_path)
                entry_icon.delete(0, tk.END)
                entry_icon.insert(0, ico_path)
                if hasattr(entry_icon, 'icopath'):
                    del entry_icon.icopath
                icon_option.set("custom")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to convert PNG to ICO: {e}")
        elif ext == ".ico":
            entry_icon.delete(0, tk.END)
            entry_icon.insert(0, icon_path)
            if hasattr(entry_icon, 'icopath'):
                del entry_icon.icopath
            icon_option.set("custom")
        else:
            messagebox.showinfo("Info", "Please select a .ico or .png file.")

def run_build(py_file, add_data, icon_path, use_icon, log_callback, status_callback):
    script_dir = os.path.dirname(py_file)
    script_name = os.path.splitext(os.path.basename(py_file))[0]
    exe_name = script_name + ".exe"
    work_dir = os.path.abspath(script_dir)
    dist_dir = os.path.join(work_dir, "dist")
    build_dir = os.path.join(work_dir, "build")
    spec_dir = work_dir

    for folder in [dist_dir, build_dir]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception:
                time.sleep(1)
                shutil.rmtree(folder)

    # Base command
    cmd_str = f'pyinstaller --onefile --distpath "{dist_dir}" --workpath "{build_dir}" --specpath "{spec_dir}"'

    # Always add Tkinter data folders (for portable .exe)
    try:
        tk_data_pairs = get_tkinter_data_dirs()
        for src, dest in tk_data_pairs:
            cmd_str += f' --add-data "{src};{dest}"'
    except Exception as e:
        log_callback(f"Warning: Could not locate Tkinter data folders: {e}\n")

    # User-supplied icon
    if use_icon and icon_path:
        cmd_str += f' --icon "{icon_path}"'
    # User-supplied add_data
    if add_data:
        for item in add_data.split('|'):
            if ';' in item:
                cmd_str += f' --add-data "{item}"'
    cmd_str += f' "{py_file}"'
    log_callback(f"Running: {cmd_str}\n")

    try:
        process = subprocess.Popen(
            cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in process.stdout:
            log_callback(line)
        process.wait()
        dist_exe_path = os.path.join(dist_dir, exe_name)
        target_exe_path = os.path.join(script_dir, exe_name)
        if process.returncode == 0:
            if os.path.exists(dist_exe_path):
                shutil.copy2(dist_exe_path, target_exe_path)
                status_callback(f"Build completed! EXE copied to: {target_exe_path}", "blue")
            else:
                status_callback(f"Error: EXE not found in dist folder: {dist_exe_path}", "red")
        else:
            status_callback("Build failed. See terminal.", "red")
    except Exception as e:
        status_callback(f"Exception: {e}", "red")
    finally:
        try:
            if os.path.exists(dist_dir):
                shutil.rmtree(dist_dir)
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
            spec_file = os.path.join(spec_dir, script_name + ".spec")
            if os.path.isfile(spec_file):
                os.remove(spec_file)
        except Exception as e:
            status_callback(f"Warning: Could not delete temp files ({e})", "orange")

def build_exe():
    py_file = entry_file.get()
    add_data = entry_add_data.get()
    icon_path = entry_icon.get()
    use_icon = bool(icon_path)
    if not py_file or not os.path.exists(py_file):
        set_status("Please select a valid Python script.", "red")
        return

    btn_build.config(state="disabled")
    btn_select.config(state="disabled")
    btn_add_data.config(state="disabled")
    btn_icon_select.config(state="disabled")
    set_status("Building...", "black")

    def log_callback(line):
        terminal_text.config(state="normal")
        insert_terminal_output(line)
        terminal_text.config(state="disabled")

    def status_callback(text, color):
        btn_build.config(state="normal")
        btn_select.config(state="normal")
        btn_add_data.config(state="normal")
        btn_icon_select.config(state="normal")
        set_status(text, color)

    thread = threading.Thread(
        target=run_build,
        args=(py_file, add_data, icon_path, use_icon, log_callback, status_callback),
        daemon=True
    )
    thread.start()

def insert_terminal_output(line):
    timestr = time.strftime('%H:%M:%S')
    cwd = os.getcwd()
    prompt = f"[{timestr}] [{cwd}]\n"
    terminal_text.insert(tk.END, prompt)
    terminal_text.insert(tk.END, line)
    terminal_text.see(tk.END)

def update_terminal_prompt():
    terminal_text.config(state="normal")
    timestr = time.strftime('%H:%M:%S')
    cwd = os.getcwd()
    terminal_text.delete("1.0", tk.END)
    terminal_text.insert(tk.END, f"[{timestr}] [{cwd}]\n")
    help_msg = (
    "uv install pyinstaller pywin32 pillow\n"
        "Icon: .ico/.png supported (PNG auto-converts).\n"
        "─────────────────────────────────────────────\n"
    )
    terminal_text.insert(tk.END, help_msg)
    terminal_text.config(state="disabled")
    terminal_text.see(tk.END)

def get_terminal_input():
    return terminal_input.get("1.0", tk.END).strip()

def run_terminal_command(event=None):
    cmd = get_terminal_input()
    if not cmd:
        return
    terminal_text.config(state="normal")
    timestr = time.strftime('%H:%M:%S')
    cwd = os.getcwd()
    terminal_text.insert(tk.END, f"[{timestr}] [{cwd}]\n> {cmd}\n")
    terminal_text.config(state="disabled")
    terminal_text.see(tk.END)
    terminal_input.delete("1.0", tk.END)
    def do_run():
        try:
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd()
            )
            for line in process.stdout:
                terminal_text.config(state="normal")
                terminal_text.insert(tk.END, line)
                terminal_text.see(tk.END)
                terminal_text.config(state="disabled")
            process.wait()
            update_terminal_prompt()
        except Exception as e:
            terminal_text.config(state="normal")
            terminal_text.insert(tk.END, f"Exception: {e}\n")
            terminal_text.config(state="disabled")
            terminal_text.see(tk.END)
    threading.Thread(target=do_run, daemon=True).start()

root = tk.Tk()
root.title("Su_Onefile_Builder")
root.geometry("850x600")
root.minsize(650, 380)

BUTTON_WIDTH = 10
ENTRY_HEIGHT = 1
ENTRY_WIDTH_SCRIPT = 36
ENTRY_WIDTH_DATA = 38
ENTRY_WIDTH_ICON = 30

root.grid_rowconfigure(2, weight=0)
root.grid_rowconfigure(3, weight=1)
root.grid_columnconfigure(0, weight=1)

frame_script = tk.Frame(root)
frame_script.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
frame_script.grid_columnconfigure(1, weight=1)

btn_select = tk.Button(frame_script, text="Script", width=BUTTON_WIDTH, height=ENTRY_HEIGHT, command=select_file)
btn_select.grid(row=0, column=0, sticky="w", padx=(0,4))

entry_file = tk.Entry(frame_script, width=ENTRY_WIDTH_SCRIPT)
entry_file.grid(row=0, column=1, padx=4, ipady=3, sticky="ew")

frame_add = tk.Frame(root)
frame_add.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))
frame_add.grid_columnconfigure(1, weight=1)

btn_add_data = tk.Button(frame_add, text="AddData", width=BUTTON_WIDTH, height=ENTRY_HEIGHT, command=select_add_data)
btn_add_data.grid(row=0, column=0, sticky="w", padx=(0,4))

entry_add_data = tk.Entry(frame_add, width=ENTRY_WIDTH_DATA)
entry_add_data.grid(row=0, column=1, padx=4, ipady=3, sticky="ew")

frame_icon = tk.Frame(root)
frame_icon.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))
frame_icon.grid_columnconfigure(1, weight=1)
frame_icon.grid_columnconfigure(2, weight=0)
frame_icon.grid_columnconfigure(3, weight=0)

btn_icon_select = tk.Button(frame_icon, text="Icon", width=BUTTON_WIDTH, height=ENTRY_HEIGHT, command=select_icon)
btn_icon_select.grid(row=0, column=0, sticky="w", padx=(0,4))

entry_icon = tk.Entry(frame_icon, width=ENTRY_WIDTH_ICON)
entry_icon.grid(row=0, column=1, padx=4, ipady=3, sticky="ew")

icon_option = tk.StringVar(value="custom")

def update_icon_entry_bg(*args):
    entry_icon.config(bg="#fffde0")
icon_option.trace("w", update_icon_entry_bg)
update_icon_entry_bg()

frame_bottom = tk.Frame(root)
frame_bottom.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 3))
frame_bottom.grid_columnconfigure(0, weight=1)
frame_bottom.grid_columnconfigure(1, weight=0)

status_line = tk.Label(root, text="", anchor="w", font=("Arial", 10, "bold"))
status_line.grid(row=4, column=0, sticky="ew", padx=10, pady=(2, 2))

btn_build = tk.Button(frame_bottom, text="Build", width=BUTTON_WIDTH, height=ENTRY_HEIGHT, command=build_exe)
btn_build.grid(row=0, column=1, sticky="e")

terminal_label = tk.Label(root, text="Terminal Output:")
terminal_label.grid(row=5, column=0, sticky="w", padx=12, pady=(6, 0))

terminal_text = tk.Text(
    root,
    height=11,
    width=70,
    state="disabled",
    bg="#657A7B",
    fg="#ffffff",
    insertbackground="#5FA85F",
    font=("Consolas", 11)
)
terminal_text.grid(row=6, column=0, padx=10, pady=(0, 0), sticky="nsew")

terminal_input_frame = tk.Frame(root)
terminal_input_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))
terminal_input_frame.grid_columnconfigure(0, weight=1)
terminal_input = tk.Text(
    terminal_input_frame,
    font=("Consolas", 12),
    bg="#95BFC1",
    fg="#ffffff",
    insertbackground=PASTEL_YELLOW,
    height=2,
    wrap="word"
)
terminal_input.grid(row=0, column=0, sticky="ew", ipady=2)

def terminal_input_enter(event=None):
    if event is not None and event.state & 0x0001:
        return
    run_terminal_command()
    return "break"
terminal_input.bind('<Return>', terminal_input_enter)

terminal_send_btn = tk.Button(
    terminal_input_frame, text="Send", command=run_terminal_command, width=7
)
terminal_send_btn.grid(row=0, column=1, padx=(6,0))

root.grid_rowconfigure(6, weight=2)
root.grid_rowconfigure(4, weight=0)
root.grid_columnconfigure(0, weight=1)

def on_resize(event):
    frame_script.grid_columnconfigure(1, weight=1)
    frame_add.grid_columnconfigure(1, weight=1)
    frame_icon.grid_columnconfigure(1, weight=1)
    frame_bottom.grid_columnconfigure(0, weight=1)
    frame_bottom.grid_columnconfigure(1, weight=0)
    terminal_input_frame.grid_columnconfigure(0, weight=1)

root.bind('<Configure>', on_resize)
update_terminal_prompt()
root.mainloop()
