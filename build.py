#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepPlayer 构建脚本 — 打包为独立目录。

Usage:
    python build.py               # 为当前平台构建
    python build.py --clean       # 清理之前的构建产物
    python build.py --download-vlc # 自动下载 VLC 并捆绑

Output: dist/DeepPlayer/
  - DeepPlayer.exe (or DeepPlayer on Linux/macOS)
  - libvlc.dll, libvlccore.dll, plugins/  (bundled VLC)
  - _internal/  (PyInstaller dependencies)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.resolve()
SRC_DIR = PROJECT_ROOT
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "DeepPlayer.spec"
NAME = "DeepPlayer"
MAIN_SCRIPT = "main.py"

# ── 平台检测 ────────────────────────────────────────────

PLATFORM = sys.platform  # "win32", "linux", "darwin"
IS_WINDOWS = PLATFORM == "win32"
IS_LINUX = PLATFORM == "linux"
IS_MACOS = PLATFORM == "darwin"


def find_vlc_path() -> Path | None:
    """定位当前平台的 VLC 安装目录。"""
    if IS_WINDOWS:
        # 常见 VLC 安装路径（先 64 位，再 32 位）
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "VideoLAN" / "VLC",
            Path("C:\\Program Files (x86)") / "VideoLAN" / "VLC",
            Path(os.environ.get("LOCALAPPDATA", "")) / "VideoLAN" / "VLC",
        ]
        for p in candidates:
            if (p / "libvlc.dll").exists() and (p / "libvlccore.dll").exists():
                return p

        # 尝试从 PATH 查找
        for d in os.environ.get("PATH", "").split(os.pathsep):
            pd = Path(d)
            if (pd / "libvlc.dll").exists() and (pd / "libvlccore.dll").exists():
                return pd

        return None

    elif IS_LINUX:
        # 检查 libvlc.so 是否可找到
        import ctypes.util
        lib = ctypes.util.find_library("vlc")
        if lib:
            lib_path = Path(lib).resolve()
            # Usually /usr/lib/x86_64-linux-gnu/libvlc.so -> same dir
            return lib_path.parent
        # 回退到发行版安装路径
        candidates = [
            Path("/usr/lib/x86_64-linux-gnu"),
            Path("/usr/lib64"),
            Path("/usr/lib"),
        ]
        for p in candidates:
            vlc_dirs = list(p.glob("vlc*"))
            if vlc_dirs:
                return p
        return None

    elif IS_MACOS:
        vlc_app = Path("/Applications/VLC.app/Contents/MacOS")
        if vlc_app.exists():
            return vlc_app
        return None

    return None


# ── VLC 下载（适用于未安装 VLC 的系统）─

VLC_DOWNLOAD_URLS = {
    # 最新稳定版 VLC 3.x 便携包（官方镜像）
    "win32": (
        "win64",
        "https://download.videolan.org/pub/videolan/vlc/3.0.21/win64/vlc-3.0.21-win64.zip",
        "vlc-3.0.21",
    ),
    # 按需添加其他平台
}


