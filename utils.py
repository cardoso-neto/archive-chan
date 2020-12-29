from pathlib import Path


def safely_create_dir(dir_path: Path):
    if not dir_path.is_dir():
        dir_path.mkdir(parents=True, exist_ok=True)


def count_files_in_dir(
    dir_path: Path, files_only: bool = True, recursive: bool = False
) -> int:
    if not dir_path.is_dir():
        raise ValueError
    if not files_only and not recursive:
        return sum(1 for _ in dir_path.iterdir())
    elif not files_only and recursive:
        return sum(1 for _ in dir_path.glob('**/*'))
    elif files_only and not recursive:
        return sum(1 for item in dir_path.iterdir() if item.is_file())
    else:  # files_only and recursive:
        return sum(1 for x in dir_path.glob('**/*') if x.is_file())
