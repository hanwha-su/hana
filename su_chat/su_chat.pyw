# Copyright Juns Choi, Hanwha Energy All rights reserved.

import tkinter as tk
import openai
import os
import json
import datetime
import threading
import sys

# Finds any resource file in the same folder as the executable or script.
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = os.path.dirname(sys.executable)
    elif getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

KEY_PATH = resource_path("ak")
CONFIG_FILE = "_config.json"

THEMES = {
    "light": {
        "CHAT_BG": "#f5f6fa",
        "SIDEBAR_BG": "#ececec",
        "SESSION_FG": "#212529",
        "SESSION_SEL_BG": "#ffe45f",
        "SESSION_SEL_FG": "#000000",
        "BUTTON_BG": "#e2e6ea",
        "BUTTON_FG": "#222222",
        "SEND_BTN_BG": "#2196f3",
        "SEND_BTN_FG": "#ffffff",
        "SEND_BTN_ACTIVE_BG": "#1976d2",
        "SEND_BTN_ACTIVE_FG": "#ffffff",
        "INPUT_BG": "#F1F8F1",
        "TEXT_FG": "#212529",
        "CURSOR": "#e19e2a",
        "SELECT_BG": "#fff9b0",
        "SELECT_FG": "#000000",
        "AI_BG": "#f6f1f6",
        "USER_BG": "#e1f5e9",
        "AI_PREFIX": "#401a7e",
        "USER_PREFIX": "#2e7d32",
        "CODEBLOCK_BG": "#f0f0f0",
        "CODEBLOCK_FG": "#212529",
        "CONSOLE_BG": "#23272e",
        "CONSOLE_FG": "#bbbbbb",
        "SIDEBAR_BORDER": "#bdbdbd",
        "SCROLL_BG": "#ececec",
        "SCROLL_TROUGH": "#d3d3d3"
    },
    "dark": {
        "CHAT_BG": "#171818",
        "SIDEBAR_BG": "#23272e",
        "SESSION_FG": "#eeeeee",
        "SESSION_SEL_BG": "#eadea3",
        "SESSION_SEL_FG": "#000000",
        "BUTTON_BG": "#31364a",
        "BUTTON_FG": "#eeeeee",
        "SEND_BTN_BG": "#1976d2",
        "SEND_BTN_FG": "#ffffff",
        "SEND_BTN_ACTIVE_BG": "#2196f3",
        "SEND_BTN_ACTIVE_FG": "#ffffff",
        "INPUT_BG": "#32342E",
        "TEXT_FG": "#ffffff",
        "CURSOR": "#e0bfbf",
        "SELECT_BG": "#fff9b0",
        "SELECT_FG": "#000000",
        "AI_BG": "#2b2f36",
        "USER_BG": "#2b363b",
        "AI_PREFIX": "#eed3f4",
        "USER_PREFIX": "#edd98a",
        "CODEBLOCK_BG": "#282c34",
        "CODEBLOCK_FG": "#f8f8f2",
        "CONSOLE_BG": "#181a20",
        "CONSOLE_FG": "#bdbdbd",
        "SIDEBAR_BORDER": "#444",
        "SCROLL_BG": "#23272e",
        "SCROLL_TROUGH": "#181a20"
    }
}

sessions = []
current_session_idx = None
session_loading = False
edit_entry = None

WIN_FONT = ("Malgun Gothic", 10)
WIN_FONT_BIG = ("Malgun Gothic", 12, "bold")
AVAILABLE_MODELS = [
    ("GPT-4.1", "gpt-4.1"),
    ("GPT-4.1 Mini", "gpt-4.1-mini"),
]

def load_all():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.pop("themes", None)
        return cfg
    return {}

def save_all():
    cfg = {
        "geometry": root.geometry(),
        "sessions": [],
        "current_session_idx": current_session_idx,
        "theme": current_theme
    }
    for s in sessions:
        sess = {
            "history": s.get("history", []),
            "chat_widgets": s.get("chat_widgets", []),
            "console": s.get("console", []),
            "custom_title": s.get("custom_title", "")
        }
        cfg["sessions"].append(sess)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def log_to_console(message, always=False):
    now = datetime.datetime.now().strftime("[%m-%d %H:%M] ")
    line = now + message + "\n"
    console_box.config(state="normal")
    console_box.insert("end", line)
    console_box.see("end")
    console_box.config(state="disabled")
    if current_session_idx is not None:
        sessions[current_session_idx]["console"].append(line)
    if always:
        root.update_idletasks()

