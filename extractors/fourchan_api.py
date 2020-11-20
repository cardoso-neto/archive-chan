
import requests
from typing import List
from flask import Flask, render_template

from .extractor import Extractor
from models import Reply, Thread
from resources.database.db_interface import Database
from safe_requests_session import RetrySession


def get_thread_data(board: str, thread_id: str) -> dict:
    r = RetrySession().get(
        f"https://a.4cdn.org/{board}/thread/{thread_id}.json", timeout=16
    )
    if r.status_code != requests.codes.ok:
        print(f"Skip {thread_id} due to error {r.status_code}.")
        raise Exception(f"Thread {thread_id}: error {r.status_code}.")
    return r.json()


class FourChanAPIE(Extractor):
    VALID_URL = r'https?://boards.(4channel|4chan).org/(?P<board>[\w-]+)/thread/(?P<thread>[0-9]+)'

    def __init__(self):
        super().__init__()
        self.app = Flask('archive-chan', template_folder='./assets/templates/')
        self.thread_data: dict
        self.db = Database()

    def render_and_save_html(self, output_path: str, **kwargs):
        with self.app.app_context():
            rendered = render_template('thread.html', **kwargs)
            with open(output_path, "w", encoding='utf-8') as html_file:
                html_file.write(rendered)

    def extract(self, thread: Thread, params):
        """
        Get JSON from 4chan API, parse replies, and write to html_file.

        It's a two pass approach. First all text from a thread is saved.
        Then on the second pass all media is parsed.
        The media is downloaded and saved if preserve is True.
        """
        if params.use_db:
            self.update_boards()

        try:
            self.thread_data = get_thread_data(thread.board, thread.tid)
        except Exception as e:
            print(e)
            return

        html_page_path = params.path_to_download / thread.board / f"{thread.tid}.html"
        op_info = self.getOP(params, thread)
        replies = self.getReplyWrite(params, thread, media=False)
        self.render_and_save_html(
            html_page_path, thread=thread, op=op_info, replies=replies
        )
        replies = self.getReplyWrite(params, thread, media=True)
        self.render_and_save_html(
            html_page_path, thread=thread, op=op_info, replies=replies
        )

    def get_post_with_media(self, post: dict, thread: Thread, params) -> Reply:
        if "tim" in post:
            post["img_src"] = "https://i.4cdn.org/{}/{}{}".format(
                thread.board, post["tim"], post["ext"]
            )
            image_filename = "{}{}".format(post["filename"], post["ext"])
            folder_path = params.path_to_download / thread.board / thread.tid
            if params.preserve:
                self.download(post["img_src"], folder_path, image_filename, params)
                post["img_src"] = '{}/{}'.format(thread.tid, image_filename)
        post["board"] = thread.board
        post["preserved"] = params.preserve
        reply = Reply(post)
        return reply

    def get_post(self, post: dict, thread: Thread, params) -> Reply:
        if params.verbose:
            print("Downloading post text:", post["no"], "from", post["now"])
        post["board"] = thread.board
        post["preserved"] = False
        reply = Reply(post)
        return reply

    def getOP(self, params, thread: Thread):
        op_post = self.thread_data["posts"][0]
        reply = self.get_post_with_media(op_post, thread, params)
        if params.use_db:
            self.db.insert_reply(reply)
        return reply

    def getReplyWrite(self, params, thread: Thread, media: bool) -> List[Reply]:
        reply_posts = self.thread_data["posts"][1:]
        total_posts = len(reply_posts)
        if params.total_posts:
            total_posts = params.total_posts
        if media:
            replies = [
                self.get_post_with_media(reply, thread, params)
                for reply in reply_posts[:total_posts]
            ]
        else:
            replies = [
                self.get_post(reply, thread, params)
                for reply in reply_posts[:total_posts]
            ]
        if params.use_db:
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
