from argparse import ArgumentParser
from pathlib import Path


def get_args():
    parser = ArgumentParser(description="Archives 4chan threads")
    parser.add_argument(
        "thread", help="Link to the 4chan thread or the name of the board."
    )
    parser.add_argument(
        "-a",
        "--archived",
        action="store_true",
        help="Download threads from the /board/archive/ as well.",
    )
    parser.add_argument(
        "-ao",
        "--archived_only",
        action="store_true",
        help="Download threads from the /board/archive/ INSTEAD.",
    )
    parser.add_argument(
        "-p",
        "--preserve_media",
        action="store_true",
        help="Save images and video files locally.",
    )
    parser.add_argument(
        "--path",
        default="./threads/",
        help="Path to folder where the threads should be saved.",
        type=Path,
    )
    parser.add_argument(
        "--posts",
        default=None,
        help="Number of posts to download",
        type=int,
    )
    parser.add_argument(
        "-r",
        "--retries",
        default=1,
        help="Retry -r times if a download fails.",
        type=int,
    )
    parser.add_argument(
        "--text_only",
        action="store_true",
        help="Download only HTMLs or JSONs.",
    )
    parser.add_argument(
        "--use_db",
        action="store_true",
        help="Stores threads into a database, this is experimental.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging to stdout.",
    )
    parser.add_argument(
        "--new_logic",
        action="store_true",
        help="2.0 development switch"
    )
    args = parser.parse_args()
    return args