def download_vlc() -> Path | None:
    """下载 VLC 便携版并解压 DLL。返回 VLC 目录路径。"""
    import tempfile
    import zipfile
    import urllib.request
    import ssl

    if IS_WINDOWS:
        # 绕过缺少证书环境下的 SSL 验证
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        arch_key, url, folder_name = VLC_DOWNLOAD_URLS["win32"]
        print(f"  正在从 {url} 下载 VLC")
        print("  （可能需要几分钟 — VLC 约 50 MB）")

        temp_dir = Path(tempfile.mkdtemp(prefix="vlc_dl_"))
        zip_path = temp_dir / "vlc.zip"

        try:
            # Download with custom SSL context
            print("    正在连接...")
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 DeepPlayer Build Script"
            })
            resp = urllib.request.urlopen(req, context=ssl_ctx)
            total = int(resp.headers.get("Content-Length", 0))

            downloaded = 0
            chunk_size = 8192
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(100, downloaded * 100 // total)
                        if pct % 10 == 0:
                            print(f"    {pct}%...", end="", flush=True)
            print(" 100%")

            # Extract
            print("  正在解压...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Only extract libvlc DLLs and plugins (save time and space)
                members = [
                    m for m in zf.namelist()
                    if m.startswith(f"{folder_name}/")
                    and any(
                        m.endswith(ext) or "plugins" in m or "libvlc" in m
                        for ext in [".dll"]
                    )
                ]
                if not members:
                    # 回退：解压所有内容
                    zf.extractall(temp_dir)
                else:
                    zf.extractall(temp_dir, members=members)

            vlc_extracted = temp_dir / folder_name
            if (vlc_extracted / "libvlc.dll").exists():
                print(f"  VLC 解压至: {vlc_extracted}")
                return vlc_extracted
            else:
                print("  错误: 解压的 VLC 缺少 libvlc.dll")
                return None

        except Exception as e:
            print(f"  下载 VLC 出错: {e}")
            return None
        finally:
            # Clean up the zip but keep extracted files
            if zip_path.exists():
                zip_path.unlink()

    else:
        print("  自动下载目前仅支持 Windows。")
        print("  请通过包管理器安装 VLC。")
        return None


def copy_vlc_deps(vlc_dir: Path, dist_dir: Path) -> bool:
    """将 VLC DLL 和插件复制到分发目录中。

    成功返回 True。
    """
    print(f"  VLC 来源: {vlc_dir}")

    if IS_WINDOWS:
        # 核心 DLL
        dlls = ["libvlc.dll", "libvlccore.dll"]
        for dll in dlls:
            src = vlc_dir / dll
            dst = dist_dir / dll
            if src.exists():
                shutil.copy2(src, dst)
                print(f"    已复制 {dll}")
            else:
                print(f"    警告: 在 {src} 未找到 {dll}")

        # Plugins directory (essential for codec support)
        plugins_src = vlc_dir / "plugins"
        plugins_dst = dist_dir / "plugins"
        if plugins_src.is_dir():
            if plugins_dst.exists():
                shutil.rmtree(plugins_dst)
            shutil.copytree(plugins_src, plugins_dst,
                            ignore=shutil.ignore_patterns("*.a", "*.la", "*.def"))
            plugin_count = sum(1 for _ in plugins_dst.rglob("*") if _.is_file())
            print(f"    已复制 plugins/ ({plugin_count} 个文件)")
        else:
            print(f"    警告: 在 {plugins_src} 未找到 plugins/")
            return False

        # 同时复制 vlc.exe 路径信息供 python-vlc 回退使用
        # (not mandatory but helps discovery)
        vlc_exe = vlc_dir / "vlc.exe"
        if vlc_exe.exists():
            shutil.copy2(vlc_exe, dist_dir / "vlc.exe")

        return True

    elif IS_LINUX:
        # On Linux, typically rely on system VLC being installed.
        # Python-vlc will find libvlc.so via ldconfig.
        # We can optionally bundle the .so files.
        print("    （Linux: 依赖系统 VLC 安装）")
        # Try to copy key .so files
        for lib in ["libvlc.so", "libvlc.so.5", "libvlccore.so", "libvlccore.so.9"]:
            candidates = [
                vlc_dir / lib,
                vlc_dir / f"x86_64-linux-gnu" / lib,
            ]
            for src in candidates:
                if src.exists():
                    dst = dist_dir / lib
                    shutil.copy2(src, dst)
                    print(f"    已复制 {lib}")
                    break
        return True

    elif IS_MACOS:
        # 从 .app 包中复制 VLC 库和插件
        lib_src = vlc_dir / "lib"
        plugins_src = vlc_dir / "plugins"
        lib_dst = dist_dir / "lib"
        plugins_dst = dist_dir / "plugins"
        if lib_src.exists():
            if lib_dst.exists():
                shutil.rmtree(lib_dst)
            shutil.copytree(lib_src, lib_dst)
            print(f"    已复制 lib/")
        if plugins_src.exists():
            if plugins_dst.exists():
                shutil.rmtree(plugins_dst)
            shutil.copytree(plugins_src, plugins_dst)
            print(f"    已复制 plugins/")
        return True

    return False


def run_pyinstaller(vlc_found: bool, vlc_dir: Path | None = None) -> bool:
    """运行 PyInstaller 构建应用打包。

    Args:
        vlc_found: 构建系统上是否已定位到 VLC。
                   若为 True，python-vlc 会捆绑到应用中。
                   若为 False，vlc 将被排除，目标机器必须安装 VLC。
    """
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", NAME,
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
        # Main script
        str(SRC_DIR / MAIN_SCRIPT),
        # Hidden imports — ensure all modules are found
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtNetwork",
        # Our internal modules (inside functions, so PyInstaller may miss them)
        "--hidden-import", "ui",
        "--hidden-import", "ui.main_window",
        "--hidden-import", "ui.video_widget",
        "--hidden-import", "ui.controls",
        "--hidden-import", "ui.playlist_widget",
        "--hidden-import", "player",
        # Collect PySide6 plugins (imageformats, platforms, styles, etc.)
        "--collect-all", "PySide6",
    ]

    # Bundle VLC DLLs and plugins into the single exe (--onefile)
    if vlc_dir is not None and vlc_dir.exists():
        sep = ";" if IS_WINDOWS else ":"
        if IS_WINDOWS:
            for dll in ["libvlc.dll", "libvlccore.dll"]:
                src = vlc_dir / dll
                if src.exists():
                    cmd += ["--add-binary", f"{src}{sep}."]
            plugins_src = vlc_dir / "plugins"
            if plugins_src.exists():
                cmd += ["--add-data", f"{plugins_src}{sep}plugins"]
        elif IS_LINUX:
            for lib in vlc_dir.glob("libvlc*.so*"):
                if lib.is_file():
                    cmd += ["--add-binary", f"{lib}{sep}."]
            plugins_src = vlc_dir.parent / "plugins"
            if plugins_src.exists():
                cmd += ["--add-data", f"{plugins_src}{sep}plugins"]
        elif IS_MACOS:
            for lib in vlc_dir.glob("libvlc*.dylib"):
                cmd += ["--add-binary", f"{lib}{sep}."]
            plugins_src = vlc_dir.parent / "plugins"
            if plugins_src.exists():
                cmd += ["--add-data", f"{plugins_src}{sep}plugins"]

    # Conditionally bundle python-vlc
    if vlc_found:
        cmd += [
            "--hidden-import", "vlc",
            "--collect-all", "vlc",
        ]
    else:
        # Exclude vlc so PyInstaller doesn't fail trying to import it
        cmd += ["--exclude-module", "vlc"]

    # Platform-specific
    if IS_WINDOWS:
        # Add icon if available
        icon_path = SRC_DIR / "icon.ico"
        if icon_path.exists():
            cmd += ["--icon", str(icon_path)]
    elif IS_MACOS:
        cmd += ["--osx-bundle-identifier", "com.deepplayer.app"]

    print(f"\n  正在运行: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(SRC_DIR))
    return result.returncode == 0


def _copy_vlc_py_module(dist_dir: Path):
    """手动将 python-vlc 模块文件复制到打包目录中。

    当 PyInstaller 的分析无法导入 vlc 时需要此操作
    （例如构建时原生 DLL 不在 PATH 中）。
    """
    import importlib.util
    spec = importlib.util.find_spec("vlc")
    if not spec or not spec.origin:
        print("    （此 Python 中未找到 python-vlc 模块 — 跳过）")
        return

    src = Path(spec.origin)
    # 复制到应用根目录和 _internal/
    targets = [dist_dir, dist_dir / "_internal"]
    for target in targets:
        if target.is_dir():
            dst = target / "vlc.py"
            if not dst.exists():
                shutil.copy2(str(src), str(dst))
                print(f"    已复制 vlc.py 至 {target.relative_to(dist_dir.parent)}")


def clean_artifacts():
    """删除之前的构建输出。"""
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            print(f"  正在删除 {d}")
            shutil.rmtree(d)
    if SPEC_FILE.exists():
        SPEC_FILE.unlink()


def main():
    args = sys.argv[1:]
    if "--clean" in args:
        print("正在清理...")
        clean_artifacts()
        print("完成。")
        return

    print("=" * 60)
    print("  DeepPlayer — 构建脚本")
    print(f"  平台: {PLATFORM}")
    print("=" * 60)

    # ── 步骤 1: 查找 VLC ──────────────────────────────────────
    print("\n[1/3] 正在定位 VLC 安装...")
    vlc_dir = find_vlc_path()

    if vlc_dir is None:
        print("\n  本地未找到 VLC。")
        if "--download-vlc" in args:
            print("  正在尝试下载 VLC...")
            vlc_dir = download_vlc()
        if vlc_dir is None:
            if "--skip-vlc" in args:
                print("  仍会创建打包应用，但目标机器必须安装 VLC 才能播放。")
                print("  继续...")
            else:
                print("\n  错误: 未找到 VLC 安装。请先安装 VLC，")
                print("  或使用 --download-vlc 自动下载，")
                print("  或使用 --skip-vlc 强制跳过（产物需在已安装 VLC 的系统上运行）。")
                sys.exit(1)
    else:
        print(f"  已找到 VLC: {vlc_dir}")

    # ── 步骤 2: PyInstaller ───────────────────────────────────
    steps_total = 3
    print(f"\n[2/{steps_total}] 正在运行 PyInstaller...")

    # If we downloaded VLC, add it to PATH so python-vlc can find
    # the DLLs during PyInstaller's import analysis.
    if vlc_dir is not None and IS_WINDOWS:
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(vlc_dir) + os.pathsep + old_path

    ok = run_pyinstaller(vlc_found=vlc_dir is not None, vlc_dir=vlc_dir)
    if not ok:
        print("\n  错误: PyInstaller 运行失败。")
        sys.exit(1)

    # ── 步骤 3: 验证输出 ──────────────────────────────────────
    exe_name = f"{NAME}.exe" if IS_WINDOWS else NAME
    exe_path = DIST_DIR / NAME / exe_name
    if not exe_path.exists():
        print(f"\n  错误: 未找到 {exe_path} — PyInstaller 可能失败。")
        sys.exit(1)

    if vlc_dir is None:
        print(f"\n[3/{steps_total}] 未捆绑 VLC（未找到），目标机器需自行安装。")
    else:
        print(f"\n[3/{steps_total}] VLC 已捆绑到输出目录中。")

    # ── 最终汇总 ────────────────────────────────────────
    print()
    print("=" * 60)
    print("  构建完成！")
    exe_name = f"{NAME}.exe" if IS_WINDOWS else NAME
    exe_path = DIST_DIR / NAME / exe_name
    print(f"  输出目录: {DIST_DIR / NAME}")
    if exe_path.exists():
        size_mb = sum(f.stat().st_size for f in (DIST_DIR / NAME).rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  总大小: {size_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
