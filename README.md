# Su - Simple Utility Tools

A collection of simple yet powerful Python GUI applications for automation and development workflows.

## 🛠️ Tools Overview

### 1. **Su_Onefile_Builder** (`onefile/`)
A full-featured PyInstaller GUI builder that creates portable one-file executables from Python scripts.

**Features:**
- 🎯 One-click executable creation
- 🖼️ Icon support (PNG/ICO with auto-conversion)
- 📁 Data files bundling
- 🖥️ Integrated terminal for commands
- 🔧 Automatic Tkinter data inclusion
- 🧹 Auto-cleanup of build artifacts

**Usage:**
```bash
cd onefile
python onefile.pyw
```

**Dependencies:**
```bash
uv pip install pyinstaller pywin32 pillow
```

### 2. **Su_Chat** (`su_chat/`)
An advanced GPT-4 chatbot with session management and theme customization.

**Features:**
- 💬 GPT-4o, GPT-4 Turbo, and GPT-3.5 support
- 📚 Session management with custom titles
- 🎨 Light/Dark theme toggle
- 💾 Auto-save conversations
- 📋 Copy AI responses
- ⌨️ Rich keyboard shortcuts
- 🖥️ Console logging

**Usage:**
```bash
cd su_chat
# Place your OpenAI API key in 'ak' file
python su_chat.pyw
```

**Dependencies:**
```bash
uv pip install openai
```

**Keyboard Shortcuts:**
- `F2`: Rename session
- `F4`: Focus chat input
- `Ctrl+N`: New session
- `Ctrl+Del`: Delete session
- `Ctrl+PageUp/PageDown`: Switch sessions
- `Home/End`: Scroll to top/bottom

### 3. **Su_Click** (`su_click/`)
A mouse and keyboard automation tool for recording and replaying user interactions.

**Features:**
- 🎬 Record mouse clicks and keyboard input
- ▶️ Playback with speed control
- 📌 Pin favorite presets
- 💾 Save/load automation sequences
- 🎮 Global hotkeys (Ctrl+F8-F12)
- ✏️ Edit recordings in notepad
- 🏷️ Rename and organize presets

**Usage:**
```bash
cd su_click
python su_click.pyw
```

**Dependencies:**
```bash
uv pip install mouse keyboard
uv pip install pywin32  # Windows only, for better compatibility
```

**Global Hotkeys:**
- `Ctrl+F8`: Start recording
- `Ctrl+F9`: Stop recording playback
- `Ctrl+F10`: Start playback
- `Ctrl+F12`: Exit application

### 4. **Su_Alarm** (`alarm/`)
A task scheduling application with pastel color notifications and alarm management.

**Features:**
- ⏰ Schedule alarms and tasks with date/time
- 🎨 Pastel color notifications when alarms trigger
- 📝 Task management with titles and descriptions
- 🔔 Auto-dismiss notifications after configurable duration
- 💾 Persistent storage of alarms and settings
- 📊 Schedule management interface

**Usage:**
```bash
cd alarm
python alarm.pyw
```

**Dependencies:**
```bash
# Uses built-in Python libraries only
# tkinter (usually included with Python)
```

**Features:**
- Add, edit, and delete scheduled tasks
- Set custom date and time for each alarm
- View all scheduled alarms in a organized list
- Automatic alarm triggering with pastel notifications
- Configurable notification duration and colors

## 🚀 Quick Start

### Option 1: Use the Launcher (Recommended)
```bash
git clone https://github.com/savvy773/su.git
cd su
uv pip install -r requirements.txt
python launcher.py
```

### Option 2: Manual Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/savvy773/su.git
   cd su
   ```

2. **Install dependencies for the tool you want to use:**
   ```bash
   # For onefile builder
   uv pip install pyinstaller pywin32 pillow

   # For chat application
   uv pip install openai

   # For automation tool
   uv pip install mouse keyboard pywin32

   # Or install all at once
   uv pip install -r requirements.txt
   ```

3. **Run the desired application:**
   ```bash
   # PyInstaller GUI
   cd onefile && python onefile.pyw

   # Chat application
   cd su_chat && python su_chat.pyw

   # Automation tool
   cd su_click && python su_click.pyw

   # Alarm app
   cd alarm && python alarm.pyw
   ```

### Windows Quick Install
Run `install_deps.bat` to automatically install all dependencies.

## 📋 Requirements

- **Python 3.7+**
- **Windows OS** (for full functionality)
- **Tkinter** (usually included with Python)

## 🔧 Configuration

### Su_Chat Setup
1. Create an `ak` file in the `su_chat` directory
2. Add your OpenAI API key to this file
3. The application will automatically load the key on startup

### Su_Click Setup
- Configuration is automatically saved in `config.json`
- Presets are stored in the `presets/` folder
- Window geometry and pinned presets are preserved between sessions

## 🎨 Features in Detail

### Session Management (Su_Chat)
- **Multiple concurrent conversations**
- **Custom session titles**
- **Persistent conversation history**
- **Session switching with keyboard shortcuts**

### Automation Capabilities (Su_Click)
- **Record complex user interactions**
- **Variable playback speed**
- **Preset management with pinning system**
- **JSON-based recording format for easy editing**

### Build Optimization (Su_Onefile)
- **Automatic dependency detection**
- **Icon format conversion**
- **Data file inclusion**
- **Build artifact cleanup**

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

*Simple tools for complex workflows* ✨
