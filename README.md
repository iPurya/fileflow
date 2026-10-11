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

## Tests

```powershell
python -B -m unittest discover -s tests -v
```
