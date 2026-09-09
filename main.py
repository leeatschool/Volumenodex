"""Application entry point for Volumenodex Word Processing Studio."""

import sys
import os

# Ensure the package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, qInstallMessageHandler, QtMsgType
from PySide6.QtWidgets import QApplication
from volumenodex.ui.main_window import MainWindow


def _qt_message_handler(mode, context, message):
    # Filter known harmless DirectWrite warnings for legacy DOS raster fonts (8514oem, Fixedsys)
    if "DirectWrite: CreateFontFaceFromHDC" in message:
        return
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        sys.stderr.write(f"{message}\n")


def main():
    qInstallMessageHandler(_qt_message_handler)
    # Configure high-DPI behavior
    app = QApplication(sys.argv)
    app.setApplicationName("Volumenodex")
    app.setApplicationDisplayName("Volumenodex Word Studio")
    app.setOrganizationName("Volumenodex")

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
