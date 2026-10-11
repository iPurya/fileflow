# FileFlow

A small Python CLI for file management. Python 3.11 or newer is required.
No external packages are needed.

```powershell
python main.py --help
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
