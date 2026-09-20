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
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("volumenodex.wordprocessing.studio.2.2")
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

    # Set application icon (prioritizing multi-resolution .ico)
    from PySide6.QtGui import QIcon
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_candidates = [
        os.path.join(base_dir, "assets", "app_icon.ico"),
        os.path.join(base_dir, "volumenodex", "resources", "app_icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "assets", "app_icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "assets", "app_icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "app_icon.ico"),
        os.path.join(base_dir, "assets", "icon.png"),
        os.path.join(base_dir, "volumenodex", "resources", "app_icon.png"),
    ]
    app_ico_path = None
    for p in icon_candidates:
        if os.path.exists(p):
            ico = QIcon(p)
            if not ico.isNull():
                app.setWindowIcon(ico)
                app_ico_path = p
                break

    # Instant splash screen for zero-lag startup feedback
    splash = None
    if "--no-splash" not in sys.argv and "pytest" not in sys.modules:
        try:
            from PySide6.QtWidgets import QSplashScreen
            from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
            splash_pixmap = QPixmap(420, 220)
            splash_pixmap.fill(QColor(18, 20, 26))

            painter = QPainter(splash_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            pen = QPen(QColor(45, 52, 70), 1.5)
            painter.setPen(pen)
            painter.drawRoundedRect(1, 1, 418, 218, 10, 10)

            if app_ico_path and os.path.exists(app_ico_path):
                icon_pix = QIcon(app_ico_path).pixmap(64, 64)
                if not icon_pix.isNull():
                    painter.drawPixmap(30, 45, icon_pix)

            painter.setPen(QColor(240, 243, 250))
            font_title = QFont("Segoe UI", 18, QFont.Weight.Bold)
            painter.setFont(font_title)
            painter.drawText(112, 75, "Volumenodex")

            painter.setPen(QColor(140, 150, 175))
            font_sub = QFont("Segoe UI", 10)
            painter.setFont(font_sub)
            painter.drawText(114, 100, "Word Processing Studio  •  v2.0")

            painter.setPen(QColor(100, 112, 140))
            font_status = QFont("Segoe UI", 9)
            painter.setFont(font_status)
            painter.drawText(32, 185, "Initializing workspace...")
            painter.end()

            splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
            splash.show()
            app.processEvents()
        except Exception:
            splash = None

    window = MainWindow()

    # Synchronously bind native Win32 window icons for instant taskbar rendering
    if app_ico_path:
        window.setWindowIcon(QIcon(app_ico_path))
        if sys.platform == "win32" and app_ico_path.lower().endswith(".ico"):
            try:
                import ctypes
                hwnd = int(window.winId())
                if hwnd:
                    # WM_SETICON = 0x0080; ICON_SMALL = 0; ICON_BIG = 1
                    # LR_LOADFROMFILE = 0x0010; LR_DEFAULTSIZE = 0x0040
                    h_icon_big = ctypes.windll.user32.LoadImageW(
                        0, app_ico_path, 1, 0, 0, 0x0010 | 0x00000040
                    )
                    h_icon_sm = ctypes.windll.user32.LoadImageW(
                        0, app_ico_path, 1, 16, 16, 0x0010
                    )
                    if h_icon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, h_icon_big)
                    if h_icon_sm:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, h_icon_sm)
            except Exception:
                pass

    window.show()
    window.raise_()
    window.activateWindow()

    if splash is not None:
        splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
