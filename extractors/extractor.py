import sys
from abc import abstractmethod
from pathlib import Path

from bs4 import BeautifulSoup as Soup
from flask import Flask, render_template

from models import Params
from safe_requests_session import RetrySession


class Extractor:

    @abstractmethod
    def extract(self, thread, params):
        pass

    def get_page(self, url):
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive',
        }
        page_html = RetrySession().get(url, headers=headers, timeout=10).text
        return page_html

    def parse_html(self, thread, params):
        """
        Parse html, get soup, and write post and replies to html_file.

        Call download if preserve is True
        """

        app = Flask('archive-chan', template_folder='./assets/templates/')

        page_html = self.get_page(thread.url)
        if page_html is None:
            print(f"Error on {thread.tid}. No HTML.")
            return

        page_soup = Soup(page_html, "lxml")
        op_info = self.getOP(page_soup, params, thread)
        replies = self.getReplyWrite(page_soup, params, thread)

        with app.app_context():
            rendered = render_template('thread.html', thread=thread, op=op_info, replies=replies)
            with open("threads/{}/{}.html".format(thread.board, thread.tid), "w+", encoding='utf-8') as html_file:
                html_file.write(rendered)

    def download(
        self,
        url: str,
        file_path: Path,
        verbose: bool = False,
        max_retries: int = 3,
        num_retry: int = 0,
    ):
        """
        Donwload file from `url` to `file_path`.

        If it fails, retry until total retries reached.
        """
        requests_session = RetrySession()
        try:
            if file_path.is_file():
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
                self.download(url, file_path, verbose, max_retries, num_retry)

    @abstractmethod
    def getOP(self, page_soup, params, thread):
        """
        Get the OP information from the page soup.

        Return OP elements in a tuple of strings.
        """
        pass

    @abstractmethod
    def getReplyWrite(self, page_soup, params, thread):
        """
        Get the reply information from page soup.

        Returns a list of replies.
        """
        pass
