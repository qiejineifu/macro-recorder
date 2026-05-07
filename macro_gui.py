#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""键鼠宏录制/回放 GUI 工具"""

import ctypes
import json
import os
import sys
import time
import threading
from datetime import datetime
from pynput import mouse, keyboard as pynput_kb
import tkinter as tk
from tkinter import ttk, messagebox

if sys.platform == 'win32':
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _get_data_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_DIR = _get_data_dir()
RECORD_DIR = os.path.join(DATA_DIR, "recordings")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ---- 配色方案 ----
C_BG = "#f0f2f5"
C_CARD = "#ffffff"
C_TEXT = "#1a1a2e"
C_SUBTEXT = "#6b7280"
C_PRIMARY = "#4f46e5"
C_RECORD = "#ef4444"
C_PLAY = "#3b82f6"
C_STOP = "#6b7280"
C_SUCCESS = "#10b981"
C_BORDER = "#e5e7eb"

SPECIAL_KEYS = {
    'ctrl': pynput_kb.Key.ctrl, 'ctrl_l': pynput_kb.Key.ctrl_l, 'ctrl_r': pynput_kb.Key.ctrl_r,
    'shift': pynput_kb.Key.shift, 'shift_l': pynput_kb.Key.shift_l, 'shift_r': pynput_kb.Key.shift_r,
    'alt': pynput_kb.Key.alt, 'alt_l': pynput_kb.Key.alt_l, 'alt_r': pynput_kb.Key.alt_r,
    'cmd': pynput_kb.Key.cmd, 'cmd_l': pynput_kb.Key.cmd_l, 'cmd_r': pynput_kb.Key.cmd_r,
    'enter': pynput_kb.Key.enter, 'tab': pynput_kb.Key.tab,
    'space': pynput_kb.Key.space, 'esc': pynput_kb.Key.esc,
    'backspace': pynput_kb.Key.backspace, 'delete': pynput_kb.Key.delete,
    'insert': pynput_kb.Key.insert, 'home': pynput_kb.Key.home, 'end': pynput_kb.Key.end,
    'page_up': pynput_kb.Key.page_up, 'page_down': pynput_kb.Key.page_down,
    'up': pynput_kb.Key.up, 'down': pynput_kb.Key.down,
    'left': pynput_kb.Key.left, 'right': pynput_kb.Key.right,
    'caps_lock': pynput_kb.Key.caps_lock, 'num_lock': pynput_kb.Key.num_lock,
    'print_screen': pynput_kb.Key.print_screen,
}
for i in range(1, 13):
    SPECIAL_KEYS[f'f{i}'] = getattr(pynput_kb.Key, f'f{i}')

BUTTON_MAP = {
    'left': mouse.Button.left, 'right': mouse.Button.right, 'middle': mouse.Button.middle,
}
CONTROL_KEYS = {'f8', 'f9', 'f10'}


