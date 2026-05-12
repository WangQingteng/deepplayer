# DeepPlayer

基于 PySide6 + libVLC 的跨平台视频播放器。

## 支持平台

- Windows
- Linux
- macOS

## 功能特性

- 播放、暂停、停止、快进、音量控制
- 全屏模式（F / Esc）
- 播放列表，支持拖放、排序、添加/移除
- 从文件管理器拖放文件或文件夹
- 打开文件夹 — 添加目录中所有媒体文件
- 完整的键盘快捷键
- 自动播放播放列表中的下一首
- 循环播放模式
- 字幕加载 + 延迟调节
- 音轨切换
- 画面比例控制
- 深色主题

## 环境要求

1. **Python 3.10+**
2. **VLC** 必须安装在系统中：
   - Windows: https://www.videolan.org/vlc/
   - Linux: `sudo apt install vlc`（或等效命令）
   - macOS: `brew install --cask vlc`（或从 videolan.org 下载）
3. **python-vlc** — Python 绑定（通过 pip 安装，见下文）

> ⚠️ VLC 的架构（32/64 位）必须与 Python 匹配。如果使用 64 位 Python，请安装 64 位 VLC。

## 安装

```bash
cd video_player
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

或直接打开文件：

```bash
python main.py "path/to/video.mp4"
```

## 键盘快捷键

| 按键 | 功能 |
|------|------|
| **空格** | 播放 / 暂停 |
| **Ctrl+.** | 停止 |
| **F** | 切换全屏 |
| **Esc** | 退出全屏 |
| **← →** | 快进/快退 ±5 秒 |
| **Shift+← →** | 快进/快退 ±1 秒 |
| **Ctrl+← →** | 上一首 / 下一首 |
| **Ctrl+Shift+← →** | 快进/快退 ±15 秒 |
| **↑ ↓** | 音量 ±5 |
| **Ctrl+↑ ↓** | 音量 ±5 |
| **M** | 静音 |
| **P** | 切换播放列表面板 |
| **0-9** | 跳转到 0%-90% 位置 |
| **Ctrl+O** | 打开文件 |
| **Ctrl+T** | 下一音轨 |
| **Ctrl+/** | 显示快捷键 |
| **Ctrl+Q** | 退出 |

## 项目结构

```
video_player/
├── main.py              # 入口文件、深色主题、命令行参数
├── player.py            # VLCPlayer — 封装 libVLC，通过 Qt 信号通信
├── requirements.txt
├── README.md
└── ui/
    ├── __init__.py
    ├── main_window.py   # 主窗口 — 菜单、快捷键、拖放、信号连接
    ├── video_widget.py  # 承载 VLC 视频输出的 QFrame
    ├── controls.py      # 控制栏 — 播放/暂停、进度条、音量
    └── playlist_widget.py  # 播放列表 — 列表、文件对话框、排序
```

## 支持的格式

所有 VLC/ffmpeg 支持的格式，包括：

**视频:** MP4、MKV、AVI、WebM、MOV、WMV、FLV、M4V、MPG/MPEG、3GP、OGV、TS、VOB、DivX、ASF、RM/RMVB、M2TS、F4V

**音频:** MP3、FLAC、AAC、OGG、WAV、WMA、M4A、Opus

## 构建（独立可执行文件）

将 DeepPlayer 打包为独立文件夹，无需 Python 即可运行。

### 前置条件

```bash
pip install pyinstaller
```

### 构建

```bash
python build.py
```

此命令将：
1. 定位 VLC 安装目录，将其 DLL 和插件复制到打包目录中
2. 运行 PyInstaller 冻结所有 Python 代码和 Qt 依赖
3. 输出自包含的文件夹到 `dist/DeepPlayer/`

如果构建时未安装 VLC，仍会生成包，但目标机器必须安装 VLC 才能播放媒体。

### 清理

```bash
python build.py --clean
```

### 构建输出

```
dist/DeepPlayer/
├── DeepPlayer.exe        # 启动此文件（无需 Python）
├── libvlc.dll            # 捆绑的 VLC 运行时
├── libvlccore.dll
├── plugins/              # VLC 编解码器
└── _internal/            # PyInstaller 依赖
```

分发方式：将整个 `dist/DeepPlayer/` 文件夹压缩后分享。接收者直接运行 `DeepPlayer.exe` — 无需 Python，无需安装。

> ⚠️ **架构说明:** 打包产物与架构绑定。64 位构建需要目标系统安装 64 位 VLC。请分别针对不同平台和架构进行构建。
