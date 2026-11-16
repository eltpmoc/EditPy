"""Draw the original EditPy file icon family as portable SVGs with outlined labels."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtGui import QFont, QPainterPath
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "editpy" / "assets"
LABELS = {
    "javascript": ("JS", "#c6a63e"),
    "typescript": ("TS", "#4b94d1"),
    "react": ("JSX", "#42a9c5"),
    "html": ("<>", "#dc8054"),
    "css": ("#", "#5e99d4"),
    "sass": ("S", "#cf7eab"),
    "vue": ("V", "#4baf8b"),
    "svelte": ("S", "#e7835b"),
    "json": ("{}", "#c5a451"),
    "yaml": ("Y", "#bb7bba"),
    "toml": ("T", "#b58b69"),
    "xml": ("</>", "#58a7a2"),
    "markdown": ("M↓", "#699fc6"),
    "text": ("Aa", "#8e9db0"),
    "log": ("≡", "#b8a561"),
    "notebook": ("J", "#dd9b50"),
    "python-config": ("Py", "#6fa6cb"),
    "python-deps": ("Py", "#d1af53"),
    "npm": ("npm", "#cd727c"),
    "environment": ("ENV", "#67a58a"),
    "build": ("⚙", "#c68a91"),
    "c": ("C", "#669bd4"),
    "cpp": ("C+", "#738fce"),
    "csharp": ("C#", "#799e67"),
    "java": ("J", "#c58763"),
    "kotlin": ("K", "#b785d8"),
    "rust": ("R", "#c39579"),
    "go": ("Go", "#55a7be"),
    "swift": ("S", "#df8c62"),
    "ruby": ("Rb", "#c77583"),
    "php": ("php", "#9290c9"),
    "r": ("R", "#679bc5"),
    "lua": ("L", "#8a91c9"),
    "pdf": ("PDF", "#cb747c"),
    "document": ("W", "#638fc2"),
    "binary": ("01", "#949dac"),
    "font": ("Ff", "#b397be"),
    "audio": ("♪", "#bc87bb"),
    "video": ("▶", "#b68bc9"),
}
# Geometry for types whose recognition benefits from a symbol rather than a label.
SYMBOLS = {
    "file": ("#8b9bb0", '<path d="M8 11h7M8 14h7M8 17h5"/>'),
    "readme": ("#60a7d3", '<circle cx="12" cy="14" r="5"/><path d="M12 13v4m0-7v.2"/>'),
    "license": ("#c3a65e", '<path d="M12 10v7m-4 1h8M8 11h8m-8 0l-2 4h4zm8 0l-2 4h4z"/>'),
    "config": (
        "#9aacc1",
        '<circle cx="12" cy="14" r="3"/><path d="M12 9v2m0 6v2m-5-5h2m6 0h2m-8.5-3.5l1.4 1.4m4.2 4.2l1.4 1.4m0-7l-1.4 1.4m-4.2 4.2l-1.4 1.4"/>',
    ),
    "git": (
        "#db8a66",
        '<path d="M9 10v7m0-4h4a2 2 0 002-2v-1"/><circle cx="9" cy="9" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="9" r="1.5"/>',
    ),
    "shell": ("#66b39e", '<path d="M8 11l3 3-3 3m5 0h3"/>'),
    "lock": (
        "#c5a34e",
        '<rect x="8" y="12" width="8" height="7" rx="1.5"/><path d="M10 12v-2a2 2 0 014 0v2m-2 3v1"/>',
    ),
    "key": ("#c5a34e", '<circle cx="10" cy="12" r="3"/><path d="M12 14l5 5m-1-3l-1 1"/>'),
    "image": (
        "#b18ac8",
        '<rect x="6.5" y="9.5" width="11" height="9" rx="1"/><path d="M7 17l4-4 3 3 2-2 1 1"/><circle cx="15" cy="12" r=".6"/>',
    ),
    "svg": (
        "#c88eb6",
        '<path d="M7 17l5-7 5 7z"/><circle cx="12" cy="10" r="1.4"/><circle cx="7" cy="17" r="1.4"/><circle cx="17" cy="17" r="1.4"/>',
    ),
    "table": (
        "#72a98a",
        '<rect x="6.5" y="9" width="11" height="10" rx="1"/><path d="M7 12h10M7 15h10m-7-6v10m4-10v10"/>',
    ),
    "database": (
        "#a38bc9",
        '<ellipse cx="12" cy="10" rx="5" ry="2"/><path d="M7 10v7c0 3 10 3 10 0v-7M7 13.5c0 3 10 3 10 0"/>',
    ),
    "archive": ("#b99e64", '<path d="M10 8h4v3h-4zm0 3h4v3h-4zm0 3h4v4h-4z"/>'),
    "docker": (
        "#5a9fc5",
        '<path d="M6 14h12c-1 5-10 6-12 0zm2-3h2v3H8zm3 0h2v3h-2zm3 0h2v3h-2zm-3-3h2v3h-2z"/>',
    ),
    "graphql": (
        "#c380b0",
        '<path d="M12 9l5 8H7zm0 0v10m-5-2l5 2 5-2"/><circle cx="12" cy="9" r="1"/><circle cx="7" cy="17" r="1"/><circle cx="17" cy="17" r="1"/>',
    ),
}
FOLDERS = {
    "folder": ("#8c9fb6", ""),
    "source": ("#80a6c3", "‹›"),
    "python": ("#759fb9", "Py"),
    "assets": ("#c4a44e", "◈"),
    "tests": ("#55b59e", "✓"),
    "docs": ("#69a2d0", "≡"),
    "scripts": ("#76b8aa", "›_"),
    "examples": ("#80b19b", "‹›"),
    "build": ("#c58b98", "↗"),
    "package": ("#bf9d74", "□"),
    "git": ("#c49173", "±"),
    "config": ("#9c9ac5", "⚙"),
    "environment": ("#8db18c", "·"),
    "dependencies": ("#a39e80", "⋯"),
    "cache": ("#939bae", "↻"),
}


def outline(label, color, size=9, center=(12, 15)):
    font = QFont("Menlo")
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.Bold)
    path = QPainterPath()
    path.addText(0, 0, font, label)
    box = path.boundingRect()
    path.translate(center[0] - box.center().x(), center[1] - box.center().y())
    parts = []
    i = 0
    while i < path.elementCount():
        e = path.elementAt(i)
        if e.isMoveTo():
            parts.append(f"M{e.x:.3f},{e.y:.3f}")
        elif e.isLineTo():
            parts.append(f"L{e.x:.3f},{e.y:.3f}")
        elif e.type == QPainterPath.ElementType.CurveToElement:
            b, c = path.elementAt(i + 1), path.elementAt(i + 2)
            parts.append(f"C{e.x:.3f},{e.y:.3f} {b.x:.3f},{b.y:.3f} {c.x:.3f},{c.y:.3f}")
            i += 2
        i += 1
    return f'<path d="{" ".join(parts)}" fill="{color}"/>'


def write(name, body):
    (OUT / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>\n'
    )


def document(color):
    return f'<path d="M6 2.5h8l5 5v14H5v-18z" fill="{color}" fill-opacity=".09" stroke="{color}" stroke-opacity=".85" stroke-width="1.25" stroke-linejoin="round"/><path d="M14 3v5h5" fill="none" stroke="{color}" stroke-width="1.1"/>'


def main():
    app = QApplication([])
    for name, (label, color) in LABELS.items():
        write(name, document(color) + outline(label, color, 7 if len(label) > 2 else 9))
    for name, (color, symbol) in SYMBOLS.items():
        write(
            name,
            document(color)
            + f'<g fill="none" stroke="{color}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">{symbol}</g>',
        )
    for name, (color, badge) in FOLDERS.items():
        for opened in (False, True):
            body = f'<path d="M2 6a2 2 0 012-2h6l2 2h8a2 2 0 012 2v11H2z" fill="{color}" fill-opacity=".32"/>'
            front = "M2 10h21l-3 10H2z" if opened else "M2 8h20v12H2z"
            body += f'<path d="{front}" fill="{color}" fill-opacity=".8" stroke="{color}" stroke-width=".7" stroke-linejoin="round"/>'
            if badge:
                body += outline(badge, "#18222c", 8 if len(badge) > 1 else 10, (13, 14))
            write("folder-" + name + ("-open" if opened else ""), body)
    write(
        "python",
        """<path d="M12 2c-5 0-5 2-5 5h5v1H5c-4 0-4 8 0 8h2v-3a3 3 0 013-3h7V5c0-3-2-3-5-3z" fill="#559bd1"/><path d="M12 22c5 0 5-2 5-5h-5v-1h7c4 0 4-8 0-8h-2v3a3 3 0 01-3 3H7v5c0 3 2 3 5 3z" fill="#e7bd53"/><circle cx="10" cy="5" r="1" fill="#203047"/><circle cx="14" cy="19" r="1" fill="#4b412a"/>""",
    )
    recognizable_symbols()
    del app


def recognizable_symbols():
    # Larger silhouettes keep the common formats legible at 16 px.
    for name, text, background, ink in [
        ("javascript", "JS", "#d4b44c", "#282b31"),
        ("typescript", "TS", "#4b94d1", "#ffffff"),
        ("markdown", "M↓", "#669dc8", "#ffffff"),
    ]:
        write(
            name,
            f'<rect x="2" y="2" width="20" height="20" rx="2" fill="{background}"/>'
            + outline(text, ink, 11, (12, 13)),
        )
    write(
        "readme",
        '<circle cx="12" cy="12" r="10" fill="#559fd1"/>' + outline("i", "#ffffff", 17, (12, 12)),
    )
    write("json", outline("{}", "#c5a451", 19, (12, 12)))
    write(
        "react",
        '<g fill="none" stroke="#56b7d1" stroke-width="1.25"><ellipse cx="12" cy="12" rx="10" ry="4"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/></g><circle cx="12" cy="12" r="2" fill="#56b7d1"/>',
    )
    write(
        "vue",
        '<path d="M1 3h5l6 11 6-11h5L12 22z" fill="#53ac8c"/><path d="M6 3h4l2 4 2-4h4l-6 11z" fill="#64809a"/>',
    )
    write(
        "html",
        '<path d="M2 2h20l-2 18-8 3-8-3z" fill="#d98559"/>'
        + outline("<>", "#ffffff", 12, (12, 12)),
    )
    write(
        "css",
        '<path d="M2 2h20l-2 18-8 3-8-3z" fill="#5e99d4"/>' + outline("#", "#ffffff", 16, (12, 12)),
    )
    write(
        "git",
        '<rect x="3.5" y="3.5" width="17" height="17" rx="2" transform="rotate(45 12 12)" fill="#db8a66"/><path d="M9 6v12m0-8h4a3 3 0 013 3" fill="none" stroke="#ffffff" stroke-width="1.5"/><g fill="#ffffff"><circle cx="9" cy="6" r="1.7"/><circle cx="9" cy="18" r="1.7"/><circle cx="16" cy="14" r="1.7"/></g>',
    )
    write(
        "lock",
        '<rect x="4" y="10" width="16" height="12" rx="2" fill="#c5a34e"/><path d="M7 10V7a5 5 0 0110 0v3" fill="none" stroke="#c5a34e" stroke-width="2.5"/><path d="M12 14v4" stroke="#403929" stroke-width="2" stroke-linecap="round"/>',
    )
    write(
        "shell",
        '<rect x="1.5" y="3.5" width="21" height="17" rx="2" fill="#66b39e" fill-opacity=".12" stroke="#66b39e" stroke-width="1.5"/><path d="M6 8l4 4-4 4m6 0h6" fill="none" stroke="#66b39e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    )
    write(
        "notebook",
        '<path d="M4 8a10 10 0 0116 0M4 16a10 10 0 0016 0" fill="none" stroke="#dd9b50" stroke-width="3"/><circle cx="6" cy="3" r="1.5" fill="#9ba8b7"/><circle cx="19" cy="21" r="1.5" fill="#9ba8b7"/>',
    )
    python = (OUT / "python.svg").read_text().split(">", 1)[1].rsplit("</svg>", 1)[0]
    write(
        "python-config",
        f'<g transform="scale(.85)">{python}</g><circle cx="18" cy="18" r="5" fill="#547ea5" stroke="#c6d9e8" stroke-width="1"/><path d="M18 15v6m-3-3h6" stroke="#ffffff" stroke-width="1.2"/>',
    )
    write(
        "python-deps",
        f'<g transform="scale(.85)">{python}</g><rect x="14" y="14" width="9" height="9" rx="1.5" fill="#c5a34e"/><path d="M16 18h5m-2.5-2.5v5" stroke="#ffffff" stroke-width="1.2"/>',
    )


if __name__ == "__main__":
    main()
