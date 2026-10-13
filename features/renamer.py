"""Rename files using dates, counters, and original filename parts."""

from datetime import datetime

from features.common import (
    check_inside,
    collect_files,
    is_link,
    unique_path,
    validate_filename,
)


def create_plan(folder, pattern, start=1):
    date = datetime.now().strftime("%Y-%m-%d")
    plan = []
    reserved = set()
    for counter, source in enumerate(collect_files(folder, recursive=False), start):
        try:
            name = pattern.format(
                date=date,
                counter=counter,
                name=source.stem,
                ext=source.suffix.lstrip("."),
            )
        except (KeyError, IndexError, AttributeError, ValueError) as error:
            raise ValueError(f"Invalid filename pattern: {error}") from error
        validate_filename(name)
        destination = folder / name
        if destination == source:
            reserved.add(destination)
            continue
        destination = unique_path(destination, reserved)
        reserved.add(destination)
        plan.append((source, destination))
    return plan


def run(args):
    plan = create_plan(args.folder, args.pattern, args.start)
    for source, destination in plan:
        print(f"{source.name} -> {destination.name}")
    if args.apply:
        for source, destination in plan:
            check_inside(source, args.folder)
            check_inside(destination, args.folder)
            if destination.exists() or is_link(destination):
                raise OSError(f"Destination changed: {destination}")
            source.rename(destination)
        print(f"Renamed {len(plan)} file(s).")
    else:
        print(f"Preview: {len(plan)} file(s). Use --apply to rename them.")
    return 0
