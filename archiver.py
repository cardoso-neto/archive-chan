import signal
from multiprocessing import Pool
from time import time
from typing import Callable, List, Iterable, Optional, Tuple, Union

from extractors import Extractor, FourChanAPIE, FourChanE
from models import boards, Params, Thread
from params import get_args
from utils import safely_create_dir


OptionalConcreteExtractor = Optional[Union[FourChanAPIE, FourChanE]]
params = Params()


def parse_input():
    """Get user input from the command-line and parse it."""
    args = get_args()

    params.preserve = args.preserve_media
    params.total_retries = args.retries
    params.verbose = args.verbose
    params.total_posts = args.posts
    params.use_db = args.use_db
    params.path_to_download = args.path
    return args


def choose_extractor(thread_url: str) -> OptionalConcreteExtractor:
    """
    Check for valid urls in Extractor subclasses.
    """
    thread = None
    extractor: OptionalConcreteExtractor = None
    for class_ in Extractor.__subclasses__():
        thread = class_.parse_thread_url(thread_url)
        if thread:
            extractor = class_(thread, params.path_to_download)
            # TODO: this params.path_to_download does not belong here
            break
    return extractor


def download_text_data(
    extractor: OptionalConcreteExtractor
) -> OptionalConcreteExtractor:
    if extractor is not None:
        try:
            extractor.download_thread_data()
        except RuntimeError as e:
            print(repr(e))
            return None
        return extractor


def download_media_files(
    extractor: OptionalConcreteExtractor
) -> OptionalConcreteExtractor:
    if extractor is not None:
        try:
            extractor.download_thread_media()
        except Exception as e:
            raise e
        return extractor


def archive(thread_url: str):
    extractor = choose_extractor(thread_url)
    thread = extractor.thread
    if not extractor:
        print("Improper URL:", thread_url)
        return 1
    thread_folder = params.path_to_download.joinpath(
        thread.board, thread.tid
    )
    safely_create_dir(thread_folder)
    if params.verbose:
        print("Downloading thread:", thread.tid)
    extractor.extract(
        thread, params, thread_folder, params.use_db, params.verbose
    )


def feeder(
    url: str, archived: bool, archived_only: bool, verbose: bool
) -> Union[str, List[str]]:
    """Create and return a list of urls according to the input."""
    thread_urls = []
    # list of thread urls
    if ".txt" in url:
        with open(url, "r") as f:
            thread_urls.extend(map(str.strip, f))
    # a board /name/ (only from 4chan)
    elif url in boards:
        FourChanAPIE.get_threads_from_board(
            url, archived, archived_only, verbose
        )
    # single thread url
    else:
        return url
    return thread_urls


def safe_parallel_run(func: Callable, iterable: Iterable) -> Iterable:
    sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = Pool(processes=4)
    signal.signal(signal.SIGINT, sigint_handler)
    res = []
    try:
        res = pool.map_async(func, iterable)
        res.get(86400)
    except KeyboardInterrupt:
        print("Terminating download")
        pool.terminate()
    finally:
        pool.close()
        return res


def main():
    start_time = time()
    args = parse_input()
    thread_urls = feeder(
        args.thread, args.archived, args.archived_only, args.verbose
    )
    if isinstance(thread_urls, str):
        thread_urls = [thread_urls]
    if isinstance(thread_urls, list) and len(thread_urls):
        if args.new_logic:
            # choose extractors
            jobs: Iterable[OptionalConcreteExtractor]
            jobs = [choose_extractor(x) for x in thread_urls]
            # download all jsons/htmls/text only
            jobs = [download_text_data(x) for x in jobs]
            if not args.text_only:
                # download op media only
                pass  # TODO
            if args.preserve_media:
                # download all media
                jobs = [download_media_files(x) for x in jobs]
            # parse posts' text
            # render all threads
        else:
            safe_parallel_run(archive, thread_urls)
    # elif isinstance(thread_urls, str):  # single thread mode
    #     archive(thread_urls)
    print("Time elapsed: %.4fs" % (time() - start_time))


if __name__ == "__main__":
    main()
