import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def app():
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application
