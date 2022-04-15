import os
import requests
from retry import retry
import tempfile
from pathlib import Path
import sys
import re
from ListClass import ListClass
sys.path.append('./rutracker')
import rutracker

import logging
logger = logging.getLogger(__name__)

from Anime import Anime

class TorrentTracker():
    def __init__(self, proxy):
        self.download_path = os.path.join(tempfile.gettempdir(), "trp")
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        self.proxy = proxy

class ConnectionFailed(Exception):
    def __init__(self):
        super().__init__("Connection to torrent tracker failed")

class Rutracker(TorrentTracker):
    def __init__(self, proxy):
        self.inited = False
        super().__init__(proxy)
        self.tr_to_db = ['forum', 'topic', 'id_torrent', 'size', 'seeds', 'leechs', 'downloads', 'torrent_date']

    @retry(logger=logger, tries=3)
    def init(self, cfg):
        if self.inited: return
        username = cfg['Rutracker']['username']
        password = cfg['Rutracker']['password']
        try:
            self.current_proxy = self.proxy.get_proxy(self)
            if self.current_proxy:
                # prx = {'https': self.current_proxy, 'http': self.current_proxy}
                prx = {self.current_proxy.split("://")[0]: self.current_proxy}
                logger.info(f'Proxy: {prx}')
            else:
                prx = {}
            self.tracker = rutracker.Rutracker(username, password, proxies=prx)
        except requests.exceptions.RequestException:
            raise ConnectionFailed()
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
    def __init__(self, cfg, proxy):
        self.cfg = cfg
        self.classes = {
                'Rutracker': Rutracker(proxy),
                }
