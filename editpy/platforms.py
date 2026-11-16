"""Platform details kept out of editor and project logic."""

import os
import shlex
import shutil
import sys


def shell_command():
    if os.name == "nt":
        # cmd is available on every supported Windows installation; no profile scripts.
        return [
            os.environ.get("COMSPEC") or shutil.which("cmd.exe") or r"C:\Windows\System32\cmd.exe",
            "/Q",
        ]
    shell = os.environ.get("SHELL", "/bin/zsh" if sys.platform == "darwin" else "/bin/bash")
    return [shell if os.path.isfile(shell) else "/bin/sh", "-i"]


def parse_arguments(text):
    if os.name != "nt":
        return shlex.split(text)
    import ctypes
    from ctypes import wintypes

    count = ctypes.c_int()
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    argv = parse("editpy " + text, ctypes.byref(count))
    if not argv:
        raise ValueError("Argumentos inválidos para o Windows.")
    try:
        return [argv[i] for i in range(1, count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(argv)


def apply_native_theme(window, theme):
    if sys.platform == "win32":
        import ctypes

        value = ctypes.c_int(theme == "dark")
        setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
        setter.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        setter.restype = ctypes.c_long
        setter(int(window.winId()), 20, ctypes.byref(value), ctypes.sizeof(value))