def bind_scroll_to_widget(widget):
    def _on_mousewheel(event):
        chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    widget.bind("<MouseWheel>", _on_mousewheel)
    widget.bind("<Button-4>", _on_mousewheel)
    widget.bind("<Button-5>", _on_mousewheel)

def right_click_copy(event):
    widget = event.widget
    try:
        selected = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        root.clipboard_clear()
        root.clipboard_append(selected)
        log_to_console("Copied selected text.")
        widget.tag_remove(tk.SEL, "1.0", tk.END)
        widget.see("insert")
    except tk.TclError:
        pass

def console_right_click_copy(event):
    widget = event.widget
    try:
        selection = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
    except tk.TclError:
        widget.tag_add(tk.SEL, "1.0", tk.END)
        selection = widget.get("1.0", tk.END)
    root.clipboard_clear()
    root.clipboard_append(selection)
    log_to_console("Console text copied.")
    widget.tag_remove("1.0", tk.END)
    widget.see("end")

def update_widget_theme(widget, theme):
    try:
        cls = widget.winfo_class()
        if cls in ("Frame", "Canvas"):
            widget.config(bg=theme["CHAT_BG"])
        elif cls == "Label":
            widget.config(bg=theme["CHAT_BG"], fg=theme["TEXT_FG"])
        elif cls == "Button":
            widget.config(bg=theme["BUTTON_BG"], fg=theme["BUTTON_FG"],
                          activebackground=theme["SESSION_SEL_BG"], activeforeground=theme["BUTTON_FG"])
        elif cls == "Listbox":
            widget.config(bg=theme["SIDEBAR_BG"], fg=theme["SESSION_FG"],
                          selectbackground=theme["SELECT_BG"], selectforeground=theme["SELECT_FG"])
        elif cls == "Text":
            widget.config(
                selectbackground=theme["SELECT_BG"],
                selectforeground=theme["SELECT_FG"],
                insertbackground=theme["CURSOR"]
            )
            if hasattr(widget, "_is_input_box") and widget._is_input_box:
                widget.config(bg=theme["INPUT_BG"], fg=theme["TEXT_FG"])
            else:
                widget.config(bg=theme["CHAT_BG"], fg=theme["TEXT_FG"])
        elif cls == "Scrollbar":
            widget.config(
                bg=theme.get("SCROLL_BG", theme["SIDEBAR_BG"]),
                troughcolor=theme.get("SCROLL_TROUGH", theme["SIDEBAR_BG"]),
                activebackground=theme.get("SESSION_SEL_BG", theme["SIDEBAR_BG"]),
                highlightbackground=theme.get("SIDEBAR_BG", "#23272e")
            )
        elif cls == "Entry":
            widget.config(bg=theme.get("ENTRY_BG", theme["CHAT_BG"]), fg=theme["TEXT_FG"],
                          selectbackground=theme["SELECT_BG"], selectforeground=theme["SELECT_FG"],
                          insertbackground=theme["CURSOR"])
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            update_widget_theme(child, theme)
    except Exception:
        pass

