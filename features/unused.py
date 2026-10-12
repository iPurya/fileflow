"""Find inactive files and folders, then archive or delete selected items."""

import shutil
import time
from zipfile import ZIP_DEFLATED, ZipFile

from features.common import (
    check_inside,
    collect_items,
    confirm_delete,
    is_link,
    item_state,
)


def find_unused(folder, days):
    cutoff = time.time() - days * 24 * 60 * 60

    def scan(directory):
        # Read directory times before listing it, which can update access time.
        details = directory.stat()
        latest = max(details.st_atime, details.st_mtime)
        items = []
        for path in sorted(directory.iterdir()):
            if is_link(path):
                latest = max(latest, time.time())
                continue
            if path.is_dir():
                children, accessed = scan(path)
                if accessed < cutoff:
                    items.append(path)
                else:
                    items.extend(children)
            elif path.is_file():
                details = path.stat()
                accessed = max(details.st_atime, details.st_mtime)
                if accessed < cutoff:
                    items.append(path)
            else:
                accessed = time.time()
            latest = max(latest, accessed)
        return items, latest

    items, latest = scan(folder)
    return items


def archive_items(items, folder, destination):
    destination = destination.expanduser().resolve()
    if destination.is_relative_to(folder):
        raise ValueError("Save the archive outside the scanned folder")
    destination.parent.mkdir(parents=True, exist_ok=True)
    archive = ZipFile(destination, "x", compression=ZIP_DEFLATED)
    try:
        with archive:
            for item in items:
                paths = [item]
                if item.is_dir():
                    paths.extend(collect_items(item))
                for path in paths:
                    check_inside(path, folder)
                    archive.write(path, arcname=str(path.relative_to(folder)))
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def run(args):
    items = find_unused(args.folder, args.days)
    for path in items:
        kind = "Folder" if path.is_dir() else "File"
        print(f"{kind}: {path.relative_to(args.folder)}")
    print(f"Found {len(items)} inactive item(s).")
    if not items:
        return 0
    if args.archive:
        destination = archive_items(items, args.folder, args.archive)
        print(f"Archived to: {destination}. Original files were kept.")
    elif args.delete:
        states = {path: item_state(path) for path in items}
        if not confirm_delete(len(items)):
            return 0
        for path in items:
            check_inside(path, args.folder)
            if item_state(path) != states[path]:
                raise OSError(f"Item changed since the scan: {path}")
        for path in items:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"Deleted: {path.relative_to(args.folder)}")
    return 0
