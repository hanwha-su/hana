# env_gui_manager_refactored.py
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import winreg
import ctypes
import sys
import os
import json
import logging
import re


# --- Configuration & Constants ---
CONFIG_FILE = "config.json"
DEFAULT_GEOMETRY = "950x900"

# --- Logging Setup ---
def setup_logging():
    """Configures the logging format and level."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    date_format = "%m-%d %H:%M:%S"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt=date_format)


# --- Backend Logic (Interacting with Windows Registry) ---
def is_admin():
    """Checks if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"Failed to check admin status: {e}")
        return False


def _get_registry_info(scope):
    """Returns the appropriate registry key and subkey based on the scope."""
    if scope == 'user':
        return winreg.HKEY_CURRENT_USER, r'Environment'
    elif scope == 'system':
        return (
            winreg.HKEY_LOCAL_MACHINE,
            r'System\CurrentControlSet\Control\Session Manager\Environment',
        )
    else:
        raise ValueError("Invalid scope specified. Must be 'user' or 'system'.")


def get_variables(scope):
    """
    Retrieves environment variables from the specified scope.

    Args:
        scope (str): 'user' or 'system'.

    Returns:
        dict: A dictionary of variables {name: (value, type)}.
    """
    variables = {}
    try:
        key, subkey = _get_registry_info(scope)
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_READ) as r_key:
            i = 0
            while True:
                try:
                    name, value, reg_type = winreg.EnumValue(r_key, i)
                    variables[name] = (value, reg_type)
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        logging.warning(
            f"Registry key for '{scope}' scope not found. It might not exist yet."
        )
    except Exception as e:
        logging.error(f"Failed to get variables for '{scope}' scope: {e}")
    return variables


def set_variable(scope, name, value, reg_type=None):
    """
    Sets or creates an environment variable.

    Args:
        scope (str): 'user' or 'system'.
        name (str): The name of the variable.
        value (str): The value of the variable.
        reg_type (int, optional): The registry type. Defaults to REG_SZ or
                                  REG_EXPAND_SZ for PATH.

    Returns:
        bool: True on success, False on failure.
    """
    if scope == 'system' and not is_admin():
        logging.error("Administrator rights required to modify system variables.")
        return False, "Administrator rights required"

    if name.lower() == 'path':
        final_reg_type = winreg.REG_EXPAND_SZ
    elif reg_type is not None:
        final_reg_type = reg_type
    else:
        final_reg_type = winreg.REG_SZ

    try:
        key, subkey = _get_registry_info(scope)
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE) as r_key:
            winreg.SetValueEx(r_key, name, 0, final_reg_type, value)
        # Notify other processes of the change
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x1A, 0, 0, 0x2, 1000, None
        )
        logging.info(f"Successfully set variable '{name}' in '{scope}' scope.")
        return True, ""
    except Exception as e:
        logging.error(f"Error setting variable '{name}': {e}")
        return False, str(e)


def delete_variable(scope, name):
    """
    Deletes an environment variable.

    Args:
        scope (str): 'user' or 'system'.
        name (str): The name of the variable to delete.

    Returns:
        bool: True on success, False on failure.
    """
    if scope == 'system' and not is_admin():
        logging.error("Administrator rights required to delete system variables.")
        return False, "Administrator rights required"

    try:
        key, subkey = _get_registry_info(scope)
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE) as r_key:
            winreg.DeleteValue(r_key, name)
        # Notify other processes of the change
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x1A, 0, 0, 0x2, 1000, None
        )
        logging.info(f"Successfully deleted variable '{name}' from '{scope}' scope.")
        return True, ""
    except Exception as e:
        logging.error(f"Error deleting variable '{name}': {e}")
        return False, str(e)


