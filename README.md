# FileFlow

A small Python CLI for file management. Python 3.11 or newer is required.
No external packages are needed.

```powershell
python main.py --help
```

## Download

```powershell
python main.py download "https://example.com/file.zip" --output downloads
python main.py download --from-file urls.txt --workers 3
```

## Organize

```powershell
python main.py organize downloads
python main.py organize downloads --apply
```

## Analyze

```powershell
python main.py analyze downloads --largest 5
```

## Unused

```powershell
python main.py unused downloads --days 180
python main.py unused downloads --archive backups\unused.zip
```

## Duplicates

```powershell
python main.py duplicates downloads
python main.py duplicates downloads --delete
```

## Empty

```powershell
python main.py empty downloads
python main.py empty downloads --delete
```

## Tests

```powershell
python -B -m unittest discover -s tests -v
```

Deletion requires typing yes. Deleted files do not go to the Recycle Bin.
