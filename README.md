 
# TidyTrail

A tiny Python script that sorts files into folders based on their type: **Images**, **Documents**, **Videos**, **Audio**, **Code**, **Archives**, and **Other**.

## Features
- Preview where files will go before making any changes
- Keep existing files safe by renaming duplicates (`photo (1).jpg`)
- Only organize files directly inside the folder you choose
- No external libraries needed, just Python 3.9+

## Usage

1. Open a terminal in the folder containing `tidy.py`.
2. Preview what the script will do:

```bash
python tidy.py "C:\Users\YourName\Downloads"
```

3. To actually organize the files, run:

```bash
python tidy.py "C:\Users\YourName\Downloads" --apply
```

On macOS/Linux, replace the folder path with something like `~/Downloads`.

**Note:** Files are moved, not copied. There is no undo command, so make sure to preview the changes first.

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
