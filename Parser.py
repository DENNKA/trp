import os
import requests
from retry import retry
import tempfile
from pathlib import Path
from fp.fp import FreeProxy
import sys
import re
from ListClass import ListClass
sys.path.append('./rutracker')
import rutracker

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)

from Anime import Anime

class Parser():
    def __init__(self, proxy=""):
        self.download_path = os.path.join(tempfile.gettempdir(), "trp")
        Path(self.download_path).mkdir(parents=True, exist_ok=True)

        self.auto_proxy = False
        self.proxy = proxy
        if proxy == "auto":
            self.auto_proxy = True

    @retry(delay=0.1, logger=logger)
    def get_proxy(self):
        if self.proxy.find("pool://") != -1:
            prx = requests.get(self.proxy.replace("pool://", "")).text
            logger.info(f'Use proxy {prx}')
            return prx
        if self.auto_proxy:
            logger.info("Finding proxy...")
            prx = FreeProxy(timeout=1.5, rand=True).get()
            logger.info("Finding proxy done! " + prx)
            return prx
        return self.proxy


class Rutracker(Parser):
    def __init__(self, proxy=""):
        self.inited = False
        super().__init__(proxy)
        self.tr_to_db = ['forum', 'topic', 'id_torrent', 'size', 'seeds', 'leechs', 'downloads', 'torrent_date']

    def init(self, cfg):
        if self.inited: return
        username = cfg['Rutracker']['username']
        password = cfg['Rutracker']['password']
        try:
            prx = self.get_proxy()
            self.tracker = rutracker.Rutracker(username, password, proxies={'https': prx, 'http': prx})
        except requests.exceptions.RequestException:
            logger.error("Connection to Rutracker failed")
            raise
        self.inited = True


    def _search(self, name):
        return self.tracker.search(name)

    def parse_anime(self, name):
        animes = self._search(name)
        animes_out = list()
        for anime in animes:
            anime_out = dict()
            for i, elem in enumerate(self.tr_to_db):
                anime_out[elem] = anime[i]
            animes_out.append(Anime(vars=anime_out))
        return animes_out

    def get_torrent_file(self, id):
        return self.tracker.get_torrent(id, path=self.download_path)

    def get_total_episodes(self, id, topic):
        return re.findall(r'\d+', topic[topic.find("из"):])[0]

class TorrentTrackers(ListClass):
    def __init__(self, cfg, proxy=""):
        self.cfg = cfg
        self.classes = {
                'Rutracker': Rutracker(proxy),
                }
