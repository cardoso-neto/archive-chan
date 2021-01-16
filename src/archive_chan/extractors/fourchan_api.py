
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from flask import Flask, render_template
from superjson import json

from .extractor import Extractor
from ..models import Reply, Thread
from ..resources.database.db_interface import Database
from ..safe_requests_session import RetrySession
from ..utils import count_files_in_dir, safely_create_dir


@dataclass
class MediaInfo:
    tim: str
    ext: str
    md5: str

    def __post_init__(self):
        self.filename = f"{self.tim}{self.ext}"


class FourChanAPIE(Extractor):
    VALID_URL = r'https?://boards.(4channel|4chan).org/(?P<board>[\w-]+)/thread/(?P<thread>[0-9]+)'
    base_thread_url = "https://boards.4chan.org/{board}/thread/{thread_id}"
    base_media_url = "https://i.4cdn.org/{}/{}"

    def __init__(
        self, thread: Thread, archive_path: Path, verbose: bool = True
    ):
        super().__init__()
        self.thread = thread
        self.archive_path = archive_path
        self.verbose = verbose
        self.app = Flask('archive-chan', template_folder='./assets/templates/')
        self._thread_data: Optional[dict] = None
        # self.db = Database()  # I'll end up deprecating this

    @property
    def thread_data(self) -> Optional[dict]:
        if self._thread_data is None:
            self._thread_data = self._load_previous_thread_data()
        return self._thread_data

    @property
    def thread_folder(self) -> Path:
        return self.archive_path.joinpath(self.thread.board, self.thread.tid)

    @property
    def thread_media_folder(self) -> Path:
        path = self.thread_folder / "media"
        safely_create_dir(path)
        return path

    @property
    def json_path(self) -> Path:
        return self.thread_folder / "thread.json"

    @property
    def html_page_path(self) -> Path:
        return self.thread_folder / "index.html"

    @staticmethod
    def get_thread_data(board: str, thread_id: str) -> Optional[dict]:
        r = RetrySession().get(
            f"https://a.4cdn.org/{board}/thread/{thread_id}.json", timeout=16
        )
        if r.status_code == 404:
            return None
        if r.status_code != requests.codes.ok:
            print(f"Skip {thread_id} due to error {r.status_code}.")
            msg = f"Thread {thread_id}: error {r.status_code}."
            raise requests.exceptions.RequestException(msg)
        return r.json()

    def _load_previous_thread_data(self) -> Optional[dict]:
        if not self.json_path.is_file():
            return None
        return json.load(str(self.json_path), verbose=self.verbose)

    def _has_new_replies(self, previous_thread_data, current_thread_data):
        if previous_thread_data is not None:
            if (
                previous_thread_data["posts"][0]["replies"]
                == current_thread_data["posts"][0]["replies"]
            ):
                if self.verbose:
                    print("No new replies.")
                return False
        return True

    # TODO: decorator @false_on_key_error
    def _was_thread_archived(self) -> bool:
        try:
            return self.thread_data["posts"][0]["archived"]
        except KeyError:
            return False

    def _was_thread_404(self) -> bool:
        try:
            return self.thread_data["archive-chan"]["404"]
        except KeyError:
            return False

    def _dump_thread_json(self, thread_data):
        json.dump(
            thread_data,
            str(self.json_path),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            overwrite=True,
            verbose=self.verbose,
        )

    def _mark_thread_as_404(self):
        if "archive-chan" not in self.thread_data:
            self.thread_data["archive-chan"] = {"404": True}
        else:
            self.thread_data["archive-chan"].update({"404": True})
        self._dump_thread_json(self.thread_data)

    def download_thread_data(self):
        safely_create_dir(self.thread_folder)
        if self.thread_data is not None:
            if self._was_thread_archived() or self._was_thread_404():
                if self.verbose:
                    print("Nothing new will ever be available again.")
                return
        try:
            self.current_thread_data = self.get_thread_data(
                self.thread.board, self.thread.tid
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(repr(e))
        if self.current_thread_data is None:
            if self.thread_data is None:
                # R.I.P.
                raise RuntimeError("Thread 79244239 is 404. :(")
            else:
                self._mark_thread_as_404()
        elif self._has_new_replies(self.thread_data, self.current_thread_data):
            self._dump_thread_json(self.current_thread_data)


    @staticmethod
    def get_media_info(posts: List[dict]) -> List[MediaInfo]:
        # TODO: type thread_data JSON correctly
        media_info_objs = [
            MediaInfo(post["tim"], post["ext"], post["md5"])
            for post in posts
            if "tim" in post
        ]
        return media_info_objs

    @staticmethod
    def calculate_md5(file_path: Path, temp_folder: Path = None) -> str:
        if temp_folder is None:
            temp_folder = file_path.parent
        file_md5_path = temp_folder.joinpath(f"{file_path.stem}.md5")
        command = f"openssl md5 -binary {str(file_path)}"
        command += " | openssl base64"
        command += f" > {str(file_md5_path)}"
        os.system(command)
        with open(file_md5_path) as file_md5_file_handler:
            calculated_md5_digest = file_md5_file_handler.read()
        file_md5_path.unlink()
        return calculated_md5_digest.rstrip("\n")

    def _is_media_ok(self) -> bool:
        try:
            if self.thread_data["archive-chan"]["media-ok"]:
                return True
        except KeyError:
            pass
        return False

    def _are_there_undownloaded_media_files(self) -> bool:
        """
        Check if media is fully and correctly downloaded.
        """
        downloaded_media_count = count_files_in_dir(self.thread_media_folder)
        total_media_count = self.thread_data["posts"][0]["images"] + 1
        # + 1 because of the OP image
        return downloaded_media_count != total_media_count

    def _get_hash_mismatches(self) -> List[MediaInfo]:
        media_info_objs = self.get_media_info(self.thread_data["posts"])
        mismatched_hash_files = [
            media_file
            for media_file in media_info_objs
            if media_file.md5 != self.calculate_md5(
                self.thread_media_folder / media_file.filename
            )
        ]
        return mismatched_hash_files

    def _mark_thread_media_as_done(self):
        if "archive-chan" not in self.thread_data:
            self.thread_data["archive-chan"] = {"media-done": True}
        else:
            self.thread_data["archive-chan"].update({"media-done": True})
        self._dump_thread_json(self.thread_data)

    def _get_undownloaded_files(self) -> List[str]:
        downloaded_files = {
            f.name for f in self.thread_media_folder.glob("*")
        }
        media_info_objs = self.get_media_info(self.thread_data["posts"])
        all_files = [m.filename for m in media_info_objs]
        undownloaded_files = [
            f for f in all_files if f not in downloaded_files
        ]
        return undownloaded_files

    def download_thread_media(self, max_retries: int = 3):
        """
        This should only be called after thread_data has been downloaded.
        """
        if self._is_media_ok():
            return
        if self._are_there_undownloaded_media_files():
            undownloaded_files = self._get_undownloaded_files()
            for filename in undownloaded_files:
                self.download_file(
                    self.base_media_url.format(self.thread.board, filename),
                    self.thread_media_folder / filename,
                    self.verbose,
                    max_retries,
                )
        # check if the downloaded files are ok
        # TODO: walrus when py38, can't py38 yet because superjson time.clock
        mismatched_hash_files = self._get_hash_mismatches()
        if mismatched_hash_files:
            for m in mismatched_hash_files:
                (self.thread_media_folder / m.filename).unlink()
                # if at first you don't succeed, try, try again.
                self.download_thread_media(max_retries=2)
        else:
            if self.verbose:
                print("All available media has been downloaded.")
            if self._was_thread_archived() or self._was_thread_404():
                if self.verbose:
                    print("Thread media marked as fully downloaded.")
                self._mark_thread_media_as_done()
            return

    @staticmethod
    def _assemble_Reply_from_post(post: dict, board: str) -> Reply:
        post["board"] = board
        if "tim" in post:
            media_filename: str = f"{post['tim']}{post['ext']}"
            post["img_src"] = f"media/{media_filename}"
        return Reply(post)

    def render_thread(self):
        # TODO:
        # check if thread.json has been modified since last render
        posts = self.thread_data["posts"]
        replies = [
            self._assemble_Reply_from_post(p, self.thread.board) for p in posts
        ]
        self.render_and_save_html(
            self.html_page_path,
            thread=self.thread,
            op=replies[0],
            replies=replies[1:],
        )
        if self.verbose:
            print(f"Rendered HTML page at {self.html_page_path}")

    @classmethod
    def _get_archived_threads_from_board(
        cls, board: str, verbose: bool
    ) -> List[str]:
        api_url = f"https://a.4cdn.org/{board}/archive.json"
        r = RetrySession().get(api_url)
        if r.status_code != 200:
            msg = f"Couldn't retrieve {board}'s archived thread list."
            raise Exception(msg)
        data = r.json()
        if verbose:
            print(f"Found {len(data)} archived threads.")
        thread_urls = [
            cls.base_thread_url.format(board=board, thread_id=thread_id)
            for thread_id in sorted(data)
        ]
        return thread_urls

    @classmethod
    def _get_active_threads_from_board(
        cls, board: str, verbose: bool
    ) -> List[str]:
        api_url = f"https://a.4cdn.org/{board}/threads.json"
        r = RetrySession().get(api_url)
        if r.status_code != 200:
            msg = f"Couldn't retrieve {board}'s active thread list."
            raise Exception(msg)
        data = r.json()
        thread_urls = [
            cls.base_thread_url.format(board=board, thread_id=thread["no"])
            for page in data
            for thread in page["threads"]
        ]
        if verbose:
            print(f"Found {len(thread_urls)} active threads.")
        return thread_urls

    @classmethod
    def get_threads_from_board(
        cls, board: str, archived: bool, archived_only: bool, verbose: bool
    ) -> List[str]:
        thread_urls = []
        if not archived_only:
            thread_urls.extend(
                cls._get_active_threads_from_board(board, verbose)
            )
        if archived or archived_only:
            thread_urls.extend(
                cls._get_archived_threads_from_board(board, verbose)
            )
        return thread_urls
