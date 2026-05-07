#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
键盘鼠标宏录制与回放工具
  F8  - 开始/停止录制
  F9  - 回放最近一次录制
  F10 - 强制停止回放

用法:
  python macro_recorder.py              # 默认循环 1 次
  python macro_recorder.py -n 5         # 回放 5 次
  python macro_recorder.py -n 0         # 无限循环
  python macro_recorder.py -l           # 列出所有录制文件
  python macro_recorder.py -p 文件名    # 回放指定文件
"""

import json
import os
import sys
import time
import threading
from datetime import datetime
from pynput import mouse, keyboard as pynput_kb
import keyboard


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORD_DIR = os.path.join(SCRIPT_DIR, "recordings")

# 特殊键映射表
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

CONTROL_KEYS = {'f8', 'f9', 'f10'}  # 录制时忽略的控制热键


class MacroRecorder:
    def __init__(self, loop_count=1):
        self.events = []
        self.recording = False
        self.playing = False
        self.stop_playback_flag = False
        self.record_start_time = 0
        self.loop_count = loop_count if loop_count > 0 else float('inf')

        self.mouse_ctrl = mouse.Controller()
        self.kb_ctrl = pynput_kb.Controller()
        self.mouse_listener = None
        self.kb_listener = None

        os.makedirs(RECORD_DIR, exist_ok=True)
        self._setup_hotkeys()

    # ========== 热键 ==========

    def _setup_hotkeys(self):
        keyboard.add_hotkey('f8', self._toggle_recording, suppress=False)
        keyboard.add_hotkey('f9', self._start_playback, suppress=False)
        keyboard.add_hotkey('f10', self._force_stop, suppress=False)

    def _toggle_recording(self):
        if self.playing:
            print("[提示] 回放中无法录制，请先按 F10 停止回放")
            return
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording()

    # ========== 录制 ==========

    def _start_recording(self):
        self.events = []
        self.recording = True
        self.record_start_time = time.time()
        print(f"\n🔴 录制中... (按 F8 停止)")

        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.mouse_listener.start()

        self.kb_listener = pynput_kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self.kb_listener.start()

    def _stop_recording(self):
        if not self.recording:
            return
        self.recording = False

        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.kb_listener:
            self.kb_listener.stop()

        duration = time.time() - self.record_start_time
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

        print(f"⏹️ 录制停止 — {len(self.events)} 个事件，{duration:.1f} 秒")
        print(f"   已保存: {filepath}")

    def _on_mouse_click(self, x, y, button, pressed):
        if not self.recording:
            return
        self.events.append({
            "type": "mouse_click",
            "x": x, "y": y,
            "button": button.name,
            "action": "press" if pressed else "release",
            "time": round(time.time() - self.record_start_time, 4),
        })

    def _on_key_press(self, key):
        if not self.recording:
            return
        key_name = self._key_to_name(key)
        if key_name in CONTROL_KEYS:
            return
        self.events.append({
            "type": "key_press",
            "key": key_name,
            "time": round(time.time() - self.record_start_time, 4),
        })

    def _on_key_release(self, key):
        if not self.recording:
            return
        key_name = self._key_to_name(key)
        if key_name in CONTROL_KEYS:
            return
        self.events.append({
            "type": "key_release",
            "key": key_name,
            "time": round(time.time() - self.record_start_time, 4),
        })

    def _key_to_name(self, key):
        try:
            return key.char
        except AttributeError:
            return str(key).replace('Key.', '')

    # ========== 回放 ==========

    def _start_playback(self, filepath=None):
        if self.recording:
            print("[提示] 录制中，请先按 F8 停止录制")
            return
        if self.playing:
            print("[提示] 已在回放中，按 F10 停止")
            return

        if filepath:
            target = filepath
            if not os.path.exists(target):
                print(f"[错误] 文件不存在: {filepath}")
                return
        else:
            recordings = sorted(
                [f for f in os.listdir(RECORD_DIR) if f.endswith('.json')],
                reverse=True,
            )
            if not recordings:
                print("[提示] 没有录制文件，请先按 F8 录制")
                return
            target = os.path.join(RECORD_DIR, recordings[0])

        with open(target, 'r', encoding='utf-8') as f:
            data = json.load(f)

        events = data.get("events", [])
        loop_count = data.get("loop_count", self.loop_count)
        if loop_count == 0:
            loop_count = float('inf')
        duration = data.get("duration", 0)

        print(f"\n▶️ 回放: {os.path.basename(target)}")
        print(f"   事件: {len(events)} | 时长: {duration}s | 循环: {'∞' if loop_count == float('inf') else loop_count} 次")
        print(f"   按 F10 停止")

        self.playing = True
        self.stop_playback_flag = False
        threading.Thread(
            target=self._playback_loop,
            args=(events, loop_count, duration),
            daemon=True,
        ).start()

    def _playback_loop(self, events, loop_count, duration):
        loop = 0
        while loop < loop_count:
            if self.stop_playback_flag:
                break
            loop += 1

            if loop_count != 1:
                print(f"   第 {loop}/{int(loop_count) if loop_count != float('inf') else '∞'} 次循环...")

            loop_start = time.time()
            for event in events:
                if self.stop_playback_flag:
                    break
                target_time = loop_start + event["time"]
                wait = target_time - time.time()
                if wait > 0:
                    time.sleep(wait)
                if not self.stop_playback_flag:
                    self._execute_event(event)

        self.playing = False
        if self.stop_playback_flag:
            print("⏹️ 回放已强制停止")
        else:
            print("✅ 回放完成")

    def _execute_event(self, event):
        try:
            if event["type"] == "key_press":
                self.kb_ctrl.press(self._name_to_key(event["key"]))
            elif event["type"] == "key_release":
                self.kb_ctrl.release(self._name_to_key(event["key"]))
            elif event["type"] == "mouse_click":
                self.mouse_ctrl.position = (event["x"], event["y"])
                btn = BUTTON_MAP.get(event["button"], mouse.Button.left)
                if event["action"] == "press":
                    self.mouse_ctrl.press(btn)
                else:
                    self.mouse_ctrl.release(btn)
        except Exception as e:
            print(f"[警告] 执行事件异常: {event}, 原因: {e}")

    def _name_to_key(self, name):
        if name in SPECIAL_KEYS:
            return SPECIAL_KEYS[name]
        return name

    def _force_stop(self):
        if self.recording:
            self._stop_recording()
        if self.playing:
            self.stop_playback_flag = True
            print("\n⏹️ 正在停止回放...")

    def run(self):
        print("=" * 48)
        print("   ⌨️ 🖱️  键鼠宏录制/回放工具")
        print("=" * 48)
        print("   F8  - 开始/停止录制")
        print("   F9  - 回放最近一次录制")
        print("   F10 - 强制停止回放")
        print(f"   录制目录: {RECORD_DIR}")
        print("   按 Ctrl+C 退出")
        print("=" * 48)

        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n👋 已退出")


# ========== 命令行入口 ==========

def list_recordings():
    """列出所有录制文件"""
    files = sorted(
        [f for f in os.listdir(RECORD_DIR) if f.endswith('.json')],
        reverse=True,
    )
    if not files:
        print("没有录制文件。")
        return
    print(f"录制文件 ({len(files)} 个):")
    for i, f in enumerate(files, 1):
        path = os.path.join(RECORD_DIR, f)
        with open(path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        print(f"  {i}. {f}")
        print(f"     时间: {data.get('created','?')} | 事件: {data.get('event_count',0)} | 时长: {data.get('duration',0)}s | 循环: {data.get('loop_count',1)}")


def main():
    loop_count = 1
    target_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '-n':
            i += 1
            if i < len(args):
                try:
                    loop_count = int(args[i])
                except ValueError:
                    print(f"'n' 参数必须是整数: {args[i]}")
                    sys.exit(1)
        elif args[i] == '-l':
            list_recordings()
            return
        elif args[i] == '-p':
            i += 1
            if i < len(args):
                target_file = args[i]
        elif args[i] in ('-h', '--help'):
            print(__doc__)
            return
        i += 1

    recorder = MacroRecorder(loop_count=loop_count)

    if target_file:
        # 直接回放指定文件然后退出
        print(f"回放指定文件: {target_file}")
        print("按 F10 停止，回放完成后自动退出\n")
        # 延迟一小段时间后开始回放
        def delayed_play():
            time.sleep(0.5)
            recorder._start_playback(filepath=target_file)
        threading.Thread(target=delayed_play, daemon=True).start()
    try:
        recorder.run()
    except KeyboardInterrupt:
        print("\n👋 已退出")
    sys.exit(0)


if __name__ == "__main__":
    main()
