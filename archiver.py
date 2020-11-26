import re
import signal
from argparse import ArgumentParser
from multiprocessing import Pool
from pathlib import Path
from time import time
from typing import Callable, List, Iterable, Optional

from extractors import Extractor, FourChanAPIE, FourChanE
from models import boards, Params, Thread
from safe_requests_session import RetrySession
from utils import safely_create_dir


params = Params()


def parse_input():
    """Get user input from the command-line and parse it."""
    parser = ArgumentParser(description="Archives 4chan threads")
    parser.add_argument(
        "thread", help="Link to the 4chan thread or the name of the board."
    )
    parser.add_argument(
        "-p", "--preserve_files", help="Save images and video files locally.", action="store_true")
    parser.add_argument("--posts", type=int, default=None, help="Number of posts to download")
    parser.add_argument("-r", "--retries", type=int, default=1, help="Retry -r times if a download fails.")
    parser.add_argument("-v", "--verbose", help="Verbose logging to stdout.", action="store_true")
    parser.add_argument("--use_db", help="Stores threads into a database, this is experimental.", action="store_true")
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
        "--path",
        type=Path,
        default="./threads/",
        help="Path to folder where the threads should be saved.",
    )
    args = parser.parse_args()

    params.preserve = args.preserve_files
    params.total_retries = args.retries
    params.verbose = args.verbose
    params.total_posts = args.posts
    params.use_db = args.use_db
    params.path_to_download = args.path
    return args


def archive(thread_url):
    """
    Get values from the url to create a Thread object.
    Passes the thread to parse_html to be download.
    """
    match = None
    # check for valid urls in extractors
    # for cls in (FourChanAPIE, FourChanE):
    for cls in Extractor.__subclasses__():
        extractor = None
        if re.match(cls.VALID_URL, thread_url):
            match = re.match(cls.VALID_URL, thread_url)
            extractor = cls()

    if not(match):
        print("Improper URL:", thread_url)
        return 1

    board = match.group('board')
    thread_id = match.group('thread')
    thread = Thread(thread_id, board, thread_url)
    thread_folder = params.path_to_download.joinpath(
        thread.board, thread.tid
    )
    safely_create_dir(thread_folder)
    if params.verbose:
        print("Downloading thread:", thread.tid)
    extractor.extract(
        thread, params, thread_folder, params.use_db, params.verbose
    )


def feeder(url: str, args) -> Optional[List[str]]:
    """
    Check the type of input and create a list of urls
    which are then used to call archive().
    """
    thread_urls = []
    # list of thread urls
    if ".txt" in url:
        with open(url, "r") as f:
            thread_urls.extend(map(str.strip, f))
    # a board /name/ (only from 4chan)
    elif url in boards:
        if not args.archived_only:
            api_url = "https://a.4cdn.org/{}/threads.json".format(url)
            r = RetrySession().get(api_url)
            if r.status_code != 200:
                print("Invalid request:", url)
                exit(1)
            data = r.json()
            for page in data:
                for thread in page["threads"]:
                    thread_urls.append("https://boards.4chan.org/{}/thread/{}".format(url, thread["no"]))
            if args.verbose:
                print(f"Found {len(thread_urls)} active threads.")
        if args.archived or args.archived_only:
            api_url = "https://a.4cdn.org/{}/archive.json".format(url)
            r = RetrySession().get(api_url)
            if r.status_code != 200:
                print("Invalid request:", url)
                exit(1)
            data = r.json()
            if args.verbose:
                print(f"Found {len(data)} archived threads.")
            for thread_id in sorted(data):  # oldest threads first
                thread_urls.append(f"https://boards.4chan.org/{url}/thread/{thread_id}")
    # single thread url
    else:
        archive(url)
    if thread_urls:
        return thread_urls


def safe_parallel_run(func: Callable, iterable: Iterable):
    sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = Pool(processes=4)
    signal.signal(signal.SIGINT, sigint_handler)
    try:
        res = pool.map_async(func, iterable)
        res.get(86400)
    except KeyboardInterrupt:
        print("Terminating download")
        pool.terminate()
    else:
        pool.close()


def main():
    start_time = time()
    args = parse_input()
    thread_urls = feeder(args.thread, args)
    if thread_urls:
        safe_parallel_run(archive, thread_urls)
    print("Time elapsed: %.4fs" % (time() - start_time))


if __name__ == "__main__":
    main()
