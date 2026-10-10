"""Small helpers shared by file management features."""

import os
import stat
from pathlib import Path


def collect_files(folder, recursive=True):
    """Collect regular files without following symbolic links."""
    paths = collect_items(folder) if recursive else folder.iterdir()
    return sorted(path for path in paths if not is_link(path) and path.is_file())


def collect_items(folder):
    """Walk a folder while skipping links and Windows junctions."""
    items = []
    for root, folders, names in os.walk(folder, onerror=raise_scan_error):
        folders[:] = sorted(name for name in folders if not is_link(Path(root) / name))
        for name in sorted(folders + names):
            path = Path(root) / name
            if not is_link(path):
                items.append(path)
    return sorted(items)


def is_link(path):
    try:
        details = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag) or path.is_symlink()


def raise_scan_error(error):
    raise error


def format_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
