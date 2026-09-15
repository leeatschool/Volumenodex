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
