"""Count file extensions and display the largest files."""

from collections import Counter

from features.common import collect_files, format_size


def analyze(folder):
    counts = Counter()
    sizes = []
    for path in collect_files(folder):
        counts[path.suffix.lower() or "[no extension]"] += 1
        sizes.append((path, path.stat().st_size))
    sizes.sort(key=lambda item: (-item[1], str(item[0])))
    return counts, sizes


def run(args):
    counts, sizes = analyze(args.folder)
    print(f"Files: {len(sizes)}")
    print(f"Total size: {format_size(sum(size for path, size in sizes))}")
    print("\nFiles by extension:")
    for extension, count in sorted(counts.items()):
        print(f"  {extension}: {count}")
    print("\nLargest files:")
    for path, size in sizes[: args.largest]:
        print(f"  {format_size(size)}  {path.relative_to(args.folder)}")
    if not sizes:
        print("  No files found.")
    return 0
