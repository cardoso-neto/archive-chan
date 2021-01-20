import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from flask import Flask, render_template

from ..models import Thread
from ..params import get_args
from ..safe_requests_session import RetrySession


class Extractor(ABC):
    VALID_URL = r""

    def __init__(self, thread: Thread):
        super().__init__()
        self.thread = thread

        args = get_args()
        self.archive_path = args.path
        self.verbose = args.verbose

        self.app = Flask("archive-chan", template_folder="./assets/templates/")
        # TODO: fix this relative path; what if user runs outside of repo root?
        # self.db = Database()  # I'll end up deprecating this?

    @classmethod
    def parse_thread_url(cls, thread_url: str) -> Optional[Thread]:
        match_ = re.match(cls.VALID_URL, thread_url)
        if not match_:
            return None
        board = match_.group("board")
        thread_id = match_.group("thread")
        # TODO: what about the chan name? e.g., 8ch, 55chan, 4channel
        thread = Thread(thread_id, board, thread_url)
        return thread

    def render_and_save_html(self, output_path: Path, **kwargs):
        with self.app.app_context():
            rendered = render_template("thread.html", **kwargs)
            with open(output_path, "w", encoding="utf-8") as html_file:
                html_file.write(rendered)

    def download_file(
        self,
        url: str,
        file_path: Path,
        verbose: bool = False,
        max_retries: int = 3,
        num_retry: int = 0,
        skip_check: bool = True,
    ):
        """
        Donwload file from `url` to `file_path`.

        If it fails, retry until total retries reached.
        """
        requests_session = RetrySession()
        try:
            if not skip_check and file_path.is_file():
                response = requests_session.head(url, timeout=8)
                size_on_the_server = response.headers.get("content-length", 0)
                if file_path.stat().st_size == size_on_the_server:
                    return
            if verbose:
                print("Downloading image:", url, file_path.name)
            response = requests_session.get(url, timeout=16)
            with open(file_path, "wb") as output:
                output.write(response.content)
        except Exception as e:
            if max_retries > num_retry:
                print(e, file=sys.stderr)
                print(f"Retry #{num_retry}...")
                num_retry += 1
                self.download_file(url, file_path, verbose, max_retries, num_retry)

    @abstractmethod
    def download_thread_data():
        pass

    @abstractmethod
    def download_thread_media():
        pass

    @abstractmethod
    def render_thread():
        pass
