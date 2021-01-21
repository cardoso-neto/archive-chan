from archive_chan.extractors import FourChanAPIE


def test_url_parser():
    thread_id = "214860910"
    thread_board = "a"
    thread_url_4chan = "https://boards.4channel.org/a/thread/{}/boku-no-hero-academia"
    thread_url_4chan = thread_url_4chan.format(thread_id)
    thread = FourChanAPIE.parse_thread_url(thread_url_4chan)
    assert thread_id == thread.tid
    assert thread_board == thread.board
    assert thread_url_4chan == thread.url