def apply_theme(theme_name):
    theme = THEMES[theme_name]
    root.config(bg=theme["CHAT_BG"])
    for widget in root.winfo_children():
        widget.config(bg=theme["CHAT_BG"])
    update_widget_theme(root, theme)
    sidebar.config(bg=theme["SIDEBAR_BG"])
    main_area.config(bg=theme["CHAT_BG"])
    bottom_container.config(bg=theme["CHAT_BG"])
    model_console_frame.config(bg=theme["SIDEBAR_BG"])
    send_btn_frame.config(bg=theme["CHAT_BG"])
    session_listbox.config(bg=theme["SIDEBAR_BG"], fg=theme["SESSION_FG"],
                          selectbackground=theme["SELECT_BG"], selectforeground=theme["SELECT_FG"])
    session_title_label.config(bg=theme["SIDEBAR_BG"], fg=theme["SESSION_FG"])
    input_box.config(bg=theme["INPUT_BG"], fg=theme["TEXT_FG"],
                     insertbackground=theme["CURSOR"],
                     selectbackground=theme["SELECT_BG"], selectforeground=theme["SELECT_FG"])
    chat_scroll.config(
        bg=theme.get("SCROLL_BG", theme["SIDEBAR_BG"]),
        troughcolor=theme.get("SCROLL_TROUGH", theme["SIDEBAR_BG"]),
        activebackground=theme.get("SESSION_SEL_BG", theme["SIDEBAR_BG"]),
        highlightbackground=theme["SIDEBAR_BG"]
    )
    if 'update_model_select_highlight' in globals():
        update_model_select_highlight()
    status_label.config(bg=theme["SIDEBAR_BG"])
    send_btn.config(bg=theme["SEND_BTN_BG"], fg=theme["SEND_BTN_FG"],
                    activebackground=theme["SEND_BTN_ACTIVE_BG"], activeforeground=theme["SEND_BTN_ACTIVE_FG"],
                    relief="raised", bd=2, highlightbackground=theme["SEND_BTN_BG"], highlightcolor=theme["SEND_BTN_BG"])
    copy_answer_btn.config(bg=theme["BUTTON_BG"], fg=theme["BUTTON_FG"],
                    activebackground=theme["SESSION_SEL_BG"], activeforeground=theme["BUTTON_FG"],
                    relief="groove", bd=2, highlightbackground=theme["BUTTON_BG"], highlightcolor=theme["BUTTON_BG"])
    clear_btn.config(bg=theme["BUTTON_BG"], fg=theme["BUTTON_FG"],
                    activebackground=theme["SESSION_SEL_BG"], activeforeground=theme["BUTTON_FG"],
                    relief="groove", bd=2, highlightbackground=theme["BUTTON_BG"], highlightcolor=theme["BUTTON_BG"])
    help_label.config(bg=theme["SIDEBAR_BG"], fg=theme["SESSION_FG"])
    sidebar_border.config(bg=theme.get("SIDEBAR_BORDER", "#ccc"))
    root.update_idletasks()
    root.update()
    root.after(10, lambda: root.update_idletasks())

def toggle_theme():
    global current_theme
    current_theme = "dark" if current_theme == "light" else "light"
    apply_theme(current_theme)
    save_all()

def session_title(sess):
    if sess.get("custom_title"):
        return sess["custom_title"]
    if sess.get("history"):
        msg = next((m["content"] for m in sess["history"] if m["role"] == "user"), "Untitled")
        return (msg[:18] + "...") if len(msg) > 18 else msg
    return "Untitled"

def save_session_titles():
    session_listbox.delete(0, tk.END)
    for sess in sessions:
        session_listbox.insert(tk.END, session_title(sess))
    if session_listbox.size() > 0:
        select_idx = current_session_idx if current_session_idx is not None and 0 <= current_session_idx < session_listbox.size() else 0
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(select_idx)
        session_listbox.activate(select_idx)
        session_listbox.see(select_idx)

def new_chat(event=None):
    global current_session_idx
    if session_loading: return
    sessions.append({
        "history": [],
        "chat_widgets": [],
        "console": [],
        "custom_title": ""
    })
    current_session_idx = len(sessions) - 1
    save_session_titles()
    load_session(current_session_idx)
    save_all()
    input_box.delete("1.0", tk.END)

def load_session(idx):
    global current_session_idx, session_loading
    if session_loading: return
    session_loading = True
    if idx < 0 or idx >= len(sessions): idx = 0
    current_session_idx = idx
    save_session_titles()
    for widget in chat_frame.winfo_children():
        widget.destroy()
    for item in sessions[current_session_idx]["chat_widgets"]:
        add_message_block(item[1], tag=item[2], history_mode=True)
    for _ in range(5):
        chat_frame.update_idletasks()
        chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
    chat_canvas.yview_moveto(1.0)
    console_box.config(state="normal")
    console_box.delete("1.0", tk.END)
    for line in sessions[current_session_idx]["console"]:
        if not line.lstrip().startswith("입력:"):
            console_box.insert("end", line)
    console_box.see("end")
    console_box.config(state="disabled")
    input_box.delete("1.0", tk.END)
    session_loading = False
    session_listbox.selection_clear(0, tk.END)
    session_listbox.selection_set(current_session_idx)
    session_listbox.activate(current_session_idx)

def clear_chat():
    global current_session_idx
    if session_loading: return
    if current_session_idx is None or not (0 <= current_session_idx < len(sessions)):
        log_to_console("Session info is invalid. Starting a new session.")
        new_chat()
        return
    for widget in chat_frame.winfo_children():
        widget.destroy()
    sessions[current_session_idx]["history"].clear()
    sessions[current_session_idx]["chat_widgets"].clear()
    sessions[current_session_idx]["console"].clear()
    console_box.config(state="normal")
    console_box.delete("1.0", tk.END)
    console_box.config(state="disabled")
    log_to_console("Chat history cleared.")
    save_all()

