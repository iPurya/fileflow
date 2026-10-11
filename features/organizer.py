"""Sort files into folders based on their extensions."""

import shutil

from features.common import check_inside, collect_files, is_link, unique_path

CATEGORIES = {
    "Images": {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".tiff",
        ".heic",
    },
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"},
    "Documents": {
        ".pdf",
        ".txt",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
        ".md",
        ".rtf",
        ".odt",
        ".epub",
    },
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
}


def create_plan(folder):
    plan = []
    for source in collect_files(folder, recursive=False):
        category = "Other"
        for name, extensions in CATEGORIES.items():
            if source.suffix.lower() in extensions:
                category = name
                break
        target_folder = folder / category
        if is_link(target_folder):
            raise ValueError(f"Category folder is a symbolic link: {target_folder}")
        if target_folder.exists() and not target_folder.is_dir():
            raise ValueError(f"Category name is occupied by a file: {target_folder}")
        plan.append((source, unique_path(target_folder / source.name)))
    return plan


def run(args):
    plan = create_plan(args.folder)
    for source, destination in plan:
        print(f"{source.name} -> {destination.relative_to(args.folder)}")
    if args.apply:
        for source, destination in plan:
            check_inside(source, args.folder)
            destination.parent.mkdir(exist_ok=True)
            check_inside(destination, args.folder)
            if destination.exists() or is_link(destination.parent):
                raise OSError(f"Destination changed: {destination}")
            shutil.move(str(source), str(destination))
        print(f"Organized {len(plan)} file(s).")
    else:
        print(f"Preview: {len(plan)} file(s). Use --apply to move them.")
    return 0
