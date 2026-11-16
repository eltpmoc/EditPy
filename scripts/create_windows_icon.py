"""Export a multi-resolution ICO from the same SVG used by the macOS app."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import struct
from pathlib import Path
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication.instance() or QApplication([])
    root = Path(__file__).resolve().parents[1]
    renderer = QSvgRenderer(str(root / "assets" / "brand" / "editpy-icon.svg"))
    images = []
    sizes = [16, 24, 32, 48, 64, 128, 256]
    for size in sizes:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        images.append(bytes(buffer.data()))
    offset = 6 + len(images) * 16
    entries = []
    for size, data in zip(sizes, images):
        entries.append(
            struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        )
        offset += len(data)
    (root / "assets" / "EditPy.ico").write_bytes(
        struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(images)
    )
    del app


if __name__ == "__main__":
    main()