def delete_session(event):
    global current_session_idx
    idxs = session_listbox.curselection()
    if not idxs: return
    if len(sessions) <= 1:
        log_to_console("Cannot delete last session.")
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(0)
        session_listbox.activate(0)
        return
    idx = idxs[0]
    del sessions[idx]
    if current_session_idx > idx:
        current_session_idx -= 1
    elif current_session_idx == idx:
        current_session_idx = min(idx, len(sessions) - 1)
    save_session_titles()
    load_session(current_session_idx)
    save_all()
    log_to_console(f"Session {idx+1} deleted.")
    session_listbox.selection_clear(0, tk.END)
    session_listbox.selection_set(current_session_idx)
    session_listbox.activate(current_session_idx)
    session_listbox.focus_set()

def rename_session(event):
    global edit_entry
    if edit_entry is not None:
        return
    idxs = session_listbox.curselection()
    if not idxs:
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return
    if len(sessions) <= 1:
        return
    idx = idxs[0]
    bbox = session_listbox.bbox(idx)
    if bbox is None: return
    x, y, w, h = bbox
    old_title = session_title(sessions[idx])
    if edit_entry is not None:
        edit_entry.destroy()
        edit_entry = None
    edit_entry = tk.Entry(session_listbox, font=WIN_FONT)
    edit_entry.insert(0, old_title)
    edit_entry.select_range(0, tk.END)
    edit_entry.place(x=x, y=y, width=max(w, 180), height=h)
    theme = THEMES[current_theme]
    edit_entry.config(bg=theme.get("ENTRY_BG", theme["CHAT_BG"]), fg=theme["TEXT_FG"])
    root.after_idle(edit_entry.focus_set)
    def finish_edit(event=None):
        global edit_entry
        new_title = edit_entry.get().strip()
        sessions[idx]["custom_title"] = new_title if new_title else ""
        save_session_titles()
        save_all()
        if edit_entry is not None:
            edit_entry.destroy()
            edit_entry = None
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(idx)
        session_listbox.activate(idx)
    def cancel_edit(event=None):
        global edit_entry
        if edit_entry is not None:
            edit_entry.destroy()
            edit_entry = None
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(idx)
        session_listbox.activate(idx)
    edit_entry.bind("<Return>", finish_edit)
    edit_entry.bind("<Escape>", cancel_edit)
    edit_entry.bind("<FocusOut>", cancel_edit)

def global_rename_session(event=None):
    global edit_entry
    if edit_entry is not None:
        return
    session_listbox.focus_set()
    session_listbox.selection_clear(0, tk.END)
    if current_session_idx is not None and 0 <= current_session_idx < session_listbox.size():
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        session_listbox.see(current_session_idx)
    else:
        session_listbox.selection_set(0)
        session_listbox.activate(0)
        session_listbox.see(0)
    rename_session(event)

def scroll_to_end():
    root.after(50, _do_scroll)

def _do_scroll():
    chat_frame.update_idletasks()
    chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
    chat_canvas.yview_moveto(1.0)
    root.update_idletasks()

def scroll_to_start():
    def do_scroll():
        chat_frame.update_idletasks()
        chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
        chat_canvas.yview_moveto(0.0)
        root.update_idletasks()
        root.update()
    root.after_idle(do_scroll)

def chat_home(event):
    scroll_to_start()
    return "break"

def chat_end(event):
    scroll_to_end()
    return "break"

def add_message_block(text, tag=None, history_mode=False):
    theme = THEMES[current_theme]
    if tag == "log":
        return
    bg = theme["USER_BG"] if tag == "user" else theme["AI_BG"]
    sender = "You" if tag == "user" else "Hana"
    sender_color = theme["USER_PREFIX"] if tag == "user" else theme["AI_PREFIX"]

    container = tk.Frame(chat_frame, bg=bg)
    container.pack(fill="x", anchor="w", padx=0, pady=3)

    time_str = datetime.datetime.now().strftime("%H:%M")
    sender_label = tk.Label(container, text=f"{sender}  {time_str}", fg=sender_color, bg=bg, font=("Malgun Gothic", 9, "bold"), anchor="w", padx=6)
    sender_label.pack(fill="x", pady=(0, 1), anchor="w")

    msg_box = tk.Text(
        container,
        height=(text.count('\n') + 2),
        font=WIN_FONT,
        fg=theme["TEXT_FG"],
        bg=bg,
        bd=0,
        relief="flat",
        wrap="word",
        padx=10,
        pady=2,
        selectbackground=theme["SELECT_BG"],
        selectforeground=theme["SELECT_FG"],
        insertbackground=theme["CURSOR"]
    )
    msg_box.insert("1.0", text)
    msg_box.config(state="disabled")
    msg_box.pack(fill="x", padx=10, anchor="w")
    msg_box.see(tk.END)
    def on_select(event):
        event.widget.see(tk.END)
    msg_box.bind("<<Selection>>", on_select)
    msg_box.bind("<Button-3>", right_click_copy)
    bind_scroll_to_widget(msg_box)
    spacer = tk.Label(container, text="", bg=bg)
    spacer.pack(fill="x")
    scroll_to_end()
    if not history_mode and current_session_idx is not None:
        sessions[current_session_idx]["chat_widgets"].append(("plain", text, tag))

