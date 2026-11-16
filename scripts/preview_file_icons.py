"""Render the actual icon catalog at UI sizes for dark/light visual review."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math
import sys
from pathlib import Path
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from editpy.file_icons import FileIcons  # noqa: E402

FILES = [
    "main.py",
    "types.pyi",
    "pyproject.toml",
    "requirements.txt",
    "requirements.lock",
    ".gitignore",
    "README.md",
    "LICENSE",
    ".env.local",
    "Dockerfile",
    "compose.yaml",
    "package.json",
    "index.js",
    "types.ts",
    "component.tsx",
    "index.html",
    "styles.css",
    "theme.scss",
    "App.vue",
    "App.svelte",
    "settings.json",
    "workflow.yml",
    "config.toml",
    "settings.ini",
    "manifest.xml",
    "notes.txt",
    "build.log",
    "analysis.ipynb",
    "database.sqlite",
    "queries.sql",
    "schema.graphql",
    "script.sh",
    "main.swift",
    "app.go",
    "lib.rs",
    "main.cpp",
    "Program.cs",
    "Main.java",
    "app.kt",
    "app.rb",
    "index.php",
    "analysis.r",
    "plugin.lua",
    "photo.png",
    "logo.svg",
    "document.pdf",
    "data.csv",
    "report.docx",
    "archive.zip",
    "library.dylib",
    "font.woff2",
    "cert.pem",
]
FOLDERS = [
    "assets",
    "docs",
    "editpy",
    "examples",
    "packaging",
    "scripts",
    "tests",
    "src",
    "build",
    ".venv",
    ".git",
    "node_modules",
    "__pycache__",
    "custom",
]


def main():
    app = QApplication([])
    catalog = FileIcons()
    entries = [(name, False) for name in FILES] + [(name + "/", True) for name in FOLDERS]
    columns, row_height = 4, 48
    height = 90 + math.ceil(len(entries) / columns) * row_height
    output = ROOT / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    for theme, background, ink in [("dark", "#191d25", "#d5deeb"), ("light", "#f5f7fb", "#2a3449")]:
        image = QImage(1120, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(background))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(ink))
        painter.setFont(QFont("Avenir Next", 19, QFont.Weight.DemiBold))
        painter.drawText(26, 40, "EditPy  /  Arquivos e pastas")
        painter.setFont(QFont("Menlo", 11))
        for i, (name, folder) in enumerate(entries):
            x, y = 26 + (i % columns) * 274, 65 + (i // columns) * row_height
            catalog.icon(name.rstrip("/"), directory=folder).paint(painter, QRect(x, y, 26, 26))
            painter.drawText(QRect(x + 38, y, 225, 28), Qt.AlignmentFlag.AlignVCenter, name)
        painter.end()
        image.save(str(output / f"file-icons-{theme}.png"))
    del app


if __name__ == "__main__":
    main()
