"""Turn unexpected error dialogs into useful CI failures instead of modal hangs."""

import pytest
from editpy.window import MainWindow


@pytest.fixture(autouse=True)
def unexpected_error_dialog(monkeypatch):
    def fail(self, message):
        raise AssertionError(f"Unexpected EditPy error dialog: {message}")

    monkeypatch.setattr(MainWindow, "error", fail)
