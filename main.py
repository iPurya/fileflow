"""FileFlow command-line interface."""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="FileFlow", description="Manage files from the command line."
    )
    parser.add_argument("--version", action="version", version="FileFlow 0.1.0")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
