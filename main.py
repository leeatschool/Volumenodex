"""Application entry point for Volumenodex Word Processing Studio."""

import sys
import os

# Ensure the package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, qInstallMessageHandler, QtMsgType
from PySide6.QtWidgets import QApplication
from volumenodex.ui.main_window import MainWindow


# Suppress harmless DirectWrite warnings natively at Qt C++ level
os.environ.setdefault("QT_LOGGING_RULES", "qt.text.directwrite.warning=false;qt.gui.fonts=false")


def _qt_message_handler(mode, context, message):
    try:
        if not message:
            return
        # Filter known harmless DirectWrite warnings for legacy DOS raster fonts (8514oem, Fixedsys)
        if "DirectWrite: CreateFontFaceFromHDC" in message or "CreateFontFace" in message:
            return
        if "PointSize <= 0" in message or "point size <= 0" in message.lower():
            return
        if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            if sys.stderr is not None and hasattr(sys.stderr, "write"):
                sys.stderr.write(f"{message}\n")
    except Exception:
        pass


def main():
    # Hide console window on Windows when launched without a dedicated terminal
    if sys.platform == "win32" and "--console" not in sys.argv and "pytest" not in sys.modules:
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
        except Exception:
            pass

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("volumenodex.wordprocessing.studio.1.0")
        except Exception:
            pass

    try:
        qInstallMessageHandler(_qt_message_handler)
    except Exception:
        pass
    # Configure high-DPI behavior
    app = QApplication(sys.argv)
    app.setApplicationName("Volumenodex")
    app.setApplicationDisplayName("Volumenodex Word Studio")
    app.setOrganizationName("Volumenodex")

    # Set application icon
    from PySide6.QtGui import QIcon
    icon_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "volumenodex", "resources", "app_icon.png"),
    ]
    for p in icon_candidates:
        if os.path.exists(p):
            ico = QIcon(p)
            if not ico.isNull():
                app.setWindowIcon(ico)
                break

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
