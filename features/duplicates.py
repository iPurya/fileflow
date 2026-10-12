"""Find duplicate content using file sizes and SHA-256 hashes."""

import hashlib
from collections import defaultdict

from features.common import check_inside, collect_files, confirm_delete


def file_hash(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f"File changed while reading: {path}")
    return digest.hexdigest()


def find_duplicates(folder):
    sizes = defaultdict(list)
    for path in collect_files(folder):
        sizes[path.stat().st_size].append(path)
    groups = []
    for paths in sizes.values():
        if len(paths) < 2:
            continue
        hashes = defaultdict(list)
        for path in paths:
            hashes[file_hash(path)].append(path)
        groups.extend(group for group in hashes.values() if len(group) > 1)
    return groups


def run(args):
    groups = find_duplicates(args.folder)
    count = 0
    for group in groups:
        print(f"Keep: {group[0].relative_to(args.folder)}")
        for path in group[1:]:
            print(f"  Duplicate: {path.relative_to(args.folder)}")
            count += 1
    print(f"Found {count} duplicate file(s) in {len(groups)} group(s).")
    if args.delete and count and confirm_delete(count):
        for group in groups:
            keeper = group[0]
            for path in group[1:]:
                check_inside(keeper, args.folder)
                check_inside(path, args.folder)
                if file_hash(keeper) != file_hash(path):
                    raise OSError(f"Duplicate changed since the scan: {path}")
                path.unlink()
                print(f"Deleted: {path.relative_to(args.folder)}")
    return 0
