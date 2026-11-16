from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QDir, QSettings, QThreadPool, QTimer
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QTextCursor,
    QFont,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileSystemModel,
    QSizePolicy,
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QToolButton,
    QMenu,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeView,
    QTabWidget,
    QDockWidget,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QComboBox,
    QSpinBox,
    QStackedWidget,
    QPlainTextEdit,
)

from .editor import CodeEditor
from .services import (
    read_source,
    write_source,
    search_project,
    symbols,
    syntax_problem,
    default_interpreter,
)
from .tasks import Worker, ProcessPanel
from .themes import stylesheet
from .terminal import TerminalTab
from .project_tree import ProjectFilter, ProjectIcons
from .platforms import parse_arguments, apply_native_theme


class MainWindow(QMainWindow):
    def __init__(self, project=None):
        super().__init__()
        self.settings = QSettings(
            QSettings.defaultFormat(), QSettings.Scope.UserScope, "EditPy", "EditPy"
        )
        self.theme = self.settings.value("theme", "dark")
        if self.theme not in ("dark", "light"):
            self.theme = "dark"
        self.font_size = int(self.settings.value("font_size", 13))
        self.interpreter = self.settings.value("interpreter", default_interpreter())
        self.arguments = ""
        self.root = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.workers = set()
        self.search_version = 0
        self.workspace_generation = 0
        self.terminal_count = 0
        self.console_count = 0
        self.setWindowTitle("EditPy")
        self.resize(1440, 940)
        self.setMinimumSize(980, 640)
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks
        )
        self.make_icon()
        self.build_center()
        self.build_docks()
        self.build_actions()
        self.build_toolbar()
        self.set_theme(self.theme)
        self.statusBar().showMessage("Pronto para criar.")
        self.location = QLabel("Python  •  UTF-8  •  4 espaços")
        self.statusBar().addPermanentWidget(self.location)
        self.outline_timer = QTimer(self)
        self.outline_timer.setSingleShot(True)
        self.outline_timer.setInterval(450)
        self.outline_timer.timeout.connect(self.refresh_outline)
        self.tabs.currentChanged.connect(self.current_changed)
        self.poll = QTimer(self)
        self.poll.setInterval(2000)
        self.poll.timeout.connect(self.check_external_changes)
        self.poll.start()
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        initial = project or self.settings.value("project", "")
        if initial and Path(initial).is_dir():
            self.open_project(Path(initial), restore=True)

    def make_icon(self):
        icon = QIcon(str(Path(__file__).parent / "assets" / "editpy-icon.svg"))
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)

    def update_brand(self):
        path = Path(__file__).parent / "assets" / f"editpy-logo-{self.theme}.svg"
        for label, height in [(self.brand_label, 32), (self.welcome_logo, 94)]:
            label.setPixmap(
                QPixmap(str(path)).scaledToHeight(
                    height, Qt.TransformationMode.SmoothTransformation
                )
            )

    def build_center(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setContentsMargins(70, 60, 70, 60)
        layout.addStretch(2)
        self.welcome_logo = QLabel()
        self.welcome_logo.setAccessibleName("EditPy")
        layout.addWidget(self.welcome_logo)
        layout.addSpacing(20)
        eyebrow = QLabel("SEU PRÓXIMO PROJETO COMEÇA AQUI")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        brand = QLabel("Menos distrações.\nMais possibilidades.")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        subtitle = QLabel("EditPy  /  Um espaço para pensar, criar e desenvolver em Python.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        layout.addSpacing(26)
        row = QHBoxLayout()
        for text, callback in [
            ("Abrir projeto", self.choose_project),
            ("Novo arquivo", self.new_file),
            ("Abrir arquivo", self.choose_file),
        ]:
            button = QPushButton(text)
            if text == "Abrir projeto":
                button.setObjectName("primary")
            button.clicked.connect(callback)
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        layout.addSpacing(28)
        self.recents = QListWidget()
        self.recents.setMaximumHeight(150)
        self.refresh_recents()
        self.recents.itemDoubleClicked.connect(
            lambda item: self.open_project(Path(item.data(Qt.ItemDataRole.UserRole)))
        )
        layout.addWidget(self.recents)
        layout.addStretch(3)
        footer = QLabel(
            "⌘ P  Arquivos     /     ⌘ ⇧ P  Comandos     /     Ctrl Espaço  Completar"
            if sys.platform == "darwin"
            else "Ctrl P  Arquivos     /     Ctrl Shift P  Comandos     /     Ctrl Espaço  Completar"
        )
        footer.setObjectName("muted")
        layout.addWidget(footer)
        self.stack.addWidget(welcome)
        editor_area = QWidget()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb = QLabel("  EDITOR")
        self.breadcrumb.setObjectName("section")
        editor_layout.addWidget(self.breadcrumb)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("workspaceTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        plus = QToolButton()
        plus.setObjectName("newTab")
        plus.setText("+")
        plus.setToolTip("Nova aba: arquivo, terminal ou console Python")
        plus.setAccessibleName("Nova aba")
        plus.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(plus)
        menu.addAction("Novo arquivo", self.new_file)
        menu.addAction("Terminal", self.open_terminal)
        menu.addAction("Console Python", self.open_python_console)
        plus.setMenu(menu)
        self.tabs.setCornerWidget(plus, Qt.Corner.TopRightCorner)
        editor_layout.addWidget(self.tabs)
        self.find_bar = QWidget()
        find_layout = QHBoxLayout(self.find_bar)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Localizar no arquivo…")
        self.find_input.returnPressed.connect(self.find_next)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Substituir por…")
        find_layout.addWidget(self.find_input)
        find_layout.addWidget(self.replace_input)
        for text, callback in [
            ("Próximo", self.find_next),
            ("Substituir", self.replace_one),
            ("Todos", self.replace_all),
            ("×", self.find_bar.hide),
        ]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            find_layout.addWidget(button)
        self.find_bar.hide()
        editor_layout.addWidget(self.find_bar)
        self.stack.addWidget(editor_area)

    def dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        title_bar = QWidget()
        title_bar.setObjectName("dockHeader")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 10, 10, 10)
        caption = QLabel(title)
        caption.setObjectName("dockCaption")
        title_layout.addWidget(caption)
        title_layout.addStretch()
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Ocultar painel")
        close.setObjectName("panelClose")
        close.clicked.connect(dock.hide)
        title_layout.addWidget(close)
        dock.setTitleBarWidget(title_bar)
        self.addDockWidget(area, dock)
        return dock

    def build_docks(self):
        self.model = QFileSystemModel(self)
        self.model.setFilter(
            QDir.Filter.AllDirs
            | QDir.Filter.Files
            | QDir.Filter.NoDotAndDotDot
            | QDir.Filter.Hidden
        )
        self.file_icons = ProjectIcons()
        self.model.setIconProvider(self.file_icons)
        self.tree_model = ProjectFilter(self)
        self.tree_model.setSourceModel(self.model)
        self.tree = QTreeView()
        self.tree.setModel(self.tree_model)
        self.tree.setObjectName("projectTree")
        self.tree.setIndentation(16)
        self.tree.setUniformRowHeights(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        for column in range(1, 4):
            self.tree.hideColumn(column)
        self.tree.doubleClicked.connect(self.open_tree_item)
        self.project_dock = self.dock("PROJETO", self.tree, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.resizeDocks([self.project_dock], [244], Qt.Orientation.Horizontal)
        self.outline = QListWidget()
        self.outline.itemActivated.connect(
            lambda item: (
                self.editor().goto(item.data(Qt.ItemDataRole.UserRole)) if self.editor() else None
            )
        )
        self.outline_dock = self.dock(
            "ESTRUTURA", self.outline, Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.outline_dock.hide()
        self.tools = QTabWidget()
        self.tools.tabBar().setDrawBase(False)
        self.run_panel = ProcessPanel()
        self.command_panel = ProcessPanel()
        command_widget = QWidget()
        command_layout = QVBoxLayout(command_widget)
        command_layout.setContentsMargins(0, 0, 0, 0)
        command_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Comando shell no projeto — ex.: git status, ls, python3 --version"
        )
        self.command_input.returnPressed.connect(self.run_command)
        command_row.addWidget(self.command_input)
        execute = QPushButton("Executar")
        execute.clicked.connect(self.run_command)
        command_row.addWidget(execute)
        command_layout.addLayout(command_row)
        command_layout.addWidget(self.command_panel)
        self.search_widget = QWidget()
        search_layout = QVBoxLayout(self.search_widget)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar texto no projeto… (Enter)")
        self.search_input.returnPressed.connect(self.search)
        self.search_results = QListWidget()
        self.search_results.itemActivated.connect(self.open_search_result)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_results)
        self.problems = QListWidget()
        self.problems.itemActivated.connect(self.open_search_result)
        git_widget = QWidget()
        git_layout = QVBoxLayout(git_widget)
        git_row = QHBoxLayout()
        for title, callback in [("Atualizar status", self.git_status), ("Diff", self.git_diff)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            git_row.addWidget(button)
        git_layout.addLayout(git_row)
        self.git_output = QPlainTextEdit()
        self.git_output.setReadOnly(True)
        self.git_output.setFont(QFont("Menlo", 12))
        git_layout.addWidget(self.git_output)
        for title, widget in [
            ("Execução / Debug", self.run_panel),
            ("Comandos", command_widget),
            ("Busca", self.search_widget),
            ("Problemas", self.problems),
            ("Git", git_widget),
        ]:
            self.tools.addTab(widget, title)
        self.tools_dock = self.dock(
            "FERRAMENTAS", self.tools, Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.resizeDocks([self.tools_dock], [240], Qt.Orientation.Vertical)
        self.tools_dock.hide()

    def action(self, menu, text, callback, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(callback)
        if text in {
            "Salvar",
            "Salvar como…",
            "Desfazer",
            "Refazer",
            "Recortar",
            "Localizar / substituir",
            "Comentar / descomentar",
            "Formatar Python (Ruff)",
            "Ir para linha…",
            "Ir para definição",
            "Documentação do símbolo",
            "Executar arquivo Python",
            "Depurar arquivo Python (pdb)",
        }:
            self.document_actions.append(action)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        self.addAction(action)
        self.commands.append((text, callback))
        return action

    def build_actions(self):
        self.commands = []
        self.edit_actions = {}
        self.document_actions = []
        file = self.menuBar().addMenu("Arquivo")
        self.action(file, "Novo arquivo", self.new_file, QKeySequence.StandardKey.New)
        self.action(file, "Abrir arquivo…", self.choose_file, QKeySequence.StandardKey.Open)
        self.action(file, "Abrir projeto…", self.choose_project, "Ctrl+Alt+O")
        self.close_project_action = self.action(file, "Fechar projeto/pasta", self.close_project)
        self.close_project_action.setEnabled(False)
        self.action(file, "Criar arquivo no projeto…", self.create_project_file)
        file.addSeparator()
        self.action(file, "Salvar", self.save_current, QKeySequence.StandardKey.Save)
        self.action(
            file,
            "Salvar como…",
            lambda: self.save_current(save_as=True),
            QKeySequence.StandardKey.SaveAs,
        )
        self.action(file, "Salvar todos", self.save_all, "Ctrl+Alt+S")
        self.close_document_action = self.action(
            file,
            "Fechar aba",
            lambda: self.close_tab(self.tabs.currentIndex()),
            QKeySequence.StandardKey.Close,
        )
        self.action(file, "Preferências…", self.preferences, "Ctrl+,")
        edit = self.menuBar().addMenu("Editar")
        for title, method, shortcut in [
            ("Desfazer", "undo", QKeySequence.StandardKey.Undo),
            ("Refazer", "redo", QKeySequence.StandardKey.Redo),
            ("Recortar", "cut", QKeySequence.StandardKey.Cut),
            ("Copiar", "copy", QKeySequence.StandardKey.Copy),
            ("Colar", "paste", QKeySequence.StandardKey.Paste),
        ]:
            self.edit_actions[method] = self.action(
                edit, title, lambda checked=False, m=method: self.invoke_edit(m), shortcut
            )
        edit.addSeparator()
        self.action(edit, "Localizar / substituir", self.show_find, QKeySequence.StandardKey.Find)
        self.action(edit, "Comentar / descomentar", self.toggle_comment, "Ctrl+/")
        self.action(edit, "Formatar Python (Ruff)", self.format_code, "Ctrl+Alt+L")
        navigate = self.menuBar().addMenu("Navegar")
        self.action(navigate, "Abrir rapidamente…", self.quick_open, "Ctrl+P")
        self.action(navigate, "Paleta de comandos…", self.command_palette, "Ctrl+Shift+P")
        self.action(navigate, "Ir para linha…", self.goto_line, "Ctrl+L")
        self.action(navigate, "Ir para definição", self.definition, "F12")
        self.action(navigate, "Documentação do símbolo", self.documentation, "Shift+F1")
        run = self.menuBar().addMenu("Executar")
        self.action(run, "Executar arquivo Python", self.run_file, "Ctrl+R")
        self.action(
            run, "Depurar arquivo Python (pdb)", lambda: self.run_file(debug=True), "Ctrl+D"
        )
        self.action(run, "Parar", self.run_panel.stop, "Shift+F5")
        self.action(run, "Argumentos de execução…", self.set_arguments)
        self.action(run, "Executar testes (unittest)", self.run_tests, "Ctrl+Shift+T")
        self.action(run, "Analisar projeto (Ruff)", self.lint_project)
        terminal = self.menuBar().addMenu("Terminal")
        self.action(terminal, "Novo terminal", self.open_terminal, "Ctrl+Shift+J")
        self.action(terminal, "Novo console Python", self.open_python_console, "Ctrl+Shift+K")
        self.action(
            terminal,
            "Alternar para terminal",
            self.focus_terminal,
            "Meta+`" if sys.platform == "darwin" else "Ctrl+`",
        )
        environment = self.menuBar().addMenu("Ambiente")
        self.action(environment, "Selecionar interpretador…", self.preferences)
        self.action(environment, "Criar .venv no projeto", self.create_venv)
        self.action(environment, "Listar pacotes do interpretador", self.list_packages)
        view = self.menuBar().addMenu("Visualizar")
        self.action(view, "Alternar tema claro / escuro", self.toggle_theme, "Ctrl+Alt+T")
        for dock in [self.project_dock, self.outline_dock, self.tools_dock]:
            view.addAction(dock.toggleViewAction())
        self.action(view, "Buscar no projeto", self.show_search, "Ctrl+Shift+F")
        self.action(view, "Git: status", self.git_status)
        self.action(view, "Comando isolado (painel)", lambda: self.show_tool(1))
        generated = QAction("Mostrar arquivos gerados no projeto", self)
        generated.setCheckable(True)
        generated.toggled.connect(self.show_generated_files)
        view.addAction(generated)
        help_menu = self.menuBar().addMenu("Ajuda")
        self.action(
            help_menu,
            "Sobre o EditPy",
            lambda: QMessageBox.about(
                self,
                "EditPy",
                "EditPy 0.4.0\nIDE Python independente.\n\nEditor • Jedi • Ruff • pdb • Git\nPrimeira versão macOS.\n\nConsulte docs/ROADMAP.md para a cobertura de recursos.",
            ),
        )

    def build_toolbar(self):
        toolbar = self.addToolBar("Principal")
        toolbar.setMovable(False)
        toolbar.setObjectName("mainToolbar")
        self.brand_label = QLabel()
        self.brand_label.setAccessibleName("EditPy")
        self.brand_label.setContentsMargins(4, 0, 18, 0)
        toolbar.addWidget(self.brand_label)
        self.project_label = QLabel("Seu espaço de desenvolvimento")
        self.project_label.setObjectName("workspaceName")
        toolbar.addWidget(self.project_label)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        search = QPushButton(
            "Buscar arquivos ou comandos…     ⌘P"
            if sys.platform == "darwin"
            else "Buscar arquivos ou comandos…     Ctrl+P"
        )
        search.setObjectName("commandSearch")
        search.setMinimumWidth(280)
        search.clicked.connect(self.quick_open)
        toolbar.addWidget(search)
        self.editor_buttons = []
        for text, callback, name in [
            ("›_  Terminal", self.open_terminal, "terminalButton"),
            ("▷  Executar", self.run_file, "runButton"),
            ("◉  Debug", lambda: self.run_file(debug=True), "quietButton"),
            ("◐  Tema", self.toggle_theme, "quietButton"),
        ]:
            button = QPushButton(text)
            button.setObjectName(name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            if name == "runButton" or "Debug" in text:
                self.editor_buttons.append(button)
                button.setEnabled(self.editor() is not None)
        rail = self.addToolBar("Atalhos")
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, rail)
        rail.setMovable(False)
        rail.setObjectName("activityRail")
        from PySide6.QtCore import QSize

        rail.setIconSize(QSize(22, 22))
        for icon, title, callback in [
            (
                "folder",
                "Explorador do projeto",
                lambda: self.project_dock.setVisible(not self.project_dock.isVisible()),
            ),
            ("search", "Buscar no projeto", self.show_search),
            ("git", "Git", self.git_status),
            ("terminal", "Abrir terminal", self.open_terminal),
            ("python", "Abrir console Python", self.open_python_console),
        ]:
            action = rail.addAction(self.asset_icon(icon), title)
            action.triggered.connect(callback)

    @staticmethod
    def asset_icon(name):
        return QIcon(
            str(Path(__file__).parent / "assets" / f"{'git-branch' if name == 'git' else name}.svg")
        )

    def editors(self):
        return [
            self.tabs.widget(i)
            for i in range(self.tabs.count())
            if isinstance(self.tabs.widget(i), CodeEditor)
        ]

    def terminals(self):
        return [
            self.tabs.widget(i)
            for i in range(self.tabs.count())
            if isinstance(self.tabs.widget(i), TerminalTab)
        ]

    def open_terminal(self, checked=False, console=False):
        if not self.interpreter and (console or os.name != "nt"):
            return self.error("Selecione um interpretador Python em Preferências.")
        try:
            tab = TerminalTab(
                self.interpreter, self.root or Path.home(), self.theme, self.font_size, console
            )
        except (OSError, RuntimeError) as error:
            return self.error(error)
        if console:
            self.console_count += 1
            title = f"Python {self.console_count}"
        else:
            self.terminal_count += 1
            title = f"Terminal {self.terminal_count}"
        self.tabs.addTab(tab, self.asset_icon("python" if console else "terminal"), title)
        self.tabs.setTabToolTip(self.tabs.indexOf(tab), f"{title} — {tab.cwd}")
        self.tabs.setCurrentWidget(tab)
        self.stack.setCurrentIndex(1)
        tab.view.setFocus()
        return tab

    def open_python_console(self):
        return self.open_terminal(console=True)

    def focus_terminal(self):
        terminals = self.terminals()
        if terminals:
            self.tabs.setCurrentWidget(terminals[-1])
            terminals[-1].view.setFocus()
        else:
            self.open_terminal()

    def open_tree_item(self, index):
        source = self.tree_model.mapToSource(index)
        if not self.model.isDir(source):
            self.open_file(Path(self.model.filePath(source)))
        else:
            self.tree.setExpanded(index, not self.tree.isExpanded(index))

    def show_generated_files(self, show):
        self.tree_model.show_generated = show
        self.tree_model.invalidateFilter()

    def editor(self):
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def error(self, message):
        QMessageBox.warning(self, "EditPy", str(message))

    def background(self, function, callback):
        worker = Worker(function)
        generation = self.workspace_generation
        self.workers.add(worker)

        def done(result):
            self.workers.discard(worker)
            if generation == self.workspace_generation:
                callback(result)

        def failed(message):
            self.workers.discard(worker)
            if generation == self.workspace_generation:
                self.statusBar().showMessage(message, 10000)

        worker.signals.done.connect(done)
        worker.signals.failed.connect(failed)
        self.pool.start(worker)

    def session_key(self):
        import hashlib

        identity = hashlib.sha256(str(self.root).encode()).hexdigest()[:16]
        return f"sessions/{identity}/files"

    def choose_project(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Abrir projeto", str(self.root or Path.home())
        )
        if directory:
            self.open_project(Path(directory))

    def open_project(self, path, restore=False):
        path = path.resolve()
        if not path.is_dir():
            return self.error("A pasta do projeto não existe.")
        if not restore:
            # Resolve documents before stopping any terminal session.
            for editor in self.editors():
                if not self.confirm_document_close(editor):
                    return
            for index in reversed(range(self.tabs.count())):
                self.close_tab(index, confirmed=True)
        self.workspace_generation += 1
        self.root = path
        self.close_project_action.setEnabled(True)
        if self.tree.model() is None:
            self.tree.setModel(self.tree_model)
            for column in range(1, 4):
                self.tree.hideColumn(column)
        self.model.setRootPath(str(path))
        self.tree.setRootIndex(self.tree_model.mapFromSource(self.model.index(str(path))))
        self.project_label.setText(path.name)
        self.setWindowTitle(f"{path.name} — EditPy")
        self.settings.setValue("project", str(path))
        recents = self.settings.value("recents", [], type=list)
        self.settings.setValue("recents", [str(path)] + [p for p in recents if p != str(path)][:9])
        self.refresh_recents()
        if restore:
            for filename in self.settings.value(self.session_key(), [], type=list):
                if Path(filename).is_file():
                    self.open_file(Path(filename))
        self.statusBar().showMessage(str(path))

    def refresh_recents(self):
        self.recents.clear()
        for recent in self.settings.value("recents", [], type=list):
            if Path(recent).is_dir():
                item = QListWidgetItem(f"{Path(recent).name}   —   {recent}")
                item.setData(Qt.ItemDataRole.UserRole, recent)
                self.recents.addItem(item)

    def has_running_processes(self):
        return (
            self.run_panel.busy()
            or self.command_panel.busy()
            or any(tab.session.busy() for tab in self.terminals())
        )

    def stop_workspace_processes(self):
        for tab in self.terminals():
            tab.stop()
        for panel in (self.run_panel, self.command_panel):
            panel.stop()
            if panel.busy():
                panel.process.waitForFinished(1500)

    def close_project(self):
        if self.root is None:
            return True
        # Collect all decisions first. Cancelling preserves documents and sessions.
        for editor in self.editors():
            if not self.confirm_document_close(editor):
                return False
        if self.has_running_processes():
            answer = QMessageBox.question(
                self,
                "Fechar projeto/pasta",
                "Encerrar os processos e as sessões de terminal deste projeto e fechá-lo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        self.settings.setValue(self.session_key(), [str(e.path) for e in self.editors() if e.path])
        self.workspace_generation += 1
        self.search_version += 1
        self.outline_timer.stop()
        self.stop_workspace_processes()
        for index in reversed(range(self.tabs.count())):
            self.close_tab(index, confirmed=True)
        self.root = None
        self.arguments = ""
        self.settings.remove("project")
        self.settings.sync()
        self.tree.setModel(None)
        self.model.setRootPath("")
        self.outline.clear()
        self.search_results.clear()
        self.search_input.clear()
        self.problems.clear()
        self.git_output.clear()
        self.run_panel.output.clear()
        self.command_panel.output.clear()
        self.command_input.clear()
        self.find_bar.hide()
        self.find_input.clear()
        self.replace_input.clear()
        self.tools_dock.hide()
        self.breadcrumb.setText("  EDITOR")
        self.location.setText("Nenhum projeto aberto  ")
        self.project_label.setText("Seu espaço de desenvolvimento")
        self.setWindowTitle("EditPy")
        self.close_project_action.setEnabled(False)
        self.stack.setCurrentIndex(0)
        self.refresh_recents()
        self.statusBar().showMessage("Projeto fechado. Abra uma pasta para continuar.")
        return True

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", str(self.root or Path.home()))
        if path:
            self.open_file(Path(path))

    def new_file(self):
        self.add_editor(None, "")

    def create_project_file(self):
        if not self.root:
            return self.choose_project()
        name, ok = QInputDialog.getText(self, "Criar arquivo", "Caminho relativo ao projeto:")
        if ok and name:
            path = (self.root / name).resolve()
            if not path.is_relative_to(self.root):
                return self.error("Escolha um caminho dentro do projeto.")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x"):
                    pass
                self.open_file(path)
            except OSError as error:
                self.error(error)

    def open_file(self, path, line=None, column=0):
        path = path.resolve()
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            if isinstance(editor, CodeEditor) and editor.path == path:
                self.tabs.setCurrentIndex(index)
                if line:
                    editor.goto(line, column)
                return editor
        try:
            editor = self.add_editor(path, read_source(path))
            editor.disk_signature = self.signature(path)
            if line:
                editor.goto(line, column)
            return editor
        except (OSError, UnicodeError, ValueError, SyntaxError) as error:
            self.error(error)

    def add_editor(self, path, source):
        editor = CodeEditor(path, self.theme, self.font_size)
        editor.setPlainText(source)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda _: self.update_tab(editor))
        editor.textChanged.connect(lambda: self.outline_timer.start())
        editor.cursorPositionChanged.connect(self.update_position)
        editor.completion_requested.connect(self.complete)
        self.tabs.addTab(
            editor,
            self.file_icons.catalog.icon(path or "untitled.py"),
            path.name if path else "Sem título",
        )
        self.tabs.setCurrentWidget(editor)
        self.stack.setCurrentIndex(1)
        editor.setFocus()
        return editor

    def update_tab(self, editor):
        index = self.tabs.indexOf(editor)
        if index >= 0:
            self.tabs.setTabIcon(index, self.file_icons.catalog.icon(editor.path or "untitled.py"))
            self.tabs.setTabText(
                index,
                ("● " if editor.document().isModified() else "")
                + (editor.path.name if editor.path else "Sem título"),
            )
            self.tabs.setTabToolTip(index, str(editor.path or "Arquivo ainda não salvo"))

    @staticmethod
    def signature(path):
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def save_current(self, checked=False, save_as=False):
        editor = self.editor()
        return self.save_editor(editor, save_as) if editor else False

    def save_editor(self, editor, save_as=False):
        path = editor.path
        if not path or save_as:
            selected, _ = QFileDialog.getSaveFileName(
                self, "Salvar arquivo", str(path or (self.root or Path.home()) / "main.py")
            )
            if not selected:
                return False
            path = Path(selected).resolve()
            if any(other is not editor and other.path == path for other in self.editors()):
                self.error("Esse arquivo já está aberto em outra aba.")
                return False
        elif self.signature(path) != editor.disk_signature:
            answer = QMessageBox.question(
                self,
                "Arquivo alterado",
                "O arquivo mudou no disco ou foi removido. Sobrescrever com o conteúdo do editor?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        try:
            write_source(path, editor.toPlainText())
            editor.path = path
            editor.highlighter.set_path(path)
            editor.disk_signature = self.signature(path)
            editor.document().setModified(False)
            self.update_tab(editor)
            self.current_changed()
            self.statusBar().showMessage(f"Salvo: {path}", 4000)
            return True
        except (OSError, UnicodeError, SyntaxError) as error:
            self.error(error)
            return False

    def save_all(self):
        for editor in self.editors():
            if (editor.document().isModified() or not editor.path) and not self.save_editor(editor):
                return False
        return True

    def confirm_document_close(self, editor):
        if not editor.document().isModified():
            return True
        answer = QMessageBox.question(
            self,
            "Salvar alterações?",
            f"Salvar alterações em {editor.path.name if editor.path else 'Sem título'}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        return answer != QMessageBox.StandardButton.Save or self.save_editor(editor)

    def close_tab(self, index, confirmed=False):
        if index < 0:
            return True
        editor = self.tabs.widget(index)
        if isinstance(editor, TerminalTab):
            editor.stop()
        elif not confirmed and not self.confirm_document_close(editor):
            return False
        self.tabs.removeTab(index)
        editor.deleteLater()
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)
        return True

    def invoke_edit(self, method):
        editor = self.editor()
        if editor:
            getattr(editor, method)()
        elif isinstance(self.tabs.currentWidget(), TerminalTab):
            view = self.tabs.currentWidget().view
            if method == "copy":
                view.copy_selection()
            elif method == "paste":
                view.paste()

    def current_changed(self, *_):
        editor = self.editor()
        for action in getattr(self, "document_actions", []):
            action.setEnabled(editor is not None)
        for button in getattr(self, "editor_buttons", []):
            button.setEnabled(editor is not None)
        if sys.platform != "darwin" and hasattr(self, "edit_actions"):
            terminal = isinstance(self.tabs.currentWidget(), TerminalTab)
            self.close_document_action.setShortcut(
                "Ctrl+Shift+W" if terminal else QKeySequence(QKeySequence.StandardKey.Close)
            )
            for method, letter, default in [
                ("copy", "C", QKeySequence.StandardKey.Copy),
                ("paste", "V", QKeySequence.StandardKey.Paste),
            ]:
                self.edit_actions[method].setShortcut(
                    f"Ctrl+Shift+{letter}" if terminal else QKeySequence(default)
                )
        if editor:
            path = editor.path
            display = (
                str(path.relative_to(self.root))
                if path and self.root and path.is_relative_to(self.root)
                else str(path or "Sem título")
            )
            self.breadcrumb.setText("  " + display.replace(os.sep, "   /   "))
            self.refresh_outline()
        elif isinstance(self.tabs.currentWidget(), TerminalTab):
            tab = self.tabs.currentWidget()
            self.breadcrumb.setText(
                f"  {self.root.name if self.root else 'Local'}   /   {'Console Python' if tab.console else 'Terminal'}"
            )
            self.outline.clear()
            self.find_bar.hide()
        self.update_position()

    def update_position(self):
        editor = self.editor()
        if editor:
            cursor = editor.textCursor()
            self.location.setText(
                f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}   •   UTF-8   •   4 espaços   "
            )

        elif isinstance(self.tabs.currentWidget(), TerminalTab):
            self.location.setText("PTY   •   UTF-8   •   Sessão local  ")

    def check_external_changes(self):
        editor = self.editor()
        if editor and editor.path and editor.path.exists() and not editor.document().isModified():
            signature = self.signature(editor.path)
            if signature != editor.disk_signature:
                try:
                    position = editor.textCursor().position()
                    editor.setPlainText(read_source(editor.path))
                    editor.disk_signature = signature
                    cursor = editor.textCursor()
                    cursor.setPosition(min(position, editor.document().characterCount() - 1))
                    editor.setTextCursor(cursor)
                    editor.document().setModified(False)
                    self.statusBar().showMessage(
                        "Arquivo recarregado após alteração externa.", 4000
                    )
                except (OSError, UnicodeError, ValueError, SyntaxError):
                    pass

    def show_tool(self, index):
        self.tools_dock.show()
        self.tools.setCurrentIndex(index)

    def show_find(self):
        if self.editor():
            self.find_bar.show()
            if self.editor().textCursor().hasSelection():
                self.find_input.setText(self.editor().textCursor().selectedText())
            self.find_input.setFocus()

    def find_next(self):
        editor = self.editor()
        query = self.find_input.text()
        if editor and query:
            if not editor.find(query):
                cursor = editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(cursor)
                if not editor.find(query):
                    self.statusBar().showMessage("Texto não encontrado.", 3000)

    def replace_one(self):
        editor = self.editor()
        if editor and self.find_input.text():
            cursor = editor.textCursor()
            if cursor.selectedText().casefold() == self.find_input.text().casefold():
                cursor.insertText(self.replace_input.text())
            self.find_next()

    def replace_all(self):
        editor = self.editor()
        query = self.find_input.text()
        if not editor or not query:
            return
        import re

        text, count = re.subn(
            re.escape(query),
            lambda _: self.replace_input.text(),
            editor.toPlainText(),
            flags=re.IGNORECASE,
        )
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()
        self.statusBar().showMessage(f"{count} substituições.", 4000)

    def toggle_comment(self):
        editor = self.editor()
        if not editor:
            return
        cursor = editor.textCursor()
        start, end = sorted((cursor.selectionStart(), cursor.selectionEnd()))
        first = editor.document().findBlock(start)
        last = editor.document().findBlock(end)
        if end > start and end == last.position():
            last = last.previous()
        blocks = []
        block = first
        while block.isValid() and block.blockNumber() <= last.blockNumber():
            blocks.append(block)
            block = block.next()
        uncomment = all(not b.text().strip() or b.text().lstrip().startswith("#") for b in blocks)
        cursor.beginEditBlock()
        for block in reversed(blocks):
            text = block.text()
            offset = len(text) - len(text.lstrip())
            cursor.setPosition(block.position() + offset)
            if uncomment and text.lstrip().startswith("#"):
                cursor.deleteChar()
                if editor.document().characterAt(cursor.position()) == " ":
                    cursor.deleteChar()
            elif text.strip():
                cursor.insertText("# ")
        cursor.endEditBlock()

    def goto_line(self):
        editor = self.editor()
        if editor:
            line, ok = QInputDialog.getInt(
                self, "Ir para linha", "Linha:", 1, 1, editor.blockCount()
            )
            if ok:
                editor.goto(line)

    def picker(self, title, entries, callback):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(700, 440)
        layout = QVBoxLayout(dialog)
        query = QLineEdit()
        query.setPlaceholderText("Digite para filtrar…")
        items = QListWidget()
        layout.addWidget(query)
        layout.addWidget(items)

        def populate(text):
            items.clear()
            for label, data in entries:
                if text.casefold() in label.casefold():
                    item = QListWidgetItem(label)
                    item.setData(Qt.ItemDataRole.UserRole, data)
                    items.addItem(item)
                    if items.count() >= 500:
                        break
            items.setCurrentRow(0)

        def activate(item=None):
            item = item or items.currentItem()
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                dialog.accept()
                callback(data)

        query.textChanged.connect(populate)
        query.returnPressed.connect(activate)
        items.itemActivated.connect(activate)
        populate("")
        dialog.exec()

    def command_palette(self):
        commands = list(self.commands)
        self.picker(
            "Comandos",
            [(title, i) for i, (title, _) in enumerate(commands)],
            lambda i: commands[i][1](),
        )

    def quick_open(self):
        if not self.root:
            return self.choose_file()
        from .services import project_files

        root = self.root

        def collect():
            entries = []
            for path in project_files(root):
                entries.append((str(path.relative_to(root)), str(path)))
                if len(entries) >= 20000:
                    break
            return entries

        self.background(
            collect,
            lambda entries: self.picker(
                "Abrir arquivo — até 20.000 arquivos indexados",
                entries,
                lambda p: self.open_file(Path(p)),
            ),
        )

    def show_search(self):
        self.show_tool(2)
        self.search_input.setFocus()

    def search(self):
        if not self.root:
            return self.error("Abra uma pasta de projeto primeiro.")
        self.search_version += 1
        version = self.search_version
        query, root = self.search_input.text(), self.root
        self.search_results.clear()
        self.statusBar().showMessage("Buscando…")

        def done(results):
            if version != self.search_version or root != self.root:
                return
            for match in results:
                item = QListWidgetItem(
                    f"{match.path.relative_to(root)}:{match.line}   {match.text}"
                )
                item.setData(Qt.ItemDataRole.UserRole, (str(match.path), match.line, 0))
                self.search_results.addItem(item)
            self.statusBar().showMessage(f"{len(results)} resultados (limite de 1.000).", 8000)

        self.background(lambda: search_project(root, query), done)

    def open_search_result(self, item):
        path, line, column = item.data(Qt.ItemDataRole.UserRole)
        self.open_file(Path(path), line, column)

    def refresh_outline(self):
        self.outline.clear()
        editor = self.editor()
        if not editor:
            return
        for name, line, kind in symbols(editor.toPlainText()):
            item = QListWidgetItem(f"{'◇' if kind == 'ClassDef' else 'ƒ'}  {name}   :{line}")
            item.setData(Qt.ItemDataRole.UserRole, line)
            self.outline.addItem(item)
        if not editor.path or editor.path.suffix == ".py":
            problem = syntax_problem(editor.toPlainText())
            self.statusBar().showMessage(
                f"Linha {problem[0]}: {problem[2]}" if problem else "Python • Sintaxe válida", 2500
            )

    def intelligence(self, operation):
        editor = self.editor()
        if not editor:
            return
        source = editor.toPlainText()
        cursor = editor.textCursor()
        line, column = cursor.blockNumber() + 1, cursor.positionInBlock()
        path = editor.path
        root = self.root

        def work():
            import jedi

            script = jedi.Script(
                source,
                path=str(path) if path else None,
                project=jedi.Project(
                    str(root or (path.parent if path else Path.cwd())),
                    environment_path=self.interpreter or None,
                ),
            )
            if operation == "complete":
                return [c.name for c in script.complete(line, column)]
            if operation == "definition":
                return [
                    (str(d.module_path), d.line, d.column, d.full_name)
                    for d in script.goto(line, column, follow_imports=True)
                    if d.module_path and d.line
                ]
            return "\n\n".join(d.docstring() for d in script.infer(line, column))

        def done(result):
            if self.tabs.indexOf(editor) < 0:
                return
            if operation == "complete":
                if (
                    editor.toPlainText() == source
                    and editor.textCursor().position() == cursor.position()
                ):
                    editor.show_completions(result)
            elif operation == "definition":
                if result:
                    self.open_file(Path(result[0][0]), result[0][1], result[0][2])
                else:
                    self.statusBar().showMessage("Definição não encontrada.", 4000)
            else:
                dialog = QDialog(self)
                dialog.setWindowTitle("Documentação")
                dialog.resize(720, 500)
                layout = QVBoxLayout(dialog)
                text = QPlainTextEdit(result or "Nenhuma documentação disponível.")
                text.setReadOnly(True)
                layout.addWidget(text)
                dialog.exec()

        self.background(work, done)

    def complete(self):
        self.intelligence("complete")

    def definition(self):
        self.intelligence("definition")

    def documentation(self):
        self.intelligence("documentation")

    def run_file(self, checked=False, debug=False):
        editor = self.editor()
        if not editor:
            return self.error("Abra um arquivo Python para executar.")
        if not self.save_all():
            return
        if editor.path.suffix not in {".py", ".pyw"}:
            return self.error("Selecione um arquivo .py ou .pyw.")
        if not self.interpreter:
            return self.preferences()
        try:
            arguments = parse_arguments(self.arguments)
        except ValueError as error:
            return self.error(error)
        args = ["-u"]
        if debug:
            args += ["-m", "pdb"]
            for line in sorted(editor.breakpoints):
                args += ["-c", f"break {line}"]
            if editor.breakpoints:
                args += ["-c", "continue"]
        args += [str(editor.path), *arguments]
        self.show_tool(0)
        if debug:
            self.run_panel.append(
                "\nDEBUG PDB  •  n: próxima linha  •  s: entrar  •  c: continuar\np expressão: inspecionar  •  where: pilha  •  q: sair\n"
            )
        self.run_panel.start(self.interpreter, args, self.root or editor.path.parent)

    def set_arguments(self):
        arguments, ok = QInputDialog.getText(
            self,
            "Configuração de execução",
            "Argumentos do arquivo (sintaxe shell):",
            text=self.arguments,
        )
        if ok:
            self.arguments = arguments

    def run_tests(self):
        if not self.root:
            return self.error("Abra um projeto primeiro.")
        if self.save_all():
            self.show_tool(0)
            self.run_panel.start(self.interpreter, ["-m", "unittest", "discover", "-v"], self.root)

    def run_command(self):
        command = self.command_input.text().strip()
        if command:
            self.show_tool(1)
            shell = (
                os.environ.get("COMSPEC", "cmd.exe")
                if os.name == "nt"
                else "/bin/zsh"
                if sys.platform == "darwin"
                else "/bin/sh"
            )
            self.command_panel.start(
                shell, ["/c" if os.name == "nt" else "-c", command], self.root or Path.home()
            )

    @staticmethod
    def ruff_command():
        if getattr(sys, "frozen", False):
            return [str(Path(sys._MEIPASS) / ("ruff.exe" if os.name == "nt" else "ruff"))]
        return [sys.executable, "-m", "ruff"]

    def format_code(self):
        editor = self.editor()
        if not editor:
            return
        source = editor.toPlainText()
        filename = str(editor.path or "main.py")

        def work():
            result = subprocess.run(
                [*self.ruff_command(), "format", "--stdin-filename", filename, "-"],
                input=source,
                text=True,
                capture_output=True,
                timeout=20,
            )
            if result.returncode:
                raise ValueError(result.stderr)
            return result.stdout

        def done(formatted):
            if self.tabs.indexOf(editor) < 0 or editor.toPlainText() != source:
                return self.statusBar().showMessage(
                    "O arquivo mudou durante a formatação. Tente novamente.", 4000
                )
            cursor = editor.textCursor()
            position = cursor.position()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(formatted)
            cursor.endEditBlock()
            cursor.setPosition(min(position, editor.document().characterCount() - 1))
            editor.setTextCursor(cursor)

        self.background(work, done)

    def lint_project(self):
        if not self.root:
            return self.error("Abra um projeto primeiro.")
        if not self.save_all():
            return
        root = self.root

        def work():
            import json

            result = subprocess.run(
                [*self.ruff_command(), "check", "--output-format", "json", str(root)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode not in (0, 1):
                raise ValueError(result.stderr)
            return json.loads(result.stdout)

        def done(problems):
            self.problems.clear()
            for problem in problems:
                path, loc = problem["filename"], problem["location"]
                item = QListWidgetItem(
                    f"{Path(path).name}:{loc['row']}  {problem['code']}  {problem['message']}"
                )
                item.setData(Qt.ItemDataRole.UserRole, (path, loc["row"], loc["column"] - 1))
                self.problems.addItem(item)
            self.show_tool(3)
            self.statusBar().showMessage(f"{len(problems)} problemas encontrados.", 5000)

        self.background(work, done)

    def git(self, args):
        if not self.root:
            return self.error("Abra um projeto primeiro.")
        root = self.root
        self.show_tool(4)
        self.git_output.setPlainText("Consultando Git…")

        def work():
            result = subprocess.run(
                ["git", "-C", str(root), "--no-pager", *args],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return result.stdout + result.stderr

        self.background(
            work, lambda result: self.git_output.setPlainText(result or "Sem alterações.")
        )

    def git_status(self):
        self.git(["status", "--short", "--branch"])

    def git_diff(self):
        self.git(["diff", "--no-ext-diff", "HEAD", "--"])

    def create_venv(self):
        if not self.root:
            return self.error("Abra um projeto primeiro.")
        path = self.root / ".venv"
        if path.exists():
            return self.error(
                "A pasta .venv já existe. Selecione seu interpretador em Preferências."
            )
        self.show_tool(0)
        self.run_panel.start(self.interpreter, ["-m", "venv", str(path)], self.root)

    def list_packages(self):
        self.show_tool(0)
        self.run_panel.start(self.interpreter, ["-m", "pip", "list"], self.root or Path.home())

    def set_theme(self, theme):
        self.theme = theme
        app = QApplication.instance()
        # Stylesheets only affect widgets; the platform also needs an explicit
        # color scheme so macOS updates the native title bar and dialogs.
        app.styleHints().setColorScheme(
            Qt.ColorScheme.Dark if theme == "dark" else Qt.ColorScheme.Light
        )
        app.setStyleSheet(stylesheet(theme))
        apply_native_theme(self, theme)
        self.settings.setValue("theme", theme)
        self.update_brand()
        for i in range(self.tabs.count()):
            self.tabs.widget(i).apply_theme(theme)

    def toggle_theme(self):
        self.set_theme("light" if self.theme == "dark" else "dark")

    def preferences(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Preferências do EditPy")
        dialog.setMinimumWidth(620)
        layout = QFormLayout(dialog)
        interpreter = QLineEdit(self.interpreter)
        row = QHBoxLayout()
        row.addWidget(interpreter)
        browse = QPushButton("Selecionar…")

        def choose():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "Executável Python", str(Path(self.interpreter).parent)
            )
            if path:
                interpreter.setText(path)

        browse.clicked.connect(choose)
        row.addWidget(browse)
        layout.addRow("Interpretador Python", row)
        theme = QComboBox()
        theme.addItems(["Escuro", "Claro"])
        theme.setCurrentIndex(0 if self.theme == "dark" else 1)
        layout.addRow("Aparência", theme)
        size = QSpinBox()
        size.setRange(10, 28)
        size.setValue(self.font_size)
        layout.addRow("Tamanho da fonte", size)
        note = QLabel(
            "Selecione o executável do ambiente virtual para executar e depurar.\nA conclusão Jedi consulta o interpretador selecionado."
        )
        note.setObjectName("muted")
        layout.addRow(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            path = Path(interpreter.text()).expanduser()
            if not path.is_file() or not os.access(path, os.X_OK):
                return self.error("Selecione um executável Python válido.")
            self.interpreter = str(path)
            self.font_size = size.value()
            self.settings.setValue("interpreter", self.interpreter)
            self.settings.setValue("font_size", self.font_size)
            self.set_theme("dark" if theme.currentIndex() == 0 else "light")
            for tab in self.terminals():
                tab.view.set_font_size(self.font_size)
            for editor in self.editors():
                font = editor.font()
                font.setPointSize(self.font_size)
                editor.setFont(font)
                editor.setStyleSheet(
                    f"font-family: Menlo, Consolas, monospace; font-size: {self.font_size}pt; font-weight: 400;"
                )
                editor.setTabStopDistance(editor.fontMetrics().horizontalAdvance(" ") * 4)
                editor.update_gutter_width()

    def closeEvent(self, event):
        if self.has_running_processes():
            answer = QMessageBox.question(
                self,
                "Processos em execução",
                "Encerrar os processos e as sessões de terminal e fechar o EditPy?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        # Resolve all unsaved changes before closing any tab or terminating processes.
        for editor in self.editors():
            if editor.document().isModified():
                answer = QMessageBox.question(
                    self,
                    "Salvar alterações?",
                    f"Salvar {editor.path or 'Sem título'}?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if answer == QMessageBox.StandardButton.Cancel or (
                    answer == QMessageBox.StandardButton.Save and not self.save_editor(editor)
                ):
                    event.ignore()
                    return
        self.stop_workspace_processes()
        self.settings.setValue("geometry", self.saveGeometry())
        if self.root is not None:
            self.settings.setValue(
                self.session_key(),
                [str(editor.path) for editor in self.editors() if editor.path],
            )
        self.settings.sync()
        self.pool.waitForDone(3000)
        event.accept()
