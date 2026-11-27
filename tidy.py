
import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

HISTORY_FILE = ".tidytrail-undo.json"

CATEGORIES = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".heic"},
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv", ".rtf", ".odt", ".md"},
    "Videos": {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"},
    "Code": {".py", ".js", ".html", ".css", ".java", ".cpp", ".json", ".c", ".cs", ".ts", ".xml", ".sql"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".tar.gz", ".tar.bz2", ".tar.xz"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
    "Executables": {".exe", ".msi", ".apk", ".appimage"},
    "3D Models": {".obj", ".fbx", ".stl", ".blend", ".gltf", ".glb"}
}


def file_extension(file):
    name = file.name.lower()

    for extension in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if name.endswith(extension):
            return extension

    return file.suffix.lower()


def category_for(file):
    extension = file_extension(file)

    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category

    return "Other"


def occupied(path):
    return path.exists() or path.is_symlink()


def available_path(destination, reserved):
    extension = file_extension(destination)
    suffix = destination.name[-len(extension):] if extension else ""
    stem = destination.name[:-len(extension)] if extension else destination.name

    candidate = destination
    number = 1

    while occupied(candidate) or candidate in reserved:
        candidate = destination.with_name(f"{stem} ({number}){suffix}")
        number += 1

    reserved.add(candidate)
    return candidate


def format_size(size):
    value = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024 or unit == "PB":
            return f"{value:.2f} {unit}"
        value /= 1024


def validate_directory(directory):
    if directory.is_symlink():
        raise ValueError("Symbolic link destination.")

    if directory.exists() and not directory.is_dir():
        raise ValueError("Destination is not a directory.")


def is_eligible(source):
    if source.name in (HISTORY_FILE, HISTORY_FILE + ".tmp"):
        return False

    return (
        source.is_file()
        and not source.is_symlink()
        and source.resolve() != Path(__file__).resolve()
    )


def build_plan(folder, selected_category=None):
    reserved = set()
    plan = []
    skipped = []

    for source in sorted(folder.iterdir()):
        try:
            if not is_eligible(source):
                continue

            category = category_for(source)

            if selected_category and category != selected_category:
                continue

            directory = folder / category
            validate_directory(directory)

            target = available_path(directory / source.name, reserved)
            plan.append((source, target, category, source.stat().st_size))

        except (OSError, ValueError) as error:
            skipped.append((source.name, str(error)))

    return plan, skipped


def print_summary(plan):
    statistics = defaultdict(lambda: {"count": 0, "size": 0})

    for source, target, category, size in plan:
        statistics[category]["count"] += 1
        statistics[category]["size"] += size

    print("\nCATEGORY BREAKDOWN")
    print("-" * 50)

    for category, data in sorted(statistics.items()):
        print(f"{category:<18} {data['count']:>5} files  {format_size(data['size']):>10}")

    print("-" * 50)
    print(f"Total files: {len(plan)}")
    print(f"Total size: {format_size(sum(item[3] for item in plan))}")

    if plan:
        largest = max(plan, key=lambda item: item[3])
        print(f"Largest file: {largest[0].name} ({format_size(largest[3])})")


def save_history(folder, records):
    history = folder / HISTORY_FILE
    temporary = folder / (HISTORY_FILE + ".tmp")

    if history.is_symlink() or occupied(temporary):
        raise ValueError("Unsafe history file location.")

    try:
        with temporary.open("x", encoding="utf-8") as file:
            json.dump(records, file, indent=2)

        temporary.replace(history)

    finally:
        if temporary.is_file() and not temporary.is_symlink():
            temporary.unlink(missing_ok=True)


def load_history(folder):
    history = folder / HISTORY_FILE

    if history.is_symlink():
        raise ValueError("Unsafe history file.")

    if not history.exists():
        return []

    records = json.loads(history.read_text(encoding="utf-8"))

    if not isinstance(records, list):
        raise ValueError("Invalid undo history.")

    return records


def signature(path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns]


def create_record(folder, source, target):
    return {
        "original": str(source.relative_to(folder)),
        "organized": str(target.relative_to(folder)),
        "signature": signature(source)
    }


def record_paths(folder, record):
    original = Path(record["original"])
    organized = Path(record["organized"])

    if original.is_absolute() or organized.is_absolute():
        raise ValueError("Invalid recorded path.")

    if len(original.parts) != 1 or len(organized.parts) != 2:
        raise ValueError("Invalid recorded location.")

    if ".." in original.parts or ".." in organized.parts:
        raise ValueError("Unsafe recorded path.")

    if organized.parts[0] not in [*CATEGORIES, "Other"]:
        raise ValueError("Unknown category.")

    source = folder / organized
    target = folder / original

    validate_directory(source.parent)

    if source.is_symlink() or target.is_symlink():
        raise ValueError("Symbolic links are not supported.")

    return source, target


def organize(folder, apply=False, selected_category=None):
    folder = Path(folder).resolve()
    plan, skipped = build_plan(folder, selected_category)

    reserved = {item[1] for item in plan}
    completed = []
    records = []

    print("\nAPPLY MODE" if apply else "\nPREVIEW MODE")
    print("-" * 50)

    if apply and plan and load_history(folder):
        print("Warning: this operation replaces the previous undo history.")

        if input("Continue? [y/N]: ").strip().lower() not in ("y", "yes"):
            return

    for source, target, category, size in plan:
        try:
            if apply:
                validate_directory(target.parent)
                target.parent.mkdir(exist_ok=True)

                if occupied(target):
                    target = available_path(target, reserved)

                record = create_record(folder, source, target)

                # Record the intended move before changing the files.
                save_history(folder, records + [record])

                try:
                    shutil.move(str(source), str(target))
                except (OSError, shutil.Error):
                    # Keep the record for recovery if the move was partial.
                    raise

                records.append(record)

            completed.append((source, target, category, size))
            print(f"{source.name} -> {target.relative_to(folder)}")

        except (OSError, ValueError, shutil.Error) as error:
            skipped.append((source.name, str(error)))

            if apply:
                print("Stopped to preserve the undo history.")
                break

    print_summary(completed)

    for name, reason in skipped:
        print(f"Skipped {name}: {reason}")

    if apply:
        print(f"\n{len(completed)} file(s) organized.")

        if records:
            print('Restore using: python tidy.py "FOLDER" --undo')
    else:
        print("\nPreview finished. No files were moved.")


def undo(folder):
    folder = Path(folder).resolve()
    records = load_history(folder)

    if not records:
        print("No previous organization found.")
        return

    restored = 0
    remaining = records.copy()

    for index in range(len(records) - 1, -1, -1):
        record = records[index]

        try:
            source, target = record_paths(folder, record)

            if not occupied(source) and target.is_file():
                # Already restored, or the original move never finished.
                if signature(target) != record["signature"]:
                    raise ValueError("Original file has changed.")

            else:
                if not source.is_file():
                    raise ValueError("Organized file is missing.")

                if occupied(target):
                    raise ValueError("Original location is occupied.")

                if signature(source) != record["signature"]:
                    raise ValueError("Organized file has changed.")

                shutil.move(str(source), str(target))
                restored += 1

            remaining.pop(index)
            save_history(folder, remaining)

            print(f"Restored: {target.name}")

        except (OSError, ValueError, KeyError, TypeError, shutil.Error) as error:
            print(f"Skipped undo entry: {error}")

    print(f"\n{restored} file(s) restored.")
    print(f"{len(remaining)} unresolved undo entries.")

    if not remaining:
        print("Undo completed.")


def main():
    parser = argparse.ArgumentParser(description="Organize files by type.")
    parser.add_argument("folder", type=Path)

    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--undo", action="store_true")

    parser.add_argument("--category", choices=[*CATEGORIES, "Other"])

    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error("Folder does not exist.")

    if args.undo and args.category:
        parser.error("--category cannot be combined with --undo.")

    try:
        if args.undo:
            undo(args.folder)
        else:
            organize(args.folder, args.apply, args.category)

    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
