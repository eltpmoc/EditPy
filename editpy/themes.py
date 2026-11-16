from pathlib import Path

THEMES = {
    "dark": dict(
        bg="#12151b",
        panel="#191d25",
        editor="#171b22",
        border="#292f3b",
        fg="#d5deeb",
        muted="#8290a7",
        accent="#b4a1f2",
        selection="#343049",
        keyword="#b7a4ed",
        string="#a6c99d",
        comment="#728199",
        number="#e1ba87",
        active="#232936",
        run_bg="#223b34",
        run_fg="#a0e0c8",
    ),
    "light": dict(
        bg="#edf0f5",
        panel="#f5f7fb",
        editor="#ffffff",
        border="#dce2ec",
        fg="#2a3449",
        muted="#7a879c",
        accent="#7960c8",
        selection="#e8e2f7",
        keyword="#8351ba",
        string="#3b804b",
        comment="#8995a7",
        number="#ac6d29",
        active="#ffffff",
        run_bg="#e0f0e9",
        run_fg="#296c54",
    ),
}


def stylesheet(theme):
    c = THEMES[theme]
    css = (
        """
    QWidget { background: %(bg)s; color: %(fg)s; font-family: ".AppleSystemUIFont", "Segoe UI", sans-serif; font-size: 13px; font-weight: 400; }
    QLabel { background: transparent; }
    QMainWindow, QDialog { background: %(bg)s; }
    QMenuBar, QMenu, QToolBar, QStatusBar { background: %(panel)s; }
    QMenuBar::item:selected, QMenu::item:selected { background: %(selection)s; }
    QMenu { border: 1px solid %(border)s; padding: 6px; }
    QMenu::item { padding: 7px 26px; border-radius: 4px; }
    QToolBar { border: 0; border-bottom: 1px solid %(border)s; spacing: 8px; padding: 10px 12px; }
    QToolBar QWidget { background: transparent; }
    QToolButton, QPushButton { border: 1px solid %(border)s; border-radius: 6px; padding: 7px 12px; background: %(panel)s; }
    QToolButton:hover, QPushButton:hover { border-color: %(accent)s; background: %(selection)s; }
    QToolButton:disabled, QPushButton:disabled { color: %(muted)s; }
    QPushButton#primary { background: %(accent)s; color: %(editor)s; font-weight: 600; border: 0; padding: 11px 22px; }
    QPushButton#runButton { color: %(run_fg)s; background: %(run_bg)s; border-color: %(run_bg)s; font-weight: 500; }
    QPushButton#runButton:disabled { color: %(muted)s; background: %(panel)s; border-color: %(border)s; }
    QPushButton#runButton:hover { border-color: %(run_fg)s; }
    QPushButton#quietButton { border-color: transparent; }
    QPushButton#commandSearch { background: %(bg)s; color: %(muted)s; text-align: left; padding: 8px 14px; }
    QLabel#workspaceName { font-weight: 500; padding: 0 12px; border-left: 1px solid %(border)s; }
    QToolBar#activityRail { background: %(bg)s; border: 0; border-right: 1px solid %(border)s; padding: 10px 4px; spacing: 10px; }
    QToolBar#activityRail QToolButton { border: 0; border-radius: 7px; padding: 9px 7px; }
    QToolBar#activityRail QToolButton:hover { background: %(active)s; }
    QLabel#brand { font-size: 36px; font-weight: 600; letter-spacing: -1px; }
    QLabel#eyebrow { color: %(accent)s; font-size: 10px; font-weight: 600; letter-spacing: 1.5px; }
    QLabel#muted { color: %(muted)s; }
    QLabel#section { color: %(muted)s; background: %(editor)s; font-size: 11px; font-weight: 400; padding: 11px 18px; letter-spacing: 0; border-bottom: 1px solid %(border)s; }
    QWidget#dockHeader { background: %(panel)s; border-bottom: 1px solid %(border)s; }
    QLabel#dockCaption { color: %(muted)s; font-size: 10px; font-weight: 600; letter-spacing: 1.2px; }
    QToolButton#panelClose { border: 0; padding: 0 4px; color: %(muted)s; background: transparent; }
    QLineEdit, QComboBox, QSpinBox { border: 1px solid %(border)s; border-radius: 6px; padding: 8px; background: %(editor)s; selection-background-color: %(selection)s; }
    QLineEdit:focus { border-color: %(accent)s; }
    QPlainTextEdit, QTextEdit { border: 0; background: %(editor)s; selection-background-color: %(selection)s; }
    QTreeView, QListWidget, QTableWidget { background: %(panel)s; border: 0; outline: 0; alternate-background-color: %(bg)s; }
    QTreeView { padding: 8px 5px; }
    QTreeView::item { padding: 6px 4px; margin: 1px 0; border-radius: 5px; }
    QListWidget::item { padding: 8px; border-radius: 5px; }
    QTreeView::item:selected, QListWidget::item:selected { background: %(selection)s; color: %(fg)s; }
    QTreeView::item:hover { background: %(active)s; }
    QHeaderView::section { background: %(panel)s; border: 0; padding: 7px; }
    QTabWidget::pane { border: 0; }
    QTabBar { background: %(bg)s; }
    QTabBar::tab { background: %(bg)s; color: %(muted)s; padding: 11px 16px; min-width: 96px; border: 0; border-bottom: 2px solid transparent; }
    QTabBar::tab:selected { background: %(active)s; color: %(fg)s; border-bottom: 2px solid %(accent)s; }
    QTabBar::tab:hover:!selected { background: %(panel)s; color: %(fg)s; }
    QToolButton#newTab { background: %(bg)s; border: 0; border-left: 1px solid %(border)s; border-radius: 0; font-size: 20px; padding: 5px 16px; color: %(muted)s; }
    QToolButton#newTab::menu-indicator { image: none; }
    QSplitter::handle { background: %(border)s; width: 1px; height: 1px; }
    QScrollBar:vertical { background: %(editor)s; width: 9px; margin: 3px 0; }
    QScrollBar::handle:vertical { background: %(border)s; min-height: 28px; border-radius: 4px; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
    QStatusBar { border-top: 1px solid %(border)s; color: %(muted)s; font-size: 11px; padding: 4px; }
    QStatusBar QLabel { font-size: 11px; color: %(muted)s; }
    QStatusBar::item { border: 0; }
    QToolTip { color: %(fg)s; background: %(panel)s; border: 1px solid %(border)s; padding: 6px; }
    QLabel#terminalBadge { color: %(run_fg)s; font-size: 10px; font-weight: 600; letter-spacing: 1px; padding-right: 16px; }
    QLabel#terminalHint { background: %(panel)s; color: %(muted)s; font-size: 10px; padding: 9px 12px; border-top: 1px solid %(border)s; }
    """
        % c
    )
    close = (Path(__file__).parent / "assets" / "close.svg").as_posix()
    return (
        css
        + f"""
    QTabBar::close-button {{ image: url('{close}'); width: 12px; height: 12px; margin-left: 8px; }}
    QTabBar::close-button:hover {{ background: {c["selection"]}; border-radius: 3px; }}
    QScrollBar:horizontal {{ background: {c["editor"]}; height: 9px; }}
    QScrollBar::handle:horizontal {{ background: {c["border"]}; min-width: 24px; border-radius: 4px; }}
    """
    )
