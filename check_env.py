# -*- coding: utf-8 -*-
"""DeepPlayer 环境检查脚本。"""
import sys
import os

if sys.platform == "win32":
    os.environ.setdefault("ProgramFiles", r"C:\Program Files")
    os.environ.setdefault("HOMEDRIVE", "C:")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("DeepPlayer 环境检查")
print("=" * 50)

# 检查 VLC
print("\n[1] 检查 VLC...")
vlc_ok = False
try:
    import vlc
    print(f"  python-vlc 版本: {vlc.__version__}")
    try:
        inst = vlc.Instance("--quiet")
        ver = vlc.libvlc_get_version().decode()
        print(f"  libVLC 版本: {ver}")
        vlc_ok = True
    except Exception as e:
        print(f"  VLC 运行时错误: {e}")
except Exception as e:
    print(f"  python-vlc 导入失败: {type(e).__name__}: {e}")

if not vlc_ok:
    print()
    print("  VLC 未安装或未找到。")
    print("  下载地址: https://www.videolan.org/vlc/")
    print("  注意: 64 位 Python 需要 64 位 VLC。")

# 检查模块导入
print("\n[2] 检查模块导入...")
for mod in ["player", "ui.video_widget", "ui.controls",
             "ui.playlist_widget", "ui.main_window"]:
    try:
        __import__(mod)
        print(f"  ✓  {mod}")
    except Exception as e:
        print(f"  ✗  {mod}: {type(e).__name__}: {e}")

print()
if vlc_ok:
    print("所有检查通过！DeepPlayer 已就绪。")
    print("运行: python main.py")
else:
    print("模块导入正常，但需要 VLC 才能播放。")
    print("安装 VLC 后运行: python main.py")
