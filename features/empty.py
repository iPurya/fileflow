"""Find and optionally delete zero-byte files."""

from features.common import check_inside, collect_files, confirm_delete


def find_empty(folder):
    return [path for path in collect_files(folder) if path.stat().st_size == 0]


def run(args):
    files = find_empty(args.folder)
    for path in files:
        print(path.relative_to(args.folder))
    print(f"Found {len(files)} empty file(s).")
    if args.delete and files and confirm_delete(len(files)):
        for path in files:
            check_inside(path, args.folder)
            if path.stat().st_size != 0:
                raise OSError(f"File is no longer empty: {path}")
            path.unlink()
            print(f"Deleted: {path.relative_to(args.folder)}")
    return 0
