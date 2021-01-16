from bs4 import BeautifulSoup as Soup
from flask import Flask, render_template

from .extractor import Extractor
from models import Reply
from safe_requests_session import RetrySession


class FourChanE(Extractor):
    """
    Deprecated in favor of using the JSON API.
    """
    # VALID_URL = r'https?://boards.(4channel|4chan).org/(?P<board>[\w-]+)/thread/(?P<thread>[0-9]+)'
    VALID_URL = r'deprecated'

    def __init__(self):
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
        self.render_and_save_html(
            "threads/{}/{}.html".format(thread.board, thread.tid),
            thread=thread,
            op=op_info,
            replies=replies,
        )

    def extract(self, thread, params):
        self.parse_html(thread, params)

    def getOP(self, page_soup, params, thread):
        op_post = page_soup.find_all("div", {"class": "postContainer opContainer"})
        op_message = op_post[0].find_all("blockquote", {"class": "postMessage"})[0]

        op_img = op_post[0].find_all("div", {"class": "fileText"})
        op_img_src = ''
        op_img_text = ''
        if len(op_img) > 0:
            op_img_src = op_img[0].find("a")["href"]
            op_img_text = op_img[0].find("a").text
            op_img_src = 'https:{}'.format(op_img_src)

            if params.preserve:
                self.download(op_img_src, op_img_text, params)
                op_img_src = '{}/{}'.format(thread.tid, op_img_text)

        op_subject = op_post[0].find_all("span", {"class": "subject"})[1].text
        op_name = op_post[0].find_all("span", {"class": "name"})[0].text
        op_date = op_post[0].find_all("span", {"class": "dateTime"})[0].text.split("No")[0]
        op_pid = op_post[0].find_all("div", {"class": "post op"})[0]['id'][1:]

        if params.verbose:
            print("Downloading post:", op_pid, "posted on", op_date[:-9])

        p1 = Reply(op_name, op_date, op_message, op_pid, op_img_src, op_img_text, op_subject)
        return p1

    def getReplyWrite(self, page_soup, params, thread):
        reply_post = page_soup.find_all("div", {"class": "postContainer replyContainer"})
        replies = []
        total_posts = len(reply_post)
        if params.total_posts:
            total_posts = min(params.total_posts, len(reply_post))

        for i in range(0, total_posts):
            reply = reply_post[i]
            reply_message = reply.find_all("blockquote", {"class": "postMessage"})[0]
            reply_img = reply.find_all("div", {"class": "fileText"})
            reply_img_src = ''
            reply_img_text = ''
            if len(reply_img) > 0:
                reply_img = reply_img[0].find_all("a")[0]
                reply_img_src = reply_img['href']
                reply_img_text = reply_img.text
                reply_img_src = 'https:{}'.format(reply_img_src)

                if params.preserve:
                    self.download(reply_img_src, reply_img_text, params)
                    reply_img_src = '{}/{}'.format(thread.tid, reply_img_text)

            reply_name = reply.find_all("span", {"class": "name"})[0].text
            reply_date = reply.find_all("span", {"class": "dateTime"})[0].text.split("No")[0]
            reply_pid = reply.find_all("div", {"class": "post reply"})[0]['id'][1:]

            if params.verbose:
                print("Downloading reply:", reply_pid, "replied on", reply_date[:-9])

            reply_info = Reply(reply_name, reply_date, reply_message, reply_pid, reply_img_src, reply_img_text)
            replies.append(reply_info)
        return replies