def on_select_session(event):
    idx = session_listbox.curselection()
    if idx:
        load_session(idx[0])
    session_listbox.selection_clear(0, tk.END)
    session_listbox.selection_set(current_session_idx)
    session_listbox.activate(current_session_idx)

def on_up_down(event):
    if edit_entry is not None:
        return "break"
    if len(sessions) <= 1:
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"
    cur = session_listbox.curselection()
    if not cur:
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"
    idx = cur[0]
    if event.keysym == "Up":
        if idx > 0:
            session_listbox.selection_clear(0, tk.END)
            session_listbox.selection_set(idx - 1)
            session_listbox.activate(idx - 1)
    elif event.keysym == "Down":
        if idx < session_listbox.size() - 1:
            session_listbox.selection_clear(0, tk.END)
            session_listbox.selection_set(idx + 1)
            session_listbox.activate(idx + 1)
    session_listbox.focus_set()
    return "break"

def on_session_enter(event):
    if edit_entry is not None:
        return "break"
    if len(sessions) <= 1:
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"
    cur = session_listbox.curselection()
    if cur:
        load_session(cur[0])
    session_listbox.selection_clear(0, tk.END)
    session_listbox.selection_set(current_session_idx)
    session_listbox.activate(current_session_idx)

def chat_pgup(event):
    chat_canvas.yview_scroll(-10, "units")
    return "break"

def chat_pgdn(event):
    chat_canvas.yview_scroll(10, "units")
    return "break"

def ctrl_pageup(event):
    global current_session_idx
    if edit_entry is not None:
        return "break"
    if len(sessions) <= 1:
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"
    if current_session_idx is not None and current_session_idx > 0:
        load_session(current_session_idx - 1)
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"

def ctrl_pagedown(event):
    global current_session_idx
    if edit_entry is not None:
        return "break"
    if len(sessions) <= 1:
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"
    if current_session_idx is not None and current_session_idx < len(sessions) - 1:
        load_session(current_session_idx + 1)
        session_listbox.selection_clear(0, tk.END)
        session_listbox.selection_set(current_session_idx)
        session_listbox.activate(current_session_idx)
        return "break"

def ctrl_newchat(event):
    new_chat()
    return "break"

def ctrl_delsession(event):
    delete_session(event)
    return "break"

def enter_event(event):
    if not event.state:
        send_message()

def focus_input_box(event=None):
    input_box.focus_set()

def set_api_status(msg, color="#888"):
    status_label.config(text=f"API status:\n{msg}", fg=color)
    status_label.update_idletasks()

