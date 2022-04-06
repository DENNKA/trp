import qbittorrent
import os
import re
import time
import collections

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)

from Anime import Anime
from File import File
from ListClass import ListClass

def make_iter(x):
    if isinstance(x, collections.Iterable):
        return x
    else:
        return (x,)

class Qbittorrent():
    def __init__(self):
        self.inited = False
        self.cl_to_db = [('name', 'path'), ('size', 'size'), ('progress', 'progress'), ('priority', 'priority'), ('piece_range', 'piece_range'), ('availability', 'availability'), ('index', 'torrent_file_id')]

    def init(self, cfg):
        if self.inited:
            return

        self.cfg = cfg
        server_address = cfg['Qbittorrent']['server_address']
        username = cfg['Qbittorrent']['username']
        password = cfg['Qbittorrent']['password']
        self.qb = qbittorrent.Client(server_address)

        response = self.qb.login(username, password)
        if response != "Ok." and response is not None:
            raise(RuntimeError("Login " + response))

        self.inited = True

    def _add_file(self, file, download_path):
        torrent_file = open(file, 'rb')
        self.qb.download_from_file(torrent_file, savepath=download_path, category="trp", paused=True, sequentialDownload=False, firstLastPiecePrio=False)
        self._wait(3)

        return self.get_last_torrent_hash()

    def _get_files(self, hash):
        return self.qb.get_torrent_files(hash)

    def get_files(self, hash):
        files = self._get_files(hash)
        files_out = list()
        for file in files:
            file_dict = dict()
            for elem in self.cl_to_db:
                file_dict[elem[1]] = file[elem[0]]
            files_out.append(File(vars=file_dict))
        return files_out

    def _priority_to_client(self, priorities):
        # 0 1 2 3 -> 0 1 6 7
        return [6 if priority == 2 else 7 if priority == 3 else priority for priority in priorities]

    def update_files(self, anime : Anime):
        hash = anime.hash
        files_torrent = self.qb.get_torrent_files(hash)
        anime.download_path = self.get_root(anime.hash)
        if len(anime.get_files()) == 0:
            for file_torrent in files_torrent:
                file = File()
                for elem in self.cl_to_db:
                    file.set_variable(elem[1], file_torrent[elem[0]])

                file.update()
                anime.add_file(file)
            return

        # FIXME: add update new files in torrent and erase code above
        for file in anime.get_files():
            for file_torrent in files_torrent:
                if int(file_torrent['index']) == file.torrent_file_id:
                    file_priority = self._priority_to_client([file.priority])[0]
                    if file_torrent['priority'] != file_priority:
                        logger.debug(f'Set priority {file.path.split("/")[-1]} = {file.priority}')
                        self.qb.set_file_priority(hash, file.torrent_file_id, file_priority)
                        self._wait()
                    for elem in self.cl_to_db:
                        if elem[1] == 'priority':
                            continue
                        file.set_variable(elem[1], file_torrent[elem[0]])
                    break

                # raise(ValueError("File from db not found in torrent"))

    def get_last_torrent_hash(self):
        return self.qb.torrents(sort="added_on", reverse=True, limit=1)[0]['hash']

    def _wait(self, time_in_seconds=1):
        time.sleep(time_in_seconds)

    def add_torrent(self, file, download_path):
        return self._add_file(file, download_path)

    def replace_torrent(self, anime : Anime, file : str):
        self.remove_torrent(anime.hash)
        anime.hash = self._add_file(file, anime.download_path)
        self.update_files(anime)
        return anime.hash

    def _get_file(self, hash, id):
        files = self.qb.get_torrent_files(hash)
        for file in files:
            if file['index'] == id:
                return file
        raise ValueError("File not found in torrent")

    def is_available(self, hash, torrent_file_id, bytes_start, bytes_end):
        pieces = self.qb.get_torrent_piece_states(hash)
        piece_size = self._get_piece_size(hash)
        file_torrent = self._get_file(hash, torrent_file_id)
        piece_start, piece_end = file_torrent['piece_range']
        check_start = piece_start + int(bytes_start / piece_size)
        check_end = min(piece_start + int(bytes_end / piece_size), piece_end)
        for i in range(check_start, check_end):
            if i >= len(pieces): break
            if pieces[i] != 2:
                return False
        return True

    def _get_seq_dl(self, hash):
        for torrent in self.qb.torrents():
            if torrent['hash'] == hash:
                return [torrent['seq_dl'], torrent['f_l_piece_prio']]
        return ValueError("Torrent not found: " + hash)

    def enable_sequential_download(self, hash):
        seq_dl = self._get_seq_dl(hash)
        if seq_dl[0] == False:
            self.qb.toggle_sequential_download(hash)
        if seq_dl[1] == False:
            self.qb.toggle_first_last_piece_priority(hash)

    def disable_sequential_download(self, hash):
        seq_dl = self._get_seq_dl(hash)
        if seq_dl[0] == True:
            self.qb.toggle_sequential_download(hash)
        if seq_dl[1] == True:
            self.qb.toggle_first_last_piece_priority(hash)

    def _get_piece_size(self, hash):
        return int(self.qb.get_torrent(hash)['piece_size'])

    def get_root(self, hash):
        return self.qb.get_torrent(hash)['save_path']

    def remove_torrent(self, hash, erase_data=False):
        self.qb._delete(hash, erase_data)
        self._wait(3)

    def resume(self, hash):
        self.qb.resume(hash)

class TorrentClients(ListClass):
    def __init__(self, cfg, proxy):
        # proxy is not used
        self.cfg = cfg
        self.classes = {
                'Qbittorrent': Qbittorrent(),
                }
