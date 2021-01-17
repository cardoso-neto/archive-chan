import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable


def get_args():
    """Get user input from the command-line and parse it."""
    parser = ArgumentParser(
        description="Build a simple JSON index for the threads."
    )
    parser.add_argument(
        "--path",
        default="./threads/",
        type=Path,
        help="Path to folder where the threads are saved.",
    )
    parser.add_argument(
        "--output",
        default="./index.json",
        type=Path,
        help="Path to file where the index will be saved.",
    )
    args = parser.parse_args()
    return args


def find_all_thread_jsons(folder_path: Path) -> Iterable[Path]:
    return folder_path.rglob("*.json")


def load_json(json_path: Path) -> dict:
    with open(json_path) as file_handler:
        return json.load(file_handler)


def get_semantic_url(thread_json: dict) -> str:
    return thread_json["posts"][0]["semantic_url"]


def save_json(obj: dict, json_path: Path):
    with open(json_path, "w") as file_handler:
        return json.dump(obj, file_handler, indent=4, sort_keys=True)


def get_thread_id_from_json_path(json_path: Path) -> str:
    return f"{json_path.parent.parent.name}/{json_path.parent.name}"


def main():
    args = get_args()
    threads = list(find_all_thread_jsons(args.path))
    if not threads:
        print(f"No threads were found at {args.path!r}.")
        exit()
    else:
        print(f"{len(threads)} were found.")
    jsons = map(load_json, threads)
    semantic_urls = map(get_semantic_url, jsons)
    thread_ids = map(get_thread_id_from_json_path, threads)
    index = dict(zip(thread_ids, semantic_urls))
    save_json(index, args.output)
    print(f"Index saved to {args.output!r}.")


if __name__ == "__main__":
    main()
