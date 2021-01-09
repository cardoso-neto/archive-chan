from multiprocessing import Pool
from time import time
from typing import Callable, List, Iterable, Optional, TypeVar

from toolz import compose

from extractors import Extractor, FourChanAPIE
from models import boards, Params
from params import get_args
from utils import safely_create_dir


T = TypeVar("T")
U = TypeVar("U")
OptionalConcreteExtractor = Optional[FourChanAPIE]
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
    """Check for valid urls in Extractor subclasses."""
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
        return


def download_media_files(
    extractor: OptionalConcreteExtractor
) -> OptionalConcreteExtractor:
    if extractor is not None:
        try:
            extractor.download_thread_media()
        except Exception as e:
            print(repr(e))
        return extractor


def render_threads(
    extractor: OptionalConcreteExtractor
) -> OptionalConcreteExtractor:
    if extractor is not None:
        try:
            extractor.render_thread()
        except Exception as e:
            raise e
        return extractor

def archive(thread_url: str):
    extractor = choose_extractor(thread_url)
    if not extractor:
        print("Improper URL:", thread_url)
        return 1
    thread = extractor.thread
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
) -> List[str]:
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
        return [url]
    return thread_urls


def safe_parallel_run(
    func: Callable[[T], U], iterable: Iterable[T], threads: int = 4
) -> Iterable[U]:
    with Pool(processes=threads) as pool:
        try:
            res = pool.map(func, iterable)
        except KeyboardInterrupt:
            print("Killing downloads...")
            pool.terminate()
            exit(1)
    return res


def main():
    start_time = time()
    args = parse_input()
    thread_urls = feeder(
        args.thread, args.archived, args.archived_only, args.verbose
    )
    if thread_urls:
        # download all jsons/htmls/text only
        safe_parallel_run(compose(download_text_data, choose_extractor), thread_urls)
        if not args.text_only:
            # TODO: download op media only
            pass
        if args.preserve_media:
            # download all media
            safe_parallel_run(compose(download_media_files, choose_extractor), thread_urls)
        # TODO: parse posts' text
        if not args.skip_renders:
            safe_parallel_run(compose(render_threads, choose_extractor), thread_urls)
    print("Time elapsed: %.4fs" % (time() - start_time))


if __name__ == "__main__":
    main()
