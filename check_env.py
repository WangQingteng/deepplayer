# -*- coding: utf-8 -*-
"""Quick sanity check for DeepPlayer."""
import sys
import os

# Workaround for python-vlc on Windows without ProgramFiles env var
if sys.platform == "win32":
    os.environ.setdefault("ProgramFiles", r"C:\Program Files")
    os.environ.setdefault("HOMEDRIVE", "C:")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("DeepPlayer Environment Check")
print("=" * 50)

# Test VLC availability
print("\n[1] Checking VLC...")
vlc_ok = False
try:
    import vlc
    print(f"  python-vlc version: {vlc.__version__}")
    try:
        inst = vlc.Instance("--quiet")
        ver = vlc.libvlc_get_version().decode()
        print(f"  libVLC: {ver}")
        vlc_ok = True
    except Exception as e:
        print(f"  VLC runtime error: {e}")
except Exception as e:
    print(f"  python-vlc import error: {type(e).__name__}: {e}")

if not vlc_ok:
    print()
    print("  VLC is NOT installed or not found.")
    print("  Download from: https://www.videolan.org/vlc/")
    print("  IMPORTANT: 64-bit Python requires 64-bit VLC.")

# Test import chain (independent of VLC runtime)
print("\n[2] Checking module imports...")
for mod in ["player", "ui.video_widget", "ui.controls",
             "ui.playlist_widget", "ui.main_window"]:
    try:
        __import__(mod)
        print(f"  OK  {mod}")
    except Exception as e:
        print(f"  FAIL {mod}: {type(e).__name__}: {e}")

print()
if vlc_ok:
    print("All checks passed. DeepPlayer is ready.")
    print("Run: python main.py")
else:
    print("Module imports OK, but VLC is required to run.")
    print("Install VLC, then run: python main.py")
