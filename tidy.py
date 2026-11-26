import argparse
import shutil
from collections import defaultdict
from pathlib import Path


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

    for name, extensions in CATEGORIES.items():
        if extension in extensions:
            return name

    return "Other"


def available_path(destination, reserved):
    candidate = destination
    extension = file_extension(destination)
    original_suffix = destination.name[-len(extension):] if extension else ""
    stem = destination.name[:-len(extension)] if extension else destination.name
    number = 1

    while candidate.exists() or candidate.is_symlink() or candidate in reserved:
        candidate = destination.with_name(f"{stem} ({number}){original_suffix}")
        number += 1

    reserved.add(candidate)
    return candidate


def format_size(size):
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"

        value /= 1024


def is_eligible(source, script):
    return source.is_file() and not source.is_symlink() and source.resolve() != script


def validate_destination(directory):
    if directory.is_symlink():
        raise ValueError("Destination is a symbolic link.")

    if directory.exists() and not directory.is_dir():
        raise ValueError("A file is blocking the destination folder.")


def build_plan(folder, selected_category=None):
    reserved = set()
    script = Path(__file__).resolve()
    plan = []
    skipped = []

    for source in sorted(folder.iterdir()):
        try:
            if not is_eligible(source, script):
                continue

            category = category_for(source)

            if selected_category and category != selected_category:
                continue

            directory = folder / category
            validate_destination(directory)

            size = source.stat().st_size
            target = available_path(directory / source.name, reserved)

            plan.append((source, target, category, size))

        except (OSError, ValueError) as error:
            skipped.append((source.name, str(error)))

    return plan, skipped


def calculate_statistics(plan):
    statistics = defaultdict(lambda: {"count": 0, "size": 0})

    for source, target, category, size in plan:
        statistics[category]["count"] += 1
        statistics[category]["size"] += size

    return statistics


def print_summary(plan):
    statistics = calculate_statistics(plan)
    total_size = sum(item[3] for item in plan)

    print("\nCATEGORY BREAKDOWN")
    print("-" * 45)

    for category, data in sorted(statistics.items()):
        count = data["count"]
        size = format_size(data["size"])

        print(f"{category:<18} {count:>5} file(s)  {size:>10}")

    print("-" * 45)
    print(f"Total files: {len(plan)}")
    print(f"Total size:  {format_size(total_size)}")

    if plan:
        largest = max(plan, key=lambda item: item[3])
        print(f"Largest file: {largest[0].name} ({format_size(largest[3])})")


def execute_move(source, target, reserved):
    validate_destination(target.parent)
    target.parent.mkdir(exist_ok=True)

    if target.exists() or target.is_symlink():
        target = available_path(target, reserved)

    shutil.move(str(source), str(target))
    return target


def organize(folder, apply=False, selected_category=None):
    folder = Path(folder).resolve()
    plan, skipped = build_plan(folder, selected_category)
    reserved = {item[1] for item in plan}

    completed = []

    print("\nAPPLY MODE" if apply else "\nPREVIEW MODE")
    print("-" * 45)

    for source, target, category, size in plan:
        try:
            if apply:
                target = execute_move(source, target, reserved)

            print(f"{source.name} -> {target.relative_to(folder)}")
            completed.append((source, target, category, size))

        except (OSError, ValueError, shutil.Error) as error:
            skipped.append((source.name, str(error)))

    print_summary(completed)

    if skipped:
        print("\nSKIPPED FILES")

        for name, reason in skipped:
            print(f"  {name}: {reason}")

    status = "organized" if apply else "previewed (nothing moved)"
    print(f"\n{len(completed)} file(s) {status}.")
    print(f"{len(skipped)} file(s) skipped.")


def main():
    parser = argparse.ArgumentParser(description="Sort files into folders by type.")

    parser.add_argument("folder", type=Path, help="Folder to organize")
    parser.add_argument("--apply", action="store_true", help="Actually move files")
    parser.add_argument("--category", choices=[*CATEGORIES, "Other"], help="Organize only the selected category")

    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error("The folder does not exist or is not a directory.")

    try:
        organize(args.folder.resolve(), args.apply, args.category)

    except OSError as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
