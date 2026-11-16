"""Build and smoke-test the portable Windows x64 distribution on Windows."""

import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect_notices():
    out = ROOT / "build" / "third-party-licenses"
    for package in [
        "PySide6-Essentials",
        "shiboken6",
        "jedi",
        "parso",
        "ruff",
        "pyte",
        "wcwidth",
        "Pygments",
        "pywinpty",
    ]:
        dist = importlib.metadata.distribution(package)
        for file in dist.files or []:
            if any(
                part.lower() in {"licenses", "license", "license.txt", "copying", "copying.txt"}
                for part in file.parts
            ):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = out / package / Path(*file.parts[-2:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    license = Path(sys.base_prefix) / "LICENSE.txt"
    if license.exists():
        (out / "Python").mkdir(parents=True, exist_ok=True)
        shutil.copy2(license, out / "Python" / "LICENSE.txt")


def main():
    if sys.platform != "win32":
        raise SystemExit("Execute este build em Windows; o PyInstaller não faz cross-compilation.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    numbers = tuple(int(p) for p in version.split(".")) + (0,)
    (build / "windows-version.txt").write_text(
        f"""VSVersionInfo(
ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
kids=[StringFileInfo([StringTable('040904B0', [
StringStruct('CompanyName', 'EditPy'), StringStruct('FileDescription', 'EditPy Python IDE'),
StringStruct('FileVersion', '{version}'), StringStruct('ProductName', 'EditPy'),
StringStruct('ProductVersion', '{version}'), StringStruct('OriginalFilename', 'EditPy.exe')
])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])""",
        encoding="utf-8",
    )
    collect_notices()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "create_windows_icon.py")], check=True)
    staging = build / "windows-dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(staging),
            "--workpath",
            str(build / "windows-work"),
            str(ROOT / "packaging" / "windows.spec"),
        ],
        cwd=ROOT,
        check=True,
    )
    executable = staging / "EditPy" / "EditPy.exe"
    # GUI executables require an explicit wait under PowerShell; subprocess.run does that.
    subprocess.run(
        [str(executable), "--smoke-test", str(build / "windows-package-smoke.json")],
        cwd=ROOT,
        check=True,
        timeout=120,
    )
    report = json.loads((build / "windows-package-smoke.json").read_text())
    if not report.get("ok"):
        raise RuntimeError(f"Validação do executável falhou: {report}")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    output = shutil.make_archive(
        str(dist / f"EditPy-{version}-Windows-x64"), "zip", root_dir=staging, base_dir="EditPy"
    )
    digest = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    Path(output + ".sha256").write_text(f"{digest}  {Path(output).name}\n")
    print(f"Windows portátil: {output}")


if __name__ == "__main__":
    main()