def send_message(event=None):
    if session_loading: return
    if current_session_idx is None: new_chat()
    user_input = input_box.get("1.0", tk.END).strip()
    if not user_input:
        log_to_console("[Warning] No input.", always=True)
        return

    set_api_status("Waiting for response...\n\n", "#2196f3")
    log_to_console(f"[Model: {selected_model.get()}] User input sent")
    add_message_block(user_input, tag="user")
    input_box.delete("1.0", tk.END)
    history = sessions[current_session_idx]["history"]
    history.append({"role": "user", "content": user_input})

    def openai_worker(history_snapshot, model, sess_idx):
        full_answer = ""
        keep_going = True
        last_finish_reason = None
        local_history = history_snapshot.copy()
        while keep_going:
            try:
                response = openai.chat.completions.create(
                    model=model,
                    messages=local_history,
                    max_tokens=4096,
                )
                answer = response.choices[0].message.content.strip()
                last_finish_reason = response.choices[0].finish_reason
                full_answer = (full_answer + "\n" + answer) if full_answer else answer
                local_history.append({"role": "assistant", "content": answer})
                if last_finish_reason == "length":
                    local_history.append({"role": "user", "content": "Please continue."})
                    root.after(0, lambda: log_to_console("[Auto-continue] Response was cut off. Requesting continuation."))
                    continue
                else:
                    keep_going = False
            except Exception as e:
                root.after(0, lambda: (
                    set_api_status("Error\n\n", "#e53935"),
                    log_to_console(f"Error: {str(e)}")
                ))
                return
        def apply_answer():
            if current_session_idx == sess_idx:
                sessions[sess_idx]["history"] = local_history
                add_message_block(full_answer, tag="ai")
                scroll_to_end()
                save_session_titles()
                save_all()
                set_api_status("Connected\n\n", "#43a047")
        root.after(0, apply_answer)

    thread = threading.Thread(
        target=openai_worker,
        args=(history.copy(), selected_model.get(), current_session_idx),
        daemon=True
    )
    thread.start()

def get_last_ai_blocks():
    if current_session_idx is None or not sessions[current_session_idx]["chat_widgets"]:
        return []
    widgets = sessions[current_session_idx]["chat_widgets"]
    ai_blocks = []
    started = False
    for w in reversed(widgets):
        if (w[0] == "plain" and w[2] == "ai"):
            ai_blocks.insert(0, w)
            started = True
        elif w[0] == "plain" and w[2] == "user":
            if started:
                break
    return ai_blocks

def copy_last_ai_plain_blocks():
    ai_blocks = get_last_ai_blocks()
    if not ai_blocks:
        log_to_console("No AI answer to copy.")
        return
    text = [b[1].strip() for b in ai_blocks]
    result = "\n\n".join(text)
    root.clipboard_clear()
    root.clipboard_append(result)
    log_to_console("AI answer copied.")

def on_close():
    save_all()
    root.destroy()

if not os.path.exists(KEY_PATH):
    raise FileNotFoundError(f"API key file not found: {KEY_PATH}. Please place the file next to the executable or script.")
with open(KEY_PATH, "r") as f:
    API_KEY = f.read().strip()
openai.api_key = API_KEY

root = tk.Tk()
root.title("Su Chatbot (Hana)")

selected_model = tk.StringVar()
selected_model.set("gpt-4.1-mini")

cfg = load_all()
if "theme" in cfg:
    current_theme = cfg["theme"]
else:
    current_theme = "light"

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
default_w = int(screen_w * 0.6)
default_h = int(screen_h * 0.85)
default_geometry = f"{default_w}x{default_h}+0+{int(screen_h * 0.05)}"

if "geometry" in cfg:
    root.geometry(cfg["geometry"])
else:
    root.geometry(default_geometry)

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(2, weight=1)

sidebar = tk.Frame(root, width=170, bg=THEMES[current_theme]["SIDEBAR_BG"], highlightthickness=0)
sidebar.grid(row=0, column=0, sticky='nswe')
sidebar.grid_propagate(0)
sidebar.grid_rowconfigure(5, weight=1)

sidebar_border = tk.Frame(root, width=2, bg=THEMES[current_theme].get("SIDEBAR_BORDER", "#ccc"), highlightthickness=0)
sidebar_border.grid(row=0, column=1, sticky="ns")

main_area = tk.Frame(root, bg=THEMES[current_theme]["CHAT_BG"])
main_area.grid(row=0, column=2, sticky="nsew")
main_area.grid_rowconfigure(0, weight=10)
main_area.grid_rowconfigure(1, weight=2)
main_area.grid_rowconfigure(6, weight=1)
main_area.grid_columnconfigure(0, weight=8)
main_area.grid_columnconfigure(1, weight=2)

session_title_label = tk.Label(sidebar, text="Sessions", font=WIN_FONT_BIG, anchor="w")
session_title_label.grid(row=0, column=0, sticky="ew", padx=10, pady=6)

newchat_btn = tk.Button(sidebar, text="New Chat", command=lambda: new_chat(), font=WIN_FONT)
newchat_btn.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="ew")

theme_btn = tk.Button(sidebar, text="Toggle Theme", command=toggle_theme, font=WIN_FONT)
theme_btn.grid(row=2, column=0, padx=10, pady=(0, 4), sticky="ew")

