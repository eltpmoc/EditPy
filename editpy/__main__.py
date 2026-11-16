import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def main():
    parser = argparse.ArgumentParser(description="EditPy — Python IDE")
    parser.add_argument("project", nargs="?", type=Path)
    parser.add_argument(
        "--smoke-test",
        type=Path,
        metavar="REPORT",
        help="Verificar Qt, Jedi, Ruff e execução e gravar JSON",
    )
    args = parser.parse_args()
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("eltpmoc.EditPy")
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setApplicationName("EditPy")
    app.setApplicationVersion("0.4.0")
    app.setOrganizationName("EditPy")
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    if args.smoke_test:
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            str(args.smoke_test.resolve().parent / "smoke-settings"),
        )
    from .window import MainWindow

    window = MainWindow(args.project)
    window.show()
    if args.smoke_test:
        from .smoke import verify

        sys.exit(verify(window, args.smoke_test))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