def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class MacroRecorder:
    def __init__(self):
        self.events = []
        self.recording = False
        self.playing = False
        self.stop_flag = False
        self.record_start_time = 0
        self.loop_count = 1
        self.mouse_ctrl = mouse.Controller()
        self.kb_ctrl = pynput_kb.Controller()
        self.mouse_listener = None
        self.kb_listener = None
        self.on_status_change = None

    @staticmethod
    def _precise_sleep(seconds):
        if seconds <= 0:
            return
        if seconds > 0.01:
            time.sleep(seconds - 0.005)
        target = time.perf_counter() + seconds
        while time.perf_counter() < target:
            pass

    def start_recording(self):
        self.events = []
        self.recording = True
        self.record_start_time = time.perf_counter()
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.mouse_listener.start()
        self.kb_listener = pynput_kb.Listener(
            on_press=lambda k: self._record_key_event(k, "key_press"),
            on_release=lambda k: self._record_key_event(k, "key_release"))
        self.kb_listener.start()
        self._notify_status("recording", "录制中...")

    def stop_recording(self):
        if not self.recording:
            return None
        self.recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.kb_listener:
            self.kb_listener.stop()
        duration = time.perf_counter() - self.record_start_time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"macro_{timestamp}.json"
        filepath = os.path.join(RECORD_DIR, filename)
        data = {
            "created": timestamp,
            "duration": round(duration, 3),
            "event_count": len(self.events),
            "loop_count": self.loop_count if self.loop_count != float('inf') else 0,
            "events": self.events,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._notify_status("idle", "录制完成")
        return filepath

    def _on_mouse_click(self, x, y, button, pressed):
        if not self.recording: return
        self.events.append({
            "type": "mouse_click", "x": x, "y": y,
            "button": button.name,
            "action": "press" if pressed else "release",
            "time": round(time.perf_counter() - self.record_start_time, 4),
        })

    def _record_key_event(self, key, event_type):
        if not self.recording:
            return
        key_name = self._key_to_name(key)
        if key_name in CONTROL_KEYS:
            return
        self.events.append({
            "type": event_type, "key": key_name,
            "time": round(time.perf_counter() - self.record_start_time, 4),
        })

    def _key_to_name(self, key):
        ch = getattr(key, 'char', None)
        return ch if ch is not None else str(key).replace('Key.', '')

    def start_playback(self, filepath=None, loop_count=None):
        if self.recording: return False
        if loop_count is not None:
            self.loop_count = loop_count
        if filepath:
            target = filepath
        else:
            recordings = sorted(
                [f for f in os.listdir(RECORD_DIR) if f.endswith('.json')], reverse=True)
            if not recordings: return False
            target = os.path.join(RECORD_DIR, recordings[0])
        with open(target, 'r', encoding='utf-8') as f:
            data = json.load(f)
        events = data.get("events", [])
        if loop_count is not None:
            lc = loop_count
        else:
            lc = data.get("loop_count", self.loop_count)
        if lc == 0: lc = float('inf')
        self.playing = True
        self.stop_flag = False
        self._notify_status("playing", os.path.basename(target))
        threading.Thread(target=self._playback_loop, args=(events, lc), daemon=True).start()
        return True

    def _playback_loop(self, events, loop_count):
        loop = 0
        while loop < loop_count:
            if self.stop_flag: break
            loop += 1
            loop_start = time.perf_counter()
            for event in events:
                if self.stop_flag: break
                wait = loop_start + event["time"] - time.perf_counter()
                if wait > 0:
                    self._precise_sleep(wait)
                if not self.stop_flag: self._execute_event(event)
        self.playing = False
        if self.stop_flag:
            self._notify_status("idle", "回放已停止")
        else:
            self._notify_status("idle", "回放完成")

    def _execute_event(self, event):
        try:
            if event["type"] == "key_press":
                self.kb_ctrl.press(self._name_to_key(event["key"]))
            elif event["type"] == "key_release":
                self.kb_ctrl.release(self._name_to_key(event["key"]))
            elif event["type"] == "mouse_click":
                self.mouse_ctrl.position = (event["x"], event["y"])
                self._precise_sleep(0.005)
                btn = BUTTON_MAP.get(event["button"], mouse.Button.left)
                if event["action"] == "press":
                    self.mouse_ctrl.press(btn)
                else:
                    self.mouse_ctrl.release(btn)
        except Exception as e:
            print(f"[回放异常] {event}: {e}", file=sys.stderr)

    def _name_to_key(self, name):
        return SPECIAL_KEYS.get(name, name)

    def stop_playback(self):
        if self.recording: self.stop_recording()
        if self.playing: self.stop_flag = True

    def _notify_status(self, status, info):
        if self.on_status_change:
            self.on_status_change(status, info)


class MacroGUI:
    def __init__(self):
        self.recorder = MacroRecorder()
        self.recorder.on_status_change = self._on_status_change
        self.last_recording_filename = None
        self._poll_job = None
        os.makedirs(RECORD_DIR, exist_ok=True)

        self.root = tk.Tk()
        self.root.title("键鼠宏录制/回放")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)

        w, h = 460, 560
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self._setup_styles()
        self._build_ui()
        self._setup_hotkeys()
        self._load_last_session()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=C_BG, foreground=C_TEXT, font=('Microsoft YaHei UI', 9))
        style.configure('Card.TLabelframe', background=C_CARD, bordercolor=C_BORDER, relief='solid')
        style.configure('Card.TLabelframe.Label', background=C_CARD, foreground=C_TEXT,
                        font=('Microsoft YaHei UI', 10, 'bold'))
        style.configure('TButton', font=('Microsoft YaHei UI', 10), borderwidth=0,
                        background='#e2e8f0', foreground=C_TEXT)
        style.map('TButton', background=[('active', '#cbd5e1')])
        style.configure('Record.TButton', font=('Microsoft YaHei UI', 11, 'bold'),
                        background=C_RECORD, foreground='white', padding=(12, 8))
        style.map('Record.TButton', background=[('active', '#dc2626')])
        style.configure('Play.TButton', font=('Microsoft YaHei UI', 11, 'bold'),
                        background=C_PLAY, foreground='white', padding=(12, 8))
        style.map('Play.TButton', background=[('active', '#2563eb')])
        style.configure('Stop.TButton', font=('Microsoft YaHei UI', 10),
                        background=C_STOP, foreground='white', padding=(10, 6))
        style.map('Stop.TButton', background=[('active', '#4b5563')])
        style.configure('Small.TButton', font=('Microsoft YaHei UI', 9),
                        background='#e2e8f0', foreground=C_TEXT, padding=(8, 4))
        style.map('Small.TButton', background=[('active', '#cbd5e1')])
        style.configure('Status.TLabel', font=('Microsoft YaHei UI', 10))
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 14, 'bold'),
                        background=C_BG, foreground=C_TEXT)
        style.configure('Treeview', font=('Consolas', 9), rowheight=28,
                        background=C_CARD, fieldbackground=C_CARD, foreground=C_TEXT)
        style.configure('Treeview.Heading', font=('Microsoft YaHei UI', 9, 'bold'),
                        background=C_BG, foreground=C_SUBTEXT)
        style.map('Treeview', background=[('selected', '#dbeafe')], foreground=[('selected', C_TEXT)])

    def _build_ui(self):
        pad_outer = {'padx': 12}
        pad_inner = {'padx': 10}

        title = ttk.Label(self.root, text="键鼠宏录制 / 回放", style='Title.TLabel')
        title.pack(fill='x', padx=12, pady=(14, 6))

        self.history_frame = tk.Frame(self.root, bg=C_PRIMARY, highlightthickness=0)
        self.history_frame.pack(fill='x', padx=12, pady=(0, 4))
        self.history_label = tk.Label(
            self.history_frame,
            text="📂 上次录制: 暂无",
            font=('Microsoft YaHei UI', 9),
            bg=C_PRIMARY, fg='white',
            anchor='w', padx=12, pady=6,
        )
        self.history_label.pack(fill='x')

        card1 = ttk.LabelFrame(self.root, text="状态", style='Card.TLabelframe')
        card1.pack(fill='x', **pad_outer, pady=(4, 4))

        status_row = ttk.Frame(card1, style='TFrame')
        status_row.pack(fill='x', pady=6, **pad_inner)

        self.status_dot = tk.Canvas(status_row, width=14, height=14, bg=C_CARD, highlightthickness=0)
        self.status_dot.pack(side='left')
        self._draw_dot(C_SUCCESS)  # 默认绿色

        self.status_text = ttk.Label(status_row, text="就绪", style='Status.TLabel')
        self.status_text.pack(side='left', padx=(4, 20))

        self.event_count_label = ttk.Label(status_row, text="事件: 0", style='Status.TLabel')
        self.event_count_label.pack(side='left', padx=(0, 14))
        self.duration_label = ttk.Label(status_row, text="时长: 0.0s", style='Status.TLabel')
        self.duration_label.pack(side='left')

        card2 = ttk.LabelFrame(self.root, text="操作", style='Card.TLabelframe')
        card2.pack(fill='x', pady=4, **pad_outer)

        btn_grid = ttk.Frame(card2, style='TFrame')
        btn_grid.pack(fill='x', pady=6, **pad_inner)

        self.rec_btn = ttk.Button(btn_grid, text="开始录制  F8", style='Record.TButton',
                                  command=self._toggle_recording)
        self.rec_btn.grid(row=0, column=0, sticky='ew', padx=(0, 6), pady=3)

        self.play_btn = ttk.Button(btn_grid, text="回放  F9", style='Play.TButton',
                                   command=self._toggle_playback)
        self.play_btn.grid(row=0, column=1, sticky='ew', padx=(6, 0), pady=3)

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        self.stop_btn = ttk.Button(btn_grid, text="强制停止  F10", style='Stop.TButton',
                                   command=self._force_stop)
        self.stop_btn.grid(row=1, column=0, columnspan=2, sticky='ew', pady=3)

        loop_row = ttk.Frame(btn_grid, style='TFrame')
        loop_row.grid(row=2, column=0, columnspan=2, sticky='w', pady=(6, 0))
        ttk.Label(loop_row, text="循环次数:", font=('Microsoft YaHei UI', 9)).pack(side='left')
        self.loop_var = tk.StringVar(value="1")
        self.loop_entry = ttk.Spinbox(
            loop_row, from_=1, to=9999, textvariable=self.loop_var,
            width=8, validate='key',
            validatecommand=(self.root.register(self._validate_int), '%P'),
        )
        self.loop_entry.pack(side='left', padx=(8, 0))

        card3 = ttk.LabelFrame(self.root, text="录制文件", style='Card.TLabelframe')
        card3.pack(fill='both', expand=True, **pad_outer, pady=(4, 4))

        tree_frame = tk.Frame(card3, bg=C_CARD)
        tree_frame.pack(fill='both', expand=True, pady=6, **pad_inner)

        columns = ('filename', 'date', 'duration', 'events')
        self.file_tree = ttk.Treeview(
            tree_frame, columns=columns, show='headings',
            selectmode='browse', height=8,
        )
        self.file_tree.heading('filename', text='文件名')
        self.file_tree.heading('date', text='日期')
        self.file_tree.heading('duration', text='时长')
        self.file_tree.heading('events', text='事件数')
        self.file_tree.column('filename', width=200, minwidth=120)
        self.file_tree.column('date', width=90, anchor='center')
        self.file_tree.column('duration', width=60, anchor='center')
        self.file_tree.column('events', width=60, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        self.file_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.file_tree.bind('<Double-Button-1>', lambda e: self._toggle_playback())

        act_row = ttk.Frame(card3, style='TFrame')
        act_row.pack(fill='x', **pad_inner, pady=(0, 4))
        ttk.Button(act_row, text="刷新", style='Small.TButton',
                   command=self._refresh_file_list).pack(side='left', padx=(0, 6))
        ttk.Button(act_row, text="删除选中", style='Small.TButton',
                   command=self._delete_selected).pack(side='left')

        # ---- 底部 ----
        ttk.Label(self.root, text="热键: F8 录制  ·  F9 回放  ·  F10 停止",
                  font=('Microsoft YaHei UI', 8), foreground=C_SUBTEXT,
                  background=C_BG).pack(pady=(2, 10))

    def _draw_dot(self, color):
        self.status_dot.delete('all')
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline='')

    def _setup_hotkeys(self):
        self._hotkey_listener = pynput_kb.GlobalHotKeys({
            '<f8>': lambda: self.root.after(0, self._toggle_recording),
            '<f9>': lambda: self.root.after(0, self._toggle_playback),
            '<f10>': lambda: self.root.after(0, self._force_stop),
        })
        self._hotkey_listener.start()

    def _validate_int(self, val):
        return val == '' or val.isdigit()

    # ========== 上次录制持久化 ==========

    def _load_last_session(self):
        config = load_config()
        last_file = config.get('last_recording', '')
        last_loop = config.get('last_loop_count', 1)
        if last_loop:
            self.loop_var.set(str(last_loop))

        self._refresh_file_list()

        if last_file:
            # 在列表中查找并选中上次录制
            for item in self.file_tree.get_children():
                vals = self.file_tree.item(item, 'values')
                if vals and vals[0] == last_file:
                    self.file_tree.selection_set(item)
                    self.file_tree.see(item)
                    self.last_recording_filename = last_file
                    self._update_history_bar(last_file)
                    break
            # 即使文件已被删除，也记录文件名（下次覆盖）
            if not self.last_recording_filename:
                path = os.path.join(RECORD_DIR, last_file)
                try:
                    with open(path, 'r', encoding='utf-8') as _:
                        pass
                    self.last_recording_filename = last_file
                    self._update_history_bar(last_file)
                except FileNotFoundError:
                    pass

    def _persist_last_session(self, filename=None):
        if filename:
            self.last_recording_filename = filename
        config = load_config()
        config['last_recording'] = self.last_recording_filename
        try:
            config['last_loop_count'] = int(self.loop_var.get())
        except ValueError:
            config['last_loop_count'] = 1
        save_config(config)

    def _update_history_bar(self, filename):
        path = os.path.join(RECORD_DIR, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            dur = data.get('duration', 0)
            cnt = data.get('event_count', 0)
            self.history_label.config(
                text=f"上次录制: {filename}  ( {dur:.1f}s · {cnt} 事件 )")
        except (FileNotFoundError, json.JSONDecodeError):
            self.history_label.config(text=f"上次录制: {filename}  (已删除)")

    # ========== 动作 ==========

    def _toggle_recording(self):
        if self.recorder.playing:
            messagebox.showwarning("提示", "回放中无法录制")
            return
        if not self.recorder.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.recorder.start_recording()
        self.rec_btn.config(text="停止录制  F8")
        self.play_btn.config(state='disabled')
        self._draw_dot(C_RECORD)
        self.status_text.config(text="录制中...", foreground=C_RECORD)
        self._poll_recording()

    def _poll_recording(self):
        if not self.recorder.recording:
            return
        elapsed = time.perf_counter() - self.recorder.record_start_time
        self._update_recording_ui(len(self.recorder.events), elapsed)
        self._poll_job = self.root.after(200, self._poll_recording)

    def _stop_recording(self):
        if self._poll_job:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        filepath = self.recorder.stop_recording()
        self.rec_btn.config(text="开始录制  F8")
        self.play_btn.config(state='normal')
        self._draw_dot(C_SUCCESS)
        self.status_text.config(text="就绪", foreground=C_TEXT)
        self._refresh_file_list()
        if filepath:
            filename = os.path.basename(filepath)
            self.last_recording_filename = filename
            self._persist_last_session(filename=filename)
            self._update_history_bar(filename)

    def _toggle_playback(self):
        if self.recorder.recording:
            messagebox.showwarning("提示", "录制中无法回放")
            return
        if self.recorder.playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        sel = self.file_tree.selection()
        if sel:
            filename = self.file_tree.item(sel[0], 'values')[0]
            filepath = os.path.join(RECORD_DIR, filename)
        else:
            filepath = None

        try:
            loop = int(self.loop_var.get())
        except ValueError:
            loop = 1

        ok = self.recorder.start_playback(filepath=filepath, loop_count=loop)
        if not ok:
            messagebox.showwarning("提示", "没有可用的录制文件")
            return

        # 标记为上次使用
        if filepath:
            fname = os.path.basename(filepath)
            self._persist_last_session(filename=fname)
            self._update_history_bar(fname)

        self.play_btn.config(text="停止回放  F9")
        self.rec_btn.config(state='disabled')
        self.stop_btn.config(text="强制停止  F10")
        self._draw_dot(C_PLAY)
        self.status_text.config(text="回放中...", foreground=C_PLAY)

    def _stop_playback(self):
        self.recorder.stop_playback()

    def _force_stop(self):
        if self._poll_job:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        if self.recorder.recording:
            self._stop_recording()
        if self.recorder.playing:
            self.recorder.stop_playback()
        self.rec_btn.config(text="开始录制  F8", state='normal')
        self.play_btn.config(text="回放  F9", state='normal')
        self.stop_btn.config(text="强制停止  F10")
        self._draw_dot(C_SUCCESS)
        self.status_text.config(text="就绪", foreground=C_TEXT)

    # ========== 文件列表 (Treeview) ==========

    def _refresh_file_list(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        files = sorted(
            [f for f in os.listdir(RECORD_DIR) if f.endswith('.json')],
            reverse=True,
        )

        for f in files:
            path = os.path.join(RECORD_DIR, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                created = data.get('created', '?')
                date_str = f"{created[:4]}-{created[4:6]}-{created[6:8]}"
                dur = f"{data.get('duration', 0):.1f}s"
                cnt = str(data.get('event_count', 0))
            except Exception:
                date_str, dur, cnt = '?', '?', '?'

            # 判断是否为上次录制
            tag = 'last' if f == self.last_recording_filename else ''
            self.file_tree.insert('', 'end', values=(f, date_str, dur, cnt), tags=(tag,))

        # 样式标记上次录制
        self.file_tree.tag_configure('last', background='#ede9fe', font=('Consolas', 9, 'bold'))

        if not files:
            self.file_tree.insert('', 'end', values=('（暂无录制文件）', '', '', ''))

    def _delete_selected(self):
        sel = self.file_tree.selection()
        if not sel:
            return
        filename = self.file_tree.item(sel[0], 'values')[0]
        if messagebox.askyesno("确认删除", f"删除 {filename}？"):
            os.remove(os.path.join(RECORD_DIR, filename))
            if filename == self.last_recording_filename:
                self.last_recording_filename = None
                self._persist_last_session(filename=None)
            self._refresh_file_list()

    # ========== 回调 ==========

    def _on_status_change(self, status, info):
        self.root.after(0, lambda: self._update_status_ui(status, info))

    def _update_status_ui(self, status, info):
        if status == "idle":
            self.rec_btn.config(text="开始录制  F8", state='normal')
            self.play_btn.config(text="回放  F9", state='normal')
            self.stop_btn.config(text="强制停止  F10")
            self._draw_dot(C_SUCCESS)
            self.status_text.config(text="就绪", foreground=C_TEXT)
            self.event_count_label.config(text="事件: 0")
            self.duration_label.config(text="时长: 0.0s")

    def _update_recording_ui(self, count, elapsed):
        self.event_count_label.config(text=f"事件: {count}")
        self.duration_label.config(text=f"时长: {elapsed:.1f}s")

    def _on_close(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        self._persist_last_session()
        self.recorder.stop_playback()
        if self.recorder.recording:
            self.recorder.stop_recording()
        self.root.destroy()
        sys.exit(0)


def main():
    MacroGUI()


if __name__ == "__main__":
    main()
