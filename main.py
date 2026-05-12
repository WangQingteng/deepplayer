"""DeepPlayer — Cross-platform video player."""
import sys
import os

# Add parent to path for development convenience
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DeepPlayer")
    app.setOrganizationName("DeepPlayer")
    app.setApplicationDisplayName("DeepPlayer — 视频播放器")

    # Dark palette
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, "#1e1e1e")
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, "#2d2d2d")
    palette.setColor(palette.ColorRole.AlternateBase, "#353535")
    palette.setColor(palette.ColorRole.ToolTipBase, "#2d2d2d")
    palette.setColor(palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Button, "#353535")
    palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(palette.ColorRole.Link, "#42a5f5")
    palette.setColor(palette.ColorRole.Highlight, "#42a5f5")
    palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

    # Stylesheet tweaks
    app.setStyleSheet("""
        QToolTip { color: #ffffff; background-color: #2d2d2d; border: 1px solid #555; padding: 2px; }
        QMenu { background-color: #2d2d2d; color: #fff; border: 1px solid #555; }
        QMenu::item:selected { background-color: #42a5f5; }
        QSlider::groove:horizontal { border: 1px solid #555; height: 4px; background: #555; margin: 2px 0; border-radius: 2px; }
        QSlider::handle:horizontal { background: #42a5f5; border: none; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
        QSlider::sub-page:horizontal { background: #42a5f5; border-radius: 2px; }
        QListWidget { background-color: #252525; border: 1px solid #444; color: #ccc; }
        QListWidget::item:selected { background-color: #42a5f5; color: #000; }
        QListWidget::item:hover { background-color: #3a3a3a; }
    """)

    window = MainWindow()

    # Handle file arguments (open with)
    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
