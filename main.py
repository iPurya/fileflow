"""Command-line interface for automation tasks."""

import argparse
import sys

from tasks import TASKS


def main(argv: list[str] | None = None) -> int:
    """Read a command, execute it, and return an exit code."""
    parser = argparse.ArgumentParser(description="Run Python automation tasks.")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List available tasks")

    run_parser = commands.add_parser("run", help="Run an automation task")
    run_parser.add_argument("task", choices=sorted(TASKS), help="Task to run")
    
    args = parser.parse_args(argv)

    if args.command == "list":
        for name in sorted(TASKS):
            print(name)
        return 0

    try:
        if args.dry_run:
            print(f"Would run: {args.task}")
        else:
            print(TASKS[args.task]())
        return 0
    except OSError as error:
        print(f"{parser.prog}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"{parser.prog}: cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