status_label = tk.Label(
    sidebar,
    text="API status:\n...\n",
    font=("Malgun Gothic", 9, "italic"),
    anchor="w",
    fg="#888",
    bg=THEMES[current_theme]["SIDEBAR_BG"],
    width=24,
    height=3,
    wraplength=180,
    justify="left",
    padx=2,
    pady=7
)
status_label.grid(row=3, column=0, padx=10, pady=(0, 2), sticky="ew")

help_label = tk.Label(
    sidebar,
    text="Help\nF2: Rename session\nF4: Focus chat\nCtrl+N: New session\nCtrl+Del: Delete session\nHome: Scroll top\nEnd: Scroll bottom",
    font=("Malgun Gothic", 9),
    anchor="w",
    bg=THEMES.get(current_theme, {}).get("SIDEBAR_BG", "#eaeaea"),
    fg=THEMES.get(current_theme, {}).get("SESSION_FG", "#222"),
    wraplength=155,
    justify="left",
    relief="flat",
    padx=2,
    pady=7
)
help_label.grid(row=4, column=0, padx=10, pady=(0, 3), sticky="ew")

session_listbox = tk.Listbox(
    sidebar, font=WIN_FONT, activestyle='none', highlightthickness=0, exportselection=0
)
session_listbox.grid(row=5, column=0, sticky="nswe", padx=6, pady=(0, 2))

