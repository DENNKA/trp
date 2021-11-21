import os
import requests
from retry import retry
import tempfile
from pathlib import Path
from fp.fp import FreeProxy
from rutracker import Rutracker

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)


class Parser():
    def __init__(self, proxy=None):
        self.download_path = os.path.join(tempfile.gettempdir(), "trp")
        Path(self.download_path).mkdir(parents=True, exist_ok=True)

        self.auto_proxy = False
        self.proxy = proxy
        if proxy == "auto":
            self.auto_proxy = True

    @retry(delay=0.1, logger=logger)
    def get_proxy(self):
        if self.auto_proxy:
            logger.info("Finding proxy...")
            prx = FreeProxy(timeout=1.5, rand=True).get()
            logger.info("Finding proxy done! " + prx)
            return prx
        return self.proxy


class ParserRutracker(Parser):
    def __init__(self, proxy=None, username=None, password=None):
        super().__init__(proxy)
        #FIXME: need retry call for auto proxy
        try:
            self.tracker = Rutracker(username, password, proxies={'https': self.get_proxy()})
        except requests.exceptions.RequestException:
            logger.error("Connection to Rutracker failed")
            raise

    def parse_anime(self, name):
        return self.tracker.search(name)

    def get_torrent_file(self, id):
        return self.tracker.get_torrent(id, path=self.download_path)
