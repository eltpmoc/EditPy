"""Verify the actual Cocoa window appearance, not just Qt's stylesheet."""

import ctypes
import json
import sys
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from editpy.window import MainWindow


def cocoa_appearance(widget):
    objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
        ("objc_msgSend", objc)
    )

    def call(receiver, selector):
        return send(receiver, objc.sel_registerName(selector.encode()))

    view = int(widget.winId())
    window = call(view, "window")
    appearance = call(window, "effectiveAppearance")
    name = call(appearance, "name")
    return ctypes.string_at(call(name, "UTF8String")).decode()


def main():
    if sys.platform != "darwin":
        raise SystemExit("Requer macOS com plataforma Qt Cocoa.")
    app = QApplication([])
    if app.platformName() != "cocoa":
        raise SystemExit("A verificação requer QT_QPA_PLATFORM=cocoa.")
    app.setStyle("Fusion")
    root = Path(__file__).resolve().parents[1]
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(root / "build" / "native-theme-settings"),
    )
    window = MainWindow()
    window.show()
    results = {}
    for theme in ("dark", "light", "dark"):
        window.set_theme(theme)
        app.processEvents()
        results[theme] = cocoa_appearance(window)
    print(json.dumps(results, indent=2))
    window.close()
    assert results["dark"] == "NSAppearanceNameDarkAqua"
    assert results["light"] == "NSAppearanceNameAqua"


if __name__ == "__main__":
    main()