chat_canvas = tk.Canvas(main_area, borderwidth=0, highlightthickness=0, bg=THEMES[current_theme]["CHAT_BG"])
chat_scroll = tk.Scrollbar(main_area, command=chat_canvas.yview)
chat_canvas.grid(row=0, column=0, padx=14, pady=(14, 20), sticky="nsew", columnspan=2)
chat_scroll.grid(row=0, column=2, sticky="ns")
chat_canvas.config(yscrollcommand=chat_scroll.set)
chat_frame = tk.Frame(chat_canvas, bg=THEMES[current_theme]["CHAT_BG"])
chat_window = chat_canvas.create_window((0, 0), window=chat_frame, anchor="nw")
chat_frame.bind("<Configure>", lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all")))
chat_canvas.bind("<Configure>", lambda e: chat_canvas.itemconfig(chat_window, width=e.width))

bind_scroll_to_widget(chat_canvas)
bind_scroll_to_widget(chat_frame)
main_area.bind_all("<Prior>", chat_pgup)
main_area.bind_all("<Next>", chat_pgdn)
main_area.bind_all("<Home>", chat_home)
main_area.bind_all("<End>", chat_end)

input_box = tk.Text(
    main_area,
    width=80,
    height=5,
    font=WIN_FONT,
    undo=True,
    autoseparators=True,
    maxundo=-1,
    relief="flat",
    insertbackground=THEMES[current_theme]["CURSOR"],
    selectbackground=THEMES[current_theme]["SELECT_BG"],
    selectforeground=THEMES[current_theme]["SELECT_FG"],
    bg=THEMES[current_theme]["INPUT_BG"],
    fg=THEMES[current_theme]["TEXT_FG"]
)
input_box._is_input_box = True
input_box.grid(row=1, column=0, padx=16, pady=12, sticky='nsew', columnspan=2)

bottom_container = tk.Frame(main_area)
bottom_container.grid(row=6, column=0, columnspan=2, sticky='nsew', padx=0, pady=(0, 0))
bottom_container.grid_rowconfigure(0, weight=1)
bottom_container.grid_columnconfigure(0, weight=1)
bottom_container.grid_columnconfigure(1, weight=3)

model_console_frame = tk.Frame(
    bottom_container,
    highlightbackground="#bdbdbd",
    highlightthickness=1,
    bd=1
)
model_console_frame.grid(row=0, column=0, padx=(16, 0), pady=8, sticky='nsew')
model_console_frame.grid_rowconfigure(0, weight=1)
model_console_frame.grid_columnconfigure(0, weight=1)

model_buttons = []
def set_selected_model(model_value):
    selected_model.set(model_value)
    update_model_select_highlight()
    save_all()

def update_model_select_highlight():
    theme = THEMES[current_theme]
    for idx, (label, value) in enumerate(AVAILABLE_MODELS):
        btn = model_buttons[idx]
        btn.config(font=("Malgun Gothic", 9))
        if selected_model.get() == value:
            btn.config(bg=theme["SESSION_SEL_BG"], fg=theme["SESSION_SEL_FG"],
                       relief="solid", bd=2)
        else:
            btn.config(bg=theme["BUTTON_BG"], fg=theme["BUTTON_FG"], relief="flat", bd=0)

for idx, (label, value) in enumerate(AVAILABLE_MODELS):
    btn = tk.Button(model_console_frame, text=label, command=lambda v=value: set_selected_model(v),
                    font=("Malgun Gothic", 9), anchor="w", justify="left", wraplength=90, cursor="hand2")
    btn.pack(anchor="w", pady=2, padx=6, fill="x")
    model_buttons.append(btn)
update_model_select_highlight()

console_btns_frame = tk.Frame(bottom_container)
console_btns_frame.grid(row=0, column=1, padx=(0, 16), pady=8, sticky="nsew")
console_btns_frame.grid_rowconfigure(0, weight=1)
console_btns_frame.grid_columnconfigure(0, weight=1)
console_btns_frame.grid_columnconfigure(1, weight=0)

console_box = tk.Text(
    console_btns_frame,
    height=1,
    font=("Consolas", 9),
    state="disabled",
    relief="flat",
    wrap="word",
    insertbackground=THEMES[current_theme]["CURSOR"],
    bg=THEMES[current_theme]["CONSOLE_BG"],
    fg=THEMES[current_theme]["CONSOLE_FG"]
)
console_box.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
console_box.bind("<Button-3>", console_right_click_copy)

send_btn_frame = tk.Frame(console_btns_frame)
send_btn_frame.grid(row=0, column=1, sticky="ne", padx=(10,0))
send_btn_frame.grid_rowconfigure(0, weight=1)

btn_width = 13
send_btn = tk.Button(send_btn_frame, text="Send", width=btn_width, command=lambda: send_message(),
                     font=WIN_FONT, bg=THEMES[current_theme]["SEND_BTN_BG"], fg=THEMES[current_theme]["SEND_BTN_FG"],
                     activebackground=THEMES[current_theme]["SEND_BTN_ACTIVE_BG"], activeforeground=THEMES[current_theme]["SEND_BTN_ACTIVE_FG"],
                     relief="raised", bd=2, cursor="hand2")
send_btn.pack(side="top", pady=(0, 2), anchor="e", fill="x")

copy_answer_btn = tk.Button(send_btn_frame, text="Copy Answer", width=btn_width, command=copy_last_ai_plain_blocks,
                           font=WIN_FONT, relief="groove", bd=2, cursor="hand2")
copy_answer_btn.pack(side="top", pady=(0, 2), anchor="e", fill="x")

clear_btn = tk.Button(send_btn_frame, text="Clear Chat", width=btn_width, command=lambda: clear_chat(),
                      font=WIN_FONT, relief="groove", bd=2, cursor="hand2")
clear_btn.pack(side="top", pady=(0, 2), anchor="e", fill="x")

if "sessions" in cfg and isinstance(cfg["sessions"], list) and len(cfg["sessions"]) > 0:
    for s in cfg["sessions"]:
        sessions.append({
            "history": s.get("history", []),
            "chat_widgets": s.get("chat_widgets", []),
            "console": [],
            "custom_title": s.get("custom_title", "")
        })
    if "current_session_idx" in cfg and 0 <= cfg["current_session_idx"] < len(sessions):
        current_session_idx = cfg["current_session_idx"]
    else:
        current_session_idx = 0
    root.after(50, lambda: (
        save_session_titles(),
        load_session(current_session_idx if current_session_idx is not None else 0)
    ))
else:
    new_chat()

root.bind("<F2>", global_rename_session)
session_listbox.bind("<F2>", rename_session)
session_listbox.bind("<<ListboxSelect>>", on_select_session)
session_listbox.bind("<Delete>", delete_session)
session_listbox.bind("<Up>", on_up_down)
session_listbox.bind("<Down>", on_up_down)
session_listbox.bind("<Return>", on_session_enter)
session_listbox.bind("<Double-1>", on_session_enter)
root.bind("<Control-Prior>", ctrl_pageup)
root.bind("<Control-Next>", ctrl_pagedown)
root.bind("<Control-n>", ctrl_newchat)
root.bind("<Control-Delete>", ctrl_delsession)
input_box.bind("<Control-Return>", send_message)
input_box.bind("<Shift-Return>", lambda e: input_box.insert(tk.INSERT, "\n"))
input_box.bind("<Return>", enter_event)
root.bind('<F4>', focus_input_box)
root.protocol("WM_DELETE_WINDOW", on_close)

apply_theme(current_theme)
root.after(200, lambda: set_api_status("Connected\n\n", "#43a047"))
root.mainloop()