# --- GUI Application ---
class EnvManagerApp(tk.Tk):
    """
    A GUI application for managing Windows environment variables.
    It allows viewing, editing, adding, deleting, and batch import/export.
    """

    def __init__(self):
        super().__init__()
        self.config = self._load_config()

        self.title("Environment Variable Manager")
        self.geometry(self.config.get("geometry", DEFAULT_GEOMETRY))

        self.current_scope = tk.StringVar(value="user")
        self.variables = {}
        self.selected_variable_name = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._create_widgets()
        self.on_scope_change()
        logging.info("Application initialized successfully.")
        if self.current_scope.get() == 'system' and not is_admin():
            self.update_status(
                "Warning: Running without admin rights. System vars are read-only.",
                'orange',
                duration=0,
            )

    def _load_config(self):
        """Loads GUI configuration from a JSON file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    logging.info(f"Loading configuration from {CONFIG_FILE}")
                    return json.load(f)
        except Exception as e:
            logging.error(f"Could not load or parse {CONFIG_FILE}: {e}")
        return {}

    def _save_config(self):
        """Saves the current GUI configuration to a JSON file."""
        try:
            config_data = {"geometry": self.geometry()}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            logging.info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")

    def _create_widgets(self):
        """Creates and arranges all the widgets in the main window."""
        # Top Frame: Scope Selection
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 0))
        top_frame.grid(row=0, column=0, sticky="ew")
        scope_frame = ttk.LabelFrame(top_frame, text="Scope", padding=5)
        scope_frame.pack(side=tk.LEFT)
        ttk.Radiobutton(
            scope_frame, text="User", var=self.current_scope, value="user",
            command=self.on_scope_change
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            scope_frame, text="System", var=self.current_scope, value="system",
            command=self.on_scope_change
        ).pack(side=tk.LEFT)

        # Treeview Frame: Variable List
        tree_frame = ttk.Frame(self, padding=(10, 5, 10, 0))
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_frame, columns=("Name", "Value"), show="headings"
        )
        self.tree.heading("Name", text="Name")
        self.tree.heading("Value", text="Value")
        self.tree.column("Name", width=300, stretch=tk.NO)
        self.tree.column("Value", width=600)

        # Configure a tag for highlighting the Path variable
        self.tree.tag_configure('path_row', background='#FFFFE0') # Pastel yellow

        tree_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.config(yscrollcommand=tree_scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Edit Panel: Value Editor
        self.edit_panel = ttk.LabelFrame(self, text="View / Edit Value", padding=10)
        self.edit_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        self.edit_panel.grid_rowconfigure(0, weight=1)
        self.edit_panel.grid_columnconfigure(0, weight=1)
        self.edit_text = tk.Text(self.edit_panel, wrap="word", height=15)
        self.edit_text.grid(row=0, column=0, sticky="nsew", columnspan=2)
        ttk.Button(
            self.edit_panel, text="Save Changes", command=self.save_edited_variable
        ).grid(row=1, column=1, sticky='e', pady=(5, 0))

        # Action Panel: Buttons
        action_panel = ttk.Frame(self, padding=(10, 0, 10, 10))
        action_panel.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            action_panel, text="Add New...", command=self.add_new_variable
        ).pack(side=tk.LEFT)
        self.delete_button = ttk.Button(
            action_panel, text="Delete Selected", command=self.delete_selected_variable
        )
        self.delete_button.pack(side=tk.LEFT, padx=5)
        ttk.Separator(action_panel, orient="vertical").pack(
            side=tk.LEFT, padx=(10, 5), fill='y'
        )
        ttk.Button(
            action_panel, text="Import from JSON...", command=self.import_from_json
        ).pack(side=tk.LEFT)
        ttk.Button(
            action_panel, text="Export to JSON...", command=self.export_to_json
        ).pack(side=tk.LEFT, padx=5)

        # Status Bar
        self.status_bar_text = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self, textvariable=self.status_bar_text, relief=tk.SUNKEN, anchor='w',
            padding=5
        )
        self.status_bar.grid(row=4, column=0, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle window closing event to save configuration."""
        self._save_config()
        self.destroy()

    def on_scope_change(self):
        """Handles the event when the user switches scope."""
        scope = self.current_scope.get()
        logging.info(f"Scope changed to '{scope}'.")
        self.populate_tree()
        self.clear_edit_panel()
        self.update_status(
            f"Switched to '{scope.capitalize()}' scope.", 'blue', duration=3000
        )
        if scope == 'system' and not is_admin():
            self.update_status(
                "Warning: System variables are read-only without admin rights.",
                'orange',
                duration=5000,
            )

    def populate_tree(self):
        """Fetches and displays the environment variables in the treeview."""
        selection_id = self.tree.selection()[0] if self.tree.selection() else None

        self.tree.delete(*self.tree.get_children())
        self.variables = get_variables(self.current_scope.get())

        for name, (value, reg_type) in sorted(self.variables.items()):
            tags = ()
            if name.lower() == 'path':
                tags = ('path_row',)
            self.tree.insert("", "end", iid=name, values=(name, value), tags=tags)

        if selection_id and self.tree.exists(selection_id):
            self.tree.selection_set(selection_id)
            self.tree.focus(selection_id)
            self.tree.see(selection_id)
        else:
            self.clear_edit_panel()

    def on_tree_select(self, event=None):
        """Handles the event when a variable is selected in the treeview."""
        if not self.tree.selection():
            self.clear_edit_panel()
            return

        self.selected_variable_name = self.tree.selection()[0]
        value, reg_type = self.variables[self.selected_variable_name]

        display_value = (
            value.replace(';', ';\n')
            if self.selected_variable_name.lower() == 'path'
            else value
        )

        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", display_value)
        self.edit_panel.config(text=f"View / Edit: {self.selected_variable_name}")
        logging.debug(f"Selected variable: '{self.selected_variable_name}'")

    def clear_edit_panel(self):
        """Clears the selection and the edit panel."""
        self.selected_variable_name = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.edit_text.delete("1.0", tk.END)
        self.edit_panel.config(text="View / Edit Value")

    def _convert_to_relative_paths(self, value):
        """
        Converts absolute paths in a string to their relative environment
        variable equivalents (e.g., %USERPROFILE%).

        Returns:
            tuple: (processed_string, was_expanded_boolean)
        """
        processed_value = value
        was_expanded = False

        well_known_vars = {
            'ProgramFiles(x86)': '%ProgramFiles(x86)%',
            'CommonProgramFiles(x86)': '%CommonProgramFiles(x86)%',
            'ProgramFiles': '%ProgramFiles%',
            'CommonProgramFiles': '%CommonProgramFiles%',
            'SystemRoot': '%SystemRoot%',
            'windir': '%windir%',
        }

        path_map = {}
        for var, var_name in well_known_vars.items():
            path = os.environ.get(var)
            if path:
                path_map[path] = var_name

        path_map[os.path.expanduser('~')] = '%USERPROFILE%'

        # Sort by length of the absolute path so longer, more specific
        # paths are replaced before shorter ones (avoid partial matches).
        for abs_path, var_name in sorted(
            path_map.items(), key=lambda item: len(item[0]), reverse=True
        ):
            path_bs = abs_path.replace('/', '\\')
            path_fs = abs_path.replace('\\', '/')

            if (path_bs.lower() in processed_value.lower() or
                    path_fs.lower() in processed_value.lower()):

                processed_value = re.sub(
                    re.escape(path_fs), var_name, processed_value, flags=re.IGNORECASE
                )
                processed_value = re.sub(
                    re.escape(path_bs), var_name, processed_value, flags=re.IGNORECASE
                )
                was_expanded = True

        return processed_value, was_expanded

    def save_edited_variable(self):
        """Saves changes from the edit panel to the registry."""
        if not self.selected_variable_name:
            self.update_status("No variable selected to save.", "orange")
            return

        raw_value = self.edit_text.get("1.0", "end-1c")
        original_reg_type = self.variables[self.selected_variable_name][1]

        processed_value, was_expanded = self._convert_to_relative_paths(raw_value)

        new_reg_type = (
            winreg.REG_EXPAND_SZ if was_expanded else original_reg_type
        )

        if self.selected_variable_name.lower() == 'path':
            path_entries = [
                p.strip().strip('"\'')
                for p in processed_value.replace(';\n', ';')
                .replace('\n', ';')
                .split(';')
            ]
            final_value = ";".join(line.rstrip('\\/') for line in path_entries if line)
            new_reg_type = winreg.REG_EXPAND_SZ
        else:
            final_value = processed_value

        success, msg = set_variable(
            self.current_scope.get(),
            self.selected_variable_name,
            final_value,
            new_reg_type,
        )
        if success:
            self.update_status(
                f"Variable '{self.selected_variable_name}' updated.", 'green'
            )
            self.populate_tree()
        else:
            self.update_status(f"Error updating variable: {msg}", 'red')

    def add_new_variable(self):
        """Opens dialogs to add a new environment variable."""
        name = simpledialog.askstring(
            "Add New Variable", "Enter new variable name:", parent=self
        )
        if not name:
            return
        if name in self.variables:
            self.update_status(f"Error: Variable '{name}' already exists.", 'red')
            return

        value = simpledialog.askstring(
            "Add New Variable", f"Enter value for '{name}':", parent=self
        )
        if value is not None:
            success, msg = set_variable(self.current_scope.get(), name, value)
            if success:
                self.update_status(f"Variable '{name}' created.", 'green')
                self.populate_tree()
            else:
                self.update_status(f"Error creating variable: {msg}", 'red')

    def delete_selected_variable(self):
        """Deletes the selected variable with a confirmation step."""
        if "Confirm" in self.delete_button['text']:
            if not self.tree.selection():
                return
            name = self.tree.selection()[0]

            success, msg = delete_variable(self.current_scope.get(), name)
            if success:
                self.update_status(f"Variable '{name}' deleted.", 'green')
                self.populate_tree()
                self.clear_edit_panel()
            else:
                self.update_status(f"Error deleting variable: {msg}", 'red')
            self.delete_button.config(text="Delete Selected")
        else:
            if not self.tree.selection():
                self.update_status("Please select a variable to delete.", "orange")
                return
            self.delete_button.config(text="Confirm Delete?")
            self.update_status(
                "Click again to confirm deletion.", 'orange', duration=4000
            )
            self.after(
                4000,
                lambda: self.delete_button.config(text="Delete Selected")
                if self.delete_button.winfo_exists()
                else None,
            )

    def _get_script_dir(self):
        """Gets the script's dir or the CWD as a fallback."""
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.getcwd()

    def export_to_json(self):
        """Exports the current set of variables to a JSON file."""
        scope = self.current_scope.get()
        filepath = filedialog.asksaveasfilename(
            initialdir=self._get_script_dir(),
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title=f"Export {scope.capitalize()} Variables",
            initialfile=f"{scope}_env_vars_backup.json",
        )
        if not filepath:
            return

        data_to_save = {
            name: {"value": value, "type": reg_type}
            for name, (value, reg_type) in self.variables.items()
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
            self.update_status(
                f"Successfully exported to {os.path.basename(filepath)}", 'green'
            )
            logging.info(f"Exported {len(data_to_save)} variables to {filepath}")
        except Exception as e:
            self.update_status(f"Error exporting file: {e}", 'red')
            logging.error(f"Failed to export JSON file: {e}")

    def import_from_json(self):
        """Imports variables from a JSON file, overwriting existing ones."""
        scope = self.current_scope.get()
        filepath = filedialog.askopenfilename(
            initialdir=self._get_script_dir(),
            filetypes=[("JSON Files", "*.json")],
            title=f"Import for {scope.capitalize()} scope",
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data_to_load = json.load(f)

            if not isinstance(data_to_load, dict):
                raise ValueError("Invalid JSON format. Must be a dict of variables.")

            if messagebox.askyesno(
                "Confirm Import",
                f"Found {len(data_to_load)} variables. This will OVERWRITE "
                "existing variables with the same name.\n\nProceed?",
            ):
                logging.info(
                    f"Starting import of {len(data_to_load)} variables from {filepath}"
                )
                success_count, fail_count = 0, 0
                for name, info in data_to_load.items():
                    value = info.get("value", "")
                    reg_type = info.get("type", winreg.REG_SZ)
                    success, _ = set_variable(scope, name, value, reg_type)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1

                self.populate_tree()
                summary_msg = f"{success_count} variables imported successfully."
                if fail_count > 0:
                    summary_msg += f" {fail_count} failed."
                    self.update_status(summary_msg, 'orange')
                else:
                    self.update_status(summary_msg, 'green')
                logging.info(
                    f"Import complete. Success: {success_count}, Failed: {fail_count}"
                )

        except Exception as e:
            self.update_status(f"Import Error: {e}", 'red')
            logging.error(f"Failed to import from JSON file: {e}")

    def update_status(self, message, color='black', duration=5000):
        """Updates the text and color of the status bar."""
        self.status_bar.config(foreground=color)
        self.status_bar_text.set(message)
        if hasattr(self, "_status_clear_job"):
            self.after_cancel(self._status_clear_job)

        if duration > 0:
            self._status_clear_job = self.after(
                duration,
                lambda: self.status_bar_text.set("Ready")
                or self.status_bar.config(foreground='black'),
            )


if __name__ == '__main__':
    setup_logging()
    if os.name != 'nt':
        logging.critical("This script is designed for Windows only.")
        sys.exit(1)

    # This handles finding the path when bundled with PyInstaller
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)

    app = EnvManagerApp()
    app.mainloop()
