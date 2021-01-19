
from archive_chan import archiver
from archive_chan import extractors
from archive_chan import models


def test_url_parser():
    thread_id = "214860910"
    thread_board = "a"
    thread_url_4chan = "https://boards.4channel.org/a/thread/214860910/boku-no-hero-academia"
    thread = extractors.FourChanAPIE.parse_thread_url(thread_url_4chan)
    assert thread_id == thread.tid
    assert thread_board == thread.board
    assert thread_url_4chan == thread.url
