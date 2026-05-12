# 贡献指南

欢迎提交 Issue 和 Pull Request。

## 开发环境设置

1. Fork 本仓库并克隆到本地
2. 创建虚拟环境：
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 确保系统已安装 VLC（见 README 环境要求）

## 环境检查

```bash
python check_env.py
```

## 提交 PR 前

- 至少在 Windows / Linux / macOS 中一个平台测试
- 描述清楚改动内容和原因
- 保持代码风格与项目一致

## 项目结构

```
video_player/
├── main.py              # 入口文件
├── player.py            # VLC 播放器封装
├── check_env.py         # 环境检查脚本
├── build.py             # 打包脚本
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
└── ui/
    ├── main_window.py   # 主窗口
    ├── video_widget.py  # 视频渲染区
    ├── controls.py      # 控制栏
    └── playlist_widget.py  # 播放列表
```
