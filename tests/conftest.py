import os
import sys
import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(scope="session")
def app():
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application
    for widget in application.topLevelWidgets():
        try:
            if hasattr(widget, "_stop_threads"):
                widget._stop_threads()
            widget.close()
        except Exception:
            pass
    application.processEvents()

@pytest.fixture(autouse=True)
def cleanup_widgets():
    yield
    app_instance = QApplication.instance()
    if app_instance:
        for widget in app_instance.topLevelWidgets():
            try:
                if hasattr(widget, "_stop_threads"):
                    widget._stop_threads()
                widget.close()
            except Exception:
                pass
        app_instance.processEvents()
