"""Find inactive files and folders."""

import time
from features.common import is_link


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


def run(args):
    items = find_unused(args.folder, args.days)
    for path in items:
        kind = "Folder" if path.is_dir() else "File"
        print(f"{kind}: {path.relative_to(args.folder)}")
    print(f"Found {len(items)} inactive item(s).")
    return 0
