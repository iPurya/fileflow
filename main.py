"""FileFlow command-line interface."""

import argparse
import sys
from pathlib import Path

from features import analyzer, downloader, duplicates, empty, organizer, renamer, unused


def positive_number(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Use a number greater than zero")
    return number


def existing_folder(value):
    folder = Path(value).expanduser().resolve()
    if not folder.is_dir():
        raise argparse.ArgumentTypeError(f"Folder does not exist: {value}")
    return folder


def build_parser():
    parser = argparse.ArgumentParser(
        prog="FileFlow", description="Download, organize, analyze, and clean up files."
    )
    parser.add_argument("--version", action="version", version="FileFlow 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)

    # File downloader
    command = commands.add_parser("download", help="Download URLs or a URL list")
    command.add_argument("urls", nargs="*", help="HTTP or HTTPS URLs")
    command.add_argument(
        "--from-file", type=Path, help="Text file with one URL per line"
    )
    command.add_argument(
        "--output", type=Path, default=Path("downloads"), help="Destination folder"
    )
    command.add_argument(
        "--workers",
        type=positive_number,
        default=3,
        help="Maximum simultaneous downloads",
    )
    command.set_defaults(handler=downloader.run)

    # File organizer
    command = commands.add_parser("organize", help="Sort files into category folders")
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "--apply", action="store_true", help="Move files instead of only previewing"
    )
    command.set_defaults(handler=organizer.run)

    # Folder analyzer
    command = commands.add_parser(
        "analyze", help="Count file types and show largest files"
    )
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "--largest",
        type=positive_number,
        default=5,
        help="Number of largest files to display",
    )
    command.set_defaults(handler=analyzer.run)

    # Unused files and folders
    command = commands.add_parser("unused", help="Find inactive files and folders")
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "--days", type=positive_number, default=180, help="Minimum inactive days"
    )
    action = command.add_mutually_exclusive_group()
    action.add_argument(
        "--archive", type=Path, help="Create a ZIP outside the scanned folder"
    )
    action.add_argument(
        "--delete", action="store_true", help="Delete found items after confirmation"
    )
    command.set_defaults(handler=unused.run)

    # Duplicate files
    command = commands.add_parser(
        "duplicates", help="Find files with identical content"
    )
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "--delete",
        action="store_true",
        help="Keep one copy and confirm deletion of the rest",
    )
    command.set_defaults(handler=duplicates.run)

    # Empty files
    command = commands.add_parser("empty", help="Find zero-byte files")
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "--delete", action="store_true", help="Delete empty files after confirmation"
    )
    command.set_defaults(handler=empty.run)

    # Batch renamer
    command = commands.add_parser(
        "rename", help="Rename files using a filename pattern"
    )
    command.add_argument("folder", type=existing_folder)
    command.add_argument(
        "pattern", help="Pattern with {date}, {counter}, {name}, or {ext}"
    )
    command.add_argument(
        "--start", type=positive_number, default=1, help="First counter value"
    )
    command.add_argument(
        "--apply", action="store_true", help="Rename files instead of only previewing"
    )
    command.set_defaults(handler=renamer.run)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
