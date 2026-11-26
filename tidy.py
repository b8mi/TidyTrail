import argparse
import shutil
from pathlib import Path

CATEGORIES = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"},
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"},
    "Videos": {".mp4", ".mov", ".mkv", ".avi"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a"},
    "Code": {".py", ".js", ".html", ".css", ".java", ".cpp", ".json"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
}


def category_for(file):
    return next((name for name, extensions in CATEGORIES.items()
                 if file.suffix.lower() in extensions), "Other")


def available_path(destination, reserved):
    candidate = destination
    number = 1
    while candidate.exists() or candidate in reserved:
        candidate = destination.with_name(
            f"{destination.stem} ({number}){destination.suffix}"
        )
        number += 1
    reserved.add(candidate)
    return candidate


def organize(folder, apply=False):
    reserved = set()
    count = 0
    script = Path(__file__).resolve()
    for source in sorted(folder.iterdir()):
        if not source.is_file() or source.is_symlink() or source.resolve() == script:
            continue
        target = available_path(folder / category_for(source) / source.name, reserved)
        print(f"{source.name} -> {target.relative_to(folder)}")
        if apply:
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(source), str(target))
        count += 1
    print(f"\n{count} file(s) {'organized' if apply else 'previewed (nothing moved)' }.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort files into folders by type.")
    parser.add_argument("folder", type=Path, help="Folder to organize")
    parser.add_argument("--apply", action="store_true", help="Actually move files")
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error("The folder does not exist or is not a directory.")
    organize(args.folder.resolve(), args.apply)
