"""Generate EditPy's vector identity and native macOS icon from one master."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil
import subprocess
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QImage, QPainter, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
RUNTIME = ROOT / "editpy" / "assets"
BRAND = ASSETS / "brand"

SYMBOL = """<defs>
  <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#2d3048"/><stop offset="1" stop-color="#141725"/>
  </linearGradient>
  <linearGradient id="ink" x1="0" y1="0" x2="0.8" y2="1">
    <stop stop-color="#d2c4ff"/><stop offset="1" stop-color="#9c82f4"/>
  </linearGradient>
</defs>
<rect x="64" y="64" width="896" height="896" rx="204" fill="url(#tile)"/>
<rect x="66" y="66" width="892" height="892" rx="202" fill="none" stroke="#b6a5ff" stroke-opacity=".18" stroke-width="4"/>
<path d="M270 306 Q270 288 288 288 H572 V376 H366 V468 H540 V552 H366 V648 H572 V736 H288 Q270 736 270 718 Z" fill="url(#ink)"/>
<path d="M666 386 L790 512 L666 638" fill="none" stroke="#81e5cd" stroke-width="72" stroke-linecap="round" stroke-linejoin="round"/>
"""


def svg(body, viewbox="0 0 1024 1024"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">{body}</svg>\n'


def path_data(path):
    """Export cubic outlines, keeping the wordmark independent of installed fonts."""
    parts = []
    i = 0
    while i < path.elementCount():
        element = path.elementAt(i)
        if element.isMoveTo():
            parts.append(f"M{element.x:.3f} {element.y:.3f}")
        elif element.isLineTo():
            parts.append(f"L{element.x:.3f} {element.y:.3f}")
        elif element.type == QPainterPath.ElementType.CurveToElement:
            b, c = path.elementAt(i + 1), path.elementAt(i + 2)
            parts.append(
                f"C{element.x:.3f} {element.y:.3f} {b.x:.3f} {b.y:.3f} {c.x:.3f} {c.y:.3f}"
            )
            i += 2
        i += 1
    return " ".join(parts)


def render(source, output, width, height):
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ValueError(f"SVG inválido: {source}")
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    if not image.save(str(output)):
        raise OSError(f"Falha ao exportar: {output}")


def main():
    app = QApplication.instance() or QApplication([])
    for folder in (ASSETS, RUNTIME, BRAND):
        folder.mkdir(parents=True, exist_ok=True)
    icon = BRAND / "editpy-icon.svg"
    icon.write_text(svg(SYMBOL))
    shutil.copy2(icon, RUNTIME / "editpy-icon.svg")
    render(icon, BRAND / "editpy-icon.png", 1024, 1024)
    font = QFont("Avenir Next")
    font.setWeight(QFont.Weight.DemiBold)
    font.setPixelSize(180)
    first = QPainterPath()
    first.addText(340, 220, font, "Edit")
    second = QPainterPath()
    second.addText(340 + first.boundingRect().width() + 6, 220, font, "Py")
    for theme, ink, accent in [("dark", "#edf0fa", "#81e5cd"), ("light", "#252a42", "#276e66")]:
        body = f'<g transform="scale(0.3125)">{SYMBOL}</g>'
        body += f'<path d="{path_data(first)}" fill="{ink}"/>'
        body += f'<path d="{path_data(second)}" fill="{accent}"/>'
        output = BRAND / f"editpy-logo-{theme}.svg"
        output.write_text(svg(body, "0 0 960 320"))
        shutil.copy2(output, RUNTIME / output.name)
        render(output, output.with_suffix(".png"), 1920, 640)
    iconset = ASSETS / "EditPy.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            render(
                icon,
                iconset / f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png",
                size * scale,
                size * scale,
            )
    if sys.platform == "darwin":
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "EditPy.icns")], check=True
        )
    # Keep the QApplication alive until every paint device has been released.
    del app


if __name__ == "__main__":
    main()
