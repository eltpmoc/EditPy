"""Filesystem operations shared by the explorer's menus, clipboard and drops."""

import os
import shutil
from pathlib import Path


def selected_roots(paths):
    """Deduplicate a selection, without following symlinks to their targets."""
    absolute = [Path(os.path.abspath(p)) for p in paths]
    unique = list(dict.fromkeys(p.parent.resolve() / p.name for p in absolute))
    return [p for p in unique if not any(q != p and q in p.parents for q in unique)]


def transfer_plan(paths, directory, copy=False):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError("A pasta de destino não existe.")
    plan = []
    names = set()
    for source in selected_roots(paths):
        if not os.path.lexists(source):
            raise ValueError(f"O item não existe mais: {source}")
        target = directory / source.name
        if not (source.is_symlink() or source.is_file() or source.is_dir()):
            raise ValueError(f"Tipo de arquivo não suportado: {source}")
        if copy and target == source:
            base = source.name if source.is_dir() else source.stem
            suffix = "" if source.is_dir() else source.suffix
            number = 1
            while True:
                label = " cópia" if number == 1 else f" cópia {number}"
                target = directory / f"{base}{label}{suffix}"
                if not os.path.lexists(target) and os.path.normcase(str(target)) not in names:
                    break
                number += 1
        identity = os.path.normcase(str(target))
        if identity in names or os.path.lexists(target):
            raise ValueError(
                f"Já existe um item chamado {source.name} no destino. Nada foi substituído."
            )
        if source.is_dir() and directory.is_relative_to(source.resolve()):
            raise ValueError("Uma pasta não pode ser copiada ou movida para dentro dela mesma.")
        names.add(identity)
        plan.append((source, target))
    return plan


def transfer_item(source, target, move=False):
    if os.path.lexists(target):
        raise FileExistsError(f"O destino já existe: {target}")
    if move:
        shutil.move(str(source), str(target))
    elif source.is_symlink():
        target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        # Exclusive creation prevents an existing destination from being overwritten.
        with source.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        shutil.copystat(source, target)
