# FileFlow

A simple command-line tool for downloading, organizing, analyzing, and cleaning
up files. Requires Python 3.11 or newer. Uses only the Python standard library;
no installation or external packages are needed.

Organization and renaming show a preview unless you add `--apply`. Deletion
requires `--delete` and typing `yes`. Deleted files do not go to the Recycle Bin.
Archives keep the original files.

## Quick start

Run commands from the project folder:

```powershell
python main.py --help
python main.py analyze "C:\Users\YourName\Downloads"
```

Use `python main.py COMMAND --help` to see a command's options.

## Project structure

```text
main.py                   Command-line arguments and command dispatch
features/
    __init__.py           Package marker
    common.py             Small shared helpers
    downloader.py         URL and batch downloads
    organizer.py          File organization
    analyzer.py           File counts and largest files
    unused.py             Inactive files, folders, and ZIP archives
    duplicates.py         Duplicate content detection
    empty.py              Zero-byte file detection
    renamer.py             Filename patterns
tests/
    test_fileflow.py       Behavior checks using temporary files
README.md
.gitignore
```

The program uses functions, loops, dictionaries, and `argparse`. Downloads use
`ThreadPoolExecutor` for a limited number of threads. No `asyncio` is used.

## Download files

```powershell
python main.py download "https://example.com/file.zip" --output downloads
python main.py download --from-file urls.txt --workers 3 --output downloads
```

Put one HTTP or HTTPS URL per line in `urls.txt`. Blank lines and lines starting
with `#` are ignored. You can combine individual URLs with `--from-file`.
At most `--workers` downloads run simultaneously; others wait in the thread
pool's queue. Existing filenames receive a numeric suffix instead of being
overwritten. Failed downloads are reported and partial files are removed.
Ctrl+C cancels queued downloads; transfers already running finish before exit.

## Organize a folder

```powershell
python main.py organize "C:\Users\YourName\Downloads"
python main.py organize "C:\Users\YourName\Downloads" --apply
```

Direct files are moved into `Images`, `Videos`, `Documents`, `Audio`, `Archives`,
or `Other`. Subfolders are left in place. Existing files are not overwritten.
You can provide a Desktop folder or any other folder in the same way.

## Analyze a folder

```powershell
python main.py analyze downloads --largest 10
```

Shows extension counts, total size, and the largest files, including files in
subfolders. Extension matching is case insensitive.

## Find inactive files and folders

```powershell
python main.py unused downloads --days 180
python main.py unused downloads --days 180 --archive backups\unused.zip
python main.py unused downloads --days 180 --delete
```

An item is inactive only when both its access and modification times are older
than the selected number of days. A folder is listed as a whole only when all
its contents are inactive; the selected root folder is never deleted. A folder
with active contents can still contain individually listed inactive files.

Access times depend on the filesystem and can be disabled or delayed, especially
on Windows. Review the results before deleting anything. Scanning directories
can itself update their access times.

ZIP archives must be saved outside the scanned folder. Existing archives are
not overwritten, and originals remain in place.

## Find duplicate files

```powershell
python main.py duplicates downloads
python main.py duplicates downloads --delete
```

Files are grouped by size and compared using SHA-256 content hashes, regardless
of their names. The first path in alphabetical order is kept in each group.
Contents are checked again before deleting an extra copy.

## Find empty files

```powershell
python main.py empty downloads
python main.py empty downloads --delete
```

Scans subfolders for zero-byte files. Empty directories are not deleted by this
command. A file is checked again before deletion to ensure it is still empty.

## Rename files

```powershell
python main.py rename pictures "img_{date}.jpeg"
python main.py rename pictures "photo_{counter}.png" --apply
python main.py rename documents "document_{date}_{counter}.pdf" --apply
python main.py rename downloads "{name}_{counter:03d}.{ext}" --start 10 --apply
```

Available variables: `{date}` (YYYY-MM-DD), `{counter}`, `{name}` (original name
without its extension), and `{ext}` (original extension without the dot).
Files are processed in alphabetical order. Patterns apply to direct files only.
Filename collisions receive suffixes such as ` (2)`. Invalid filenames and
unknown variables are rejected before any renaming starts.

## Run the checks

```powershell
python -B -m unittest discover -s tests -v
```

Checks use temporary folders and a local HTTP server, without touching personal
files or contacting external download sites.

Symbolic links are skipped during scans. Exit codes are `0` for success, `1` for
an operation error, `2` for invalid command arguments, and `130` for Ctrl+C.
