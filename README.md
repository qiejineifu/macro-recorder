# 键鼠宏录制/回放工具

一个 Python 桌面工具，用于录制键盘按键和鼠标点击操作，并能精确回放，帮助减少重复性工作。

## 功能特性

- **录制键盘按键和鼠标点击** — 实时记录操作序列和时间间隔
- **精确回放** — 使用 `perf_counter` 高精度时钟 + 自旋忙等待，误差 < 1ms
- **循环回放** — 支持设定 1~9999 次循环或无限循环
- **全局热键** — F8 录制、F9 回放、F10 强制停止，即使窗口不在前台也能用
- **JSON 存储** — 录制文件可手动编辑修改
- **上次录制记忆** — 关闭后重新打开自动加载上次录制
- **DPI 感知** — 自动适配高 DPI 屏幕，鼠标位置不偏移
- **独立打包** — 可打包为单个 exe 文件，无需安装 Python

## 系统要求

- Windows 10 / 11
- Python 3.10+（仅在从源码运行时需要）

## 快速开始

### 方式一：直接运行 exe（推荐）

从 [Releases](https://github.com/qiejineifu/macro-recorder/releases) 页面下载最新版 `MacroRecorder.exe`，双击运行即可。录制文件和配置自动保存在 exe 所在目录。

### 方式二：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/qiejineifu/macro-recorder.git
cd macro-recorder

# 2. 安装依赖
pip install pynput

# 3. 运行 GUI
python macro_gui.py
```

### 方式三：命令行模式

```bash
python macro_recorder.py              # 默认循环 1 次
python macro_recorder.py -n 5         # 回放 5 次
python macro_recorder.py -n 0         # 无限循环（F10 停止）
python macro_recorder.py -l           # 列出所有录制文件
python macro_recorder.py -p 文件名    # 回放指定文件
```

## 操作指南

### 热键

| 热键 | 功能 |
|------|------|
| `F8` | 开始录制 / 停止录制 |
| `F9` | 开始回放 / 停止回放 |
| `F10` | 强制停止录制或回放 |

### 录制

1. 点击「开始录制」或按 `F8`
2. 执行你需要录制的键盘和鼠标操作
3. 再次按 `F8` 或点击按钮停止录制

录制文件自动保存为 `recordings/macro_YYYYMMDD_HHMMSS.json`。

### 回放

1. 在文件列表中双击选中一个录制文件，或在列表中选择后点击「回放」
2. 设置循环次数（1 = 单次，0 = 无限）
3. 点击「回放」或按 `F9` 开始
4. 按 `F10` 可随时强制停止

### 界面说明

```
┌──────────────────────────────────────┐
│    键鼠宏录制 / 回放                  │
├──────────────────────────────────────┤
│  上次录制: macro_xxx.json (2.5s·126)  │  ← 紫色信息栏，自动记忆
├──────────────────────────────────────┤
│  ● 就绪    事件: 0    时长: 0.0s     │  ← 状态指示
├──────────────────────────────────────┤
│  [开始录制 F8]    [回放 F9]          │  ← 操作按钮
│  [强制停止 F10]                      │
│  循环次数: [  1  ]                   │  ← 循环设置
├──────────────────────────────────────┤
│  录制文件                     │▲│    │  ← 文件列表
│  ┌──────────────────────────────┐    │
│  │ macro_20260507_120000.json  │    │
│  │ 2026-05-07 │ 2.5s │ 126    │    │
│  └──────────────────────────────┘    │
│  [刷新]  [删除]                      │
└──────────────────────────────────────┘
```

## 录制文件格式

录制文件使用 JSON 格式，可以手动编辑：

```json
{
  "created": "20260507_120000",
  "duration": 2.5,
  "event_count": 4,
  "loop_count": 1,
  "events": [
    {"type": "key_press",    "key": "a", "time": 0.0},
    {"type": "key_release",  "key": "a", "time": 0.12},
    {"type": "mouse_click",  "button": "left", "action": "press",
     "x": 523, "y": 341, "time": 0.5},
    {"type": "mouse_click",  "button": "left", "action": "release",
     "x": 523, "y": 341, "time": 0.65}
  ]
}
```

### 事件类型

| type | 说明 | 字段 |
|------|------|------|
| `key_press` | 键盘按下 | `key`, `time` |
| `key_release` | 键盘释放 | `key`, `time` |
| `mouse_click` | 鼠标点击 | `button`, `action`, `x`, `y`, `time` |

### 特殊键名

```
ctrl, shift, alt, enter, tab, space, esc, backspace, delete,
insert, home, end, page_up, page_down, up, down, left, right,
f1 ~ f12, caps_lock, num_lock, print_screen
```

### 编辑技巧

- 修改 `time` 值可以调整操作节奏（数值越大间隔越久）
- 修改 `x`、`y` 可以调整鼠标点击位置
- 修改 `loop_count` 可以修改默认循环次数
- 可以删除不需要的事件来跳过某些操作

## 打包为 exe

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "MacroRecorder" macro_gui.py
```

生成的 exe 在 `dist/MacroRecorder.exe`。

## 注意事项

- 录制时 `F8`、`F9`、`F10` 不会被录入，保证控制键不受影响
- 回放是在**绝对屏幕坐标**上进行，请确保回放时屏幕分辨率和布局与录制时一致
- 本工具模拟的是桌面应用级别的输入，**不适用于游戏**（游戏通常使用 DirectInput 直接读取硬件信号）
- 请勿在需要身份验证、金融操作等敏感场景使用

## 项目结构

```
macro-recorder/
├── macro_gui.py          # GUI 主程序 (tkinter)
├── macro_recorder.py     # 命令行版本
├── run.bat               # Windows 一键启动脚本
├── recordings/           # 录制文件目录（本地，不上传 git）
├── config.json           # 用户配置（本地，不上传 git）
└── .gitignore
```

## 许可

MIT License
