import os
from pathlib import Path
from typing import List, Optional

import requests
from flask import Flask, render_template
from superjson import json

from .extractor import Extractor
from models import Params, Reply, Thread
from resources.database.db_interface import Database
from safe_requests_session import RetrySession
from utils import count_files_in_dir, safely_create_dir


class FourChanAPIE(Extractor):
    VALID_URL = r'https?://boards.(4channel|4chan).org/(?P<board>[\w-]+)/thread/(?P<thread>[0-9]+)'
    base_thread_url = "https://boards.4chan.org/{board}/thread/{thread_id}"

    def __init__(self, thread: Thread = None, verbose: bool = True):
        super().__init__()
        self.thread = thread
        self.verbose = verbose
        self.app = Flask('archive-chan', template_folder='./assets/templates/')
        self.thread_data: dict
        # self.db = Database()  # I'll end up deprecating this

    @staticmethod
    def get_thread_data(board: str, thread_id: str) -> dict:
        r = RetrySession().get(
            f"https://a.4cdn.org/{board}/thread/{thread_id}.json", timeout=16
        )
        if r.status_code != requests.codes.ok:
            print(f"Skip {thread_id} due to error {r.status_code}.")
            raise Exception(f"Thread {thread_id}: error {r.status_code}.")
        return r.json()

    def _load_previous_thread_data(self) -> Optional[dict]:
        if not self.json_path.is_file():
            return None
        return json.load(str(self.json_path), verbose=self.verbose)

    def _no_new_replies(self):
        if self.json_path.is_file():
            if self.previous_thread_data["posts"][0]["replies"] == self.thread_data["posts"][0]["replies"]:
                if self.verbose:
                    print("No new replies.")
                return True
        return False

    def _was_thread_archived(self) -> bool:
        return self.previous_thread_data["posts"][0]["archived"]

    def _was_thread_404(self) -> bool:
        try:
            return self.previous_thread_data["archive-chan"]["404"]
        except KeyError:
            return False

    def download_thread_data(self, archive_path: Path):
        self.thread_folder = archive_path.joinpath(
            self.thread.board, self.thread.tid
        )
        safely_create_dir(self.thread_folder)
        self.json_path = self.thread_folder / "thread.json"
        self.previous_thread_data = self._load_previous_thread_data()
        if self.previous_thread_data is not None:
            if self._was_thread_archived() or self._was_thread_404():
                return
        try:
            self.thread_data = self.get_thread_data(
                self.thread.board, self.thread.tid
            )
        except Exception as e:
            msg = f"Could not download {self.thread.id} from the API."
            raise RuntimeError(f"{msg}\n{repr(e)}")
        if self._no_new_replies():
            return
        json.dump(
            self.thread_data,
            str(self.json_path),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            overwrite=True,
            verbose=self.verbose,
            )

    def extract(
        self,
        thread: Thread,
        params: Params,
        thread_folder: Path,
        use_db: bool = False,
        verbose: bool = False,
    ):
        """
        Get JSON from 4chan API, parse replies, and write to html_file.

        It's a two pass approach. First all text from a thread is saved.
        Then on the second pass all media is parsed.
        The media is downloaded and saved if preserve is True.
        """
        self.max_retries = params.total_retries
        self.thread_folder = thread_folder
        self.thread_media_folder = self.thread_folder / "media"
        self.json_path = self.thread_folder / "thread.json"
        self.total_posts = params.total_posts
        self.use_db = use_db
        self.verbose = verbose
        if self.use_db:
            self.update_boards()

        try:
            self.thread_data = self.get_thread_data(thread.board, thread.tid)
        except Exception as e:
            print(e)
            return
        if self._no_new_replies():
            downloaded_media_count = count_files_in_dir(self.thread_media_folder)
            if self.previous_thread_data["posts"][0]["images"] + 1 == downloaded_media_count:
                # + 1 because of the OP image
                # what about partially downloaded images or corrupted ones?
                # if old_thread.get("archive-chan", {}).get("images-ok", False):
                return
        json.dump(
            self.thread_data,
            str(self.json_path),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            overwrite=True,
            verbose=self.verbose,
        )
        op_info = self.getOP(params, thread)
        replies = self.getReplyWrite(thread, media=False)
        html_page_path = self.thread_folder / "no-media-index.html"
        self.render_and_save_html(
            html_page_path, thread=thread, op=op_info, replies=replies
        )
        if params.preserve:
            replies = self.getReplyWrite(thread, media=True)
            html_page_path = self.thread_folder / "index.html"
            self.render_and_save_html(
                html_page_path, thread=thread, op=op_info, replies=replies
            )

    def get_post_with_media(
        self, post: dict, thread: Thread, max_retries: int = 3
    ) -> Reply:
        post["board"] = thread.board
        post["preserved"] = True
        if "tim" in post:
            media_4chan_url = "https://i.4cdn.org/{}/{}{}".format(
                thread.board, post["tim"], post["ext"]
            )
            media_folder_path: Path = self.thread_folder / "media"
            safely_create_dir(media_folder_path)
            media_filename: str = f"{post['tim']}{post['ext']}"
            post["img_src"] = f"media/{media_filename}"
            media_file_path = media_folder_path / media_filename
            if media_file_path.is_file():
                if media_file_path.stat().st_size == post["fsize"]:
                    media_file_md5_path = media_file_path.parent.joinpath(
                        f"{media_file_path.stem}.md5"
                    )
                    command = f"openssl md5 -binary {str(media_file_path)}"
                    command += " | openssl base64"
                    command += f" > {str(media_file_md5_path)}"
                    os.system(command)
                    with open(media_file_md5_path) as media_file_md5_file:
                        calculated_md5_digest = media_file_md5_file.read()
                    media_file_md5_path.unlink()
                    if calculated_md5_digest.rstrip("\n") == post["md5"]:
                        if self.verbose:
                            print(f"{media_file_path.name!r} already downloaded.")
                        return Reply(post)
            self.download_file(
                media_4chan_url,
                media_file_path,
                self.verbose,
                max_retries,
            )
        return Reply(post)

    def get_post(self, post: dict, thread: Thread) -> Reply:
        if self.verbose:
            print("Downloading post text:", post["no"], "from", post["now"])
        if "tim" in post:
            post["img_src"] = "https://i.4cdn.org/{}/{}{}".format(
                thread.board, post["tim"], post["ext"]
            )
        post["board"] = thread.board
        post["preserved"] = False
        reply = Reply(post)
        return reply

    def getOP(self, params, thread: Thread):
        op_post = self.thread_data["posts"][0]
        reply = self.get_post_with_media(op_post, thread, params)
        if self.use_db:
            self.db.insert_reply(reply)
        return reply

    def getReplyWrite(self, thread: Thread, media: bool) -> List[Reply]:
        reply_posts = self.thread_data["posts"][1:]
        total_posts = len(reply_posts)
        if self.total_posts:
            total_posts = self.total_posts
        if media:
            replies = [
                self.get_post_with_media(reply, thread, self.max_retries)
                for reply in reply_posts[:total_posts]
            ]
        else:
            replies = [
                self.get_post(reply, thread)
                for reply in reply_posts[:total_posts]
            ]
        if self.use_db:
            for reply in replies:
                self.db.insert_reply(reply)
        return replies

    def update_boards(self):
        r = RetrySession().get("https://a.4cdn.org/boards.json")
        if r.status_code != requests.codes.ok:
            print(f"Could not update boards due to error {r.status_code}.")
            return
        boards = r.json()

        keys = ["board", "title", "ws_board", "per_page", "pages",
                "max_filesize", "max_webm_filesize", "max_comment_chars",
                "max_webm_duration", "bump_limit", "image_limit",
                "cooldowns_t", "cooldowns_r", "cooldowns_i",
                "meta_description", "spoilers", "custom_spoilers",
                "is_archived", "troll_flags", "country_flags", "user_ids",
                "oekai", "sjis_tags", "code_tags", "text_only",
                "forced_anon", "webm_audio", "require_subject",
                "min_image_width", "min_image_height"]

        for board in boards["boards"]:
            print(board["title"], end="\r")
            values = []
            for key in keys:
                if "cooldowns_t" == key:
                    values.append(board["cooldowns"]["threads"])
                elif "cooldowns_r" == key:
                    values.append(board["cooldowns"]["replies"])
                elif "cooldowns_i" == key:
                    values.append(board["cooldowns"]["images"])
                else:
                    values.append(board.get(key, None))
            self.db.insert_board(tuple(values))
