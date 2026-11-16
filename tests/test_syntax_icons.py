"""Cases that previously broke regex highlighting and generic explorer icons."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
from pathlib import Path

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QTextDocument
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from editpy.file_icons import EXTENSIONS, FOLDERS, FileIcons, file_kind, folder_kind
from editpy.project_tree import ProjectIcons
from editpy.syntax import SourceHighlighter, analyze_source


def role_at(source, row, text, start=0, path=None):
    line, spans = analyze_source(source, path)[row - 1]
    column = len(line[: line.index(text, start)].encode("utf-16-le")) // 2
    return next((role for a, length, role in reversed(spans) if a <= column < a + length), None)


def test_python_declarations_parameters_calls_types_and_scope():
    source = (
        "class Service:\n    def run(self, window: str, total=42):\n"
        "        return window.strip(), len(window), total\n"
        "\ndef other():\n    window = Service()\n    return window\n"
    )
    assert role_at(source, 1, "class") == "definition"
    assert role_at(source, 1, "Service") == "type"
    assert role_at(source, 2, "run") == "declaration"
    assert role_at(source, 2, "window") == "parameter"
    assert role_at(source, 2, "str") == "type"
    assert role_at(source, 2, "42") == "number"
    assert role_at(source, 3, "window") == "parameter"
    assert role_at(source, 3, "strip") == "function"
    assert role_at(source, 3, "len") == "function"
    assert role_at(source, 6, "Service") == "type"
    assert role_at(source, 7, "window") == "name"  # No leaking parameter names across functions.


def test_comments_quotes_hashes_multiline_and_code_after_closing_string():
    source = (
        '# not a docstring: """\n'
        'value = "contains # and def fake()"\n'
        'message = """first #\nsecond def fake():\nthird"""; print(value) # real\n'
    )
    assert role_at(source, 1, '"""') == "comment"
    assert role_at(source, 2, "#") == "string"
    assert role_at(source, 2, "def") == "string"
    assert role_at(source, 3, "#") == "string"
    assert role_at(source, 4, "def") == "string"
    assert role_at(source, 5, "print") == "function"
    assert role_at(source, 5, "#") == "comment"


def test_fstring_interpolation_unicode_and_qt_utf16_coordinates():
    source = 'def demo(ação):\n    return f"😀 # {ação!r}"\n'
    assert role_at(source, 1, "ação") == "parameter"
    assert role_at(source, 2, "#") == "string"
    assert role_at(source, 2, "ação") == "parameter"
    assert role_at(source, 2, "{") == "operator"


def test_incomplete_python_and_non_python_lexers():
    source = 'def pending(value:\n    # still editing\n    print("# text")\n'
    assert role_at(source, 1, "def") == "definition"
    assert role_at(source, 2, "#") == "comment"
    assert role_at(source, 3, "#") == "string"
    assert (
        role_at('{"enabled": true, "count": 42}', 1, "42", path=Path("settings.json")) == "number"
    )
    assert role_at("def is just plain text", 1, "def", path=Path("notes.unknown")) == "name"


def test_background_highlighter_tracks_latest_document_theme_and_language():
    app = QApplication.instance() or QApplication([])
    document = QTextDocument()
    highlighter = SourceHighlighter(document, "dark")
    document.setPlainText("def before():\n    pass\n")
    highlighter.start_analysis()
    document.setPlainText("def after(window):\n    return window.strip()\n")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if highlighter.is_current:
            break
        time.sleep(0.01)
    assert highlighter.is_current
    first = document.firstBlock().layout().formats()
    dark = first[0].format.foreground().color().name()
    highlighter.theme = "light"
    highlighter.rehighlight()
    assert document.firstBlock().layout().formats()[0].format.foreground().color().name() != dark
    highlighter.set_path(Path("notes.txt"))
    assert not highlighter.is_current
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not highlighter.is_current:
        app.processEvents()
        time.sleep(0.01)
    assert highlighter.is_current
    assert all(role == "name" for _, ranges in highlighter.blocks for _, _, role in ranges)


def test_filename_priorities_case_and_folder_roles():
    cases = {
        "MAIN.PY": "python",
        "pyproject.toml": "python-config",
        "README.md": "readme",
        ".gitignore": "git",
        ".env.local": "environment",
        "requirements-dev.txt": "python-deps",
        "requirements-macos.lock": "lock",
        "docker-compose.yaml": "docker",
        "package.json": "npm",
        "schema.json": "json",
        "component.tsx": "react",
        "unknown.custom": "file",
        "artwork.svg": "svg",
        "LICENSE": "license",
    }
    assert {name: file_kind(name) for name in cases} == cases
    assert folder_kind("tests") == "tests"
    assert folder_kind("docs") == "docs"
    assert folder_kind("my_custom_dir") == "folder"


def test_all_icon_families_render_and_match_file_provider(tmp_path):
    app = QApplication.instance() or QApplication([])
    catalog = FileIcons()
    root = Path(__file__).resolve().parents[1] / "editpy" / "assets"
    families = set(EXTENSIONS.values()) | {
        file_kind(p)
        for p in [
            "README.md",
            "LICENSE",
            ".gitignore",
            ".env",
            "Dockerfile",
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            "Makefile",
            "unknown",
        ]
    }
    for family in families:
        renderer = QSvgRenderer(str(root / f"{family}.svg"))
        assert renderer.isValid(), family
    for name in [*FOLDERS, "custom"]:
        family = folder_kind(name)
        for suffix in ("", "-open"):
            assert QSvgRenderer(str(root / f"folder-{family}{suffix}.svg")).isValid()
        assert not catalog.icon(name, directory=True).pixmap(20, 20).isNull()
    file = tmp_path / "config.json"
    file.write_text("{}")
    provider = ProjectIcons()
    assert not provider.icon(QFileInfo(str(file))).pixmap(20, 20).isNull()
    assert catalog.icon(file).cacheKey() == catalog.icon(file).cacheKey()
    assert not app.closingDown()


def test_save_as_updates_tab_icon_and_language(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QFileDialog
    from editpy.window import MainWindow

    app = QApplication.instance() or QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "prefs")
    )
    window = MainWindow(tmp_path)
    editor = window.add_editor(None, '{"enabled": true, "count": 42}')
    output = tmp_path / "settings.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    try:
        assert window.save_current(save_as=True)
        assert editor.highlighter.path == output
        assert (
            window.tabs.tabIcon(window.tabs.indexOf(editor)).cacheKey()
            == window.file_icons.catalog.icon(output).cacheKey()
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not editor.highlighter.is_current:
            app.processEvents()
            time.sleep(0.01)
        assert editor.highlighter.is_current
    finally:
        editor.document().setModified(False)
        window.close()
