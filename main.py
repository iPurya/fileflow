"""FileFlow command-line interface."""

import argparse
import sys
from pathlib import Path
from features import analyzer


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
