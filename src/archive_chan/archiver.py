from multiprocessing import Pool
from pathlib import Path
from time import time
from typing import Callable, List, Optional, Sequence, TypeVar

from toolz import compose

from .extractors import Extractor, FourChanAPIE
from .models import boards
from .params import get_args

T = TypeVar("T")
U = TypeVar("U")
OptionalConcreteExtractor = Optional[FourChanAPIE]
path_to_download: Path = Path("/tmp/")


def choose_extractor(thread_url: str) -> OptionalConcreteExtractor:
    """Check for valid urls in Extractor subclasses."""
    thread = None
    extractor: OptionalConcreteExtractor = None
    for class_ in Extractor.__subclasses__():
        thread = class_.parse_thread_url(thread_url)
        if thread:
            extractor = class_(thread)
            # TODO: this path_to_download does not belong here
            break
    return extractor


def download_text_data(extractor: OptionalConcreteExtractor):
    if extractor is not None:
        try:
            extractor.download_thread_data()
        except RuntimeError as e:
            print(repr(e))


def download_media_files(extractor: OptionalConcreteExtractor):
    if extractor is not None:
        try:
            extractor.download_thread_media()
        except Exception as e:
            print(repr(e))


def render_threads(extractor: OptionalConcreteExtractor):
    if extractor is not None:
        try:
            extractor.render_thread()
        except Exception as e:
            raise e


def feeder(url: str, archived: bool, archived_only: bool, verbose: bool) -> List[str]:
    """Create and return a list of urls according to the input."""
    thread_urls = []
    # list of thread urls
    if ".txt" in url:
        with open(url, "r") as f:
            thread_urls.extend(map(str.strip, f))
    # a board /name/ (only from 4chan)
    elif url in boards:
        thread_urls = FourChanAPIE.get_threads_from_board(
            url, archived, archived_only, verbose
        )
    # single thread url
    else:
        return [url]
    return thread_urls


def safe_parallel_run(
    func: Callable[[T], U], sequence: Sequence[T], threads: int = 8
) -> Sequence[U]:
    if len(sequence) < threads:
        threads = len(sequence)
    with Pool(processes=threads) as pool:
        try:
            res = pool.map(func, sequence)
        except KeyboardInterrupt:
            print("Killing downloads...")
            pool.terminate()
            exit(1)
    return res


def main():
    start_time = time()
    args = get_args()
    global path_to_download
    path_to_download = args.path
    thread_urls = feeder(args.thread, args.archived, args.archived_only, args.verbose)
    if thread_urls:
        # download all jsons/htmls/text only
        safe_parallel_run(compose(download_text_data, choose_extractor), thread_urls)
        if not args.text_only:
            if args.preserve_media:
                # download all media
                safe_parallel_run(
                    compose(download_media_files, choose_extractor), thread_urls
                )
            else:
                # TODO: download op media only
                pass
        # TODO: parse posts' text
        if not args.skip_renders:
            safe_parallel_run(compose(render_threads, choose_extractor), thread_urls)
    print("Time elapsed: %.4fs" % (time() - start_time))
