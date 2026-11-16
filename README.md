# TidyTrail 📁

A tiny Python script that sorts files into folders by type: **Images**, **Documents**, **Videos**, **Audio**, **Code**, **Archives**, and **Other**.

## Features
- Preview moves before making changes
- Keep existing files safe by renaming duplicates (`photo (1).jpg`)
- Organize only the files directly inside the chosen folder
- No dependencies — just Python 3.9+

## Usage

1. Open a terminal in the folder containing `tidy.py`.
2. Preview what would happen:

```bash
python tidy.py "C:\Users\YourName\Downloads"
```

3. Actually organize files:

```bash
python tidy.py "C:\Users\YourName\Downloads" --apply
```

On macOS/Linux, replace the folder path with something like `~/Downloads`.

**Note:** Files are moved, not copied. The tool does not provide an undo command, so preview first.

## Example

Before:
```text
Downloads/
  cat.jpg
  notes.pdf
  song.mp3
```

After:
```text
Downloads/
  Images/cat.jpg
  Documents/notes.pdf
  Audio/song.mp3
```

