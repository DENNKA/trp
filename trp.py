import sqlite3
import configparser
from prettytable import PrettyTable
from textwrap import fill
import sys
import os
import argparse
import re
import time
import requests

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)


from Player import Player
from Torrent import Torrent
from Parser import ParserRutracker


class Trp():
    def __init__(self, args):

        self.conn = sqlite3.connect("anime.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        cfg = configparser.ConfigParser()
        cfg.read_file(open('settings.cfg'))
        username = cfg['login']['username']
        password = cfg['login']['password']

        qb_server = cfg['qbittorrent']['server']
        qb_username = cfg['qbittorrent']['username']
        qb_password = cfg['qbittorrent']['password']
        qb_download_dir = cfg['qbittorrent']['download_dir']
        self.default_reserve = int(cfg['qbittorrent']['default_reserve'])

        self.search_forums = cfg['tracker']['search_forums']
        if self.search_forums:
            self.search_forums = "&f=" + self.search_forums

        try:
            self.torrent = Torrent(qb_server, qb_username, qb_password, qb_download_dir, self.default_reserve)
        except requests.exceptions.RequestException:
            logger.error("Connection to qbittorrent failed, run qbittorrent and enable webUI")
            raise

        self.player = Player()

        if args.update:
            self.update()

        if args.find:
            self.parser = ParserRutracker(args.proxy, username=username, password=password)
            self.find()
            self.update()

        if args.add:
            self.parser = ParserRutracker(args.proxy, username=username, password=password)
            hash = self.add_anime(args.add)

            if hash:
                self.change_watched_episodes(hash, args.watched) if args.watched else None
                self.update()

        if args.watch:
            while True:
                if args.watch == "manual":
                    sql = "SELECT * FROM anime ORDER BY id DESC"
                else:
                    words = args.watch.split(" ")
                    sql = """SELECT * FROM anime WHERE topic LIKE '%""" + """%' AND topic LIKE '%""".join(words) + """%'"""

                self.cursor.execute(sql)
                self.conn.commit()
                animes = self.cursor.fetchall()
                len_animes = len(animes)
                if args.watch == "manual" or len_animes > 1:
                    for i, anime in enumerate(animes):
                        print(i, anime['topic'])
                    num = int(input("Select anime: "))
                else:
                    if len_animes < 1:
                        logger.error("Not found anime")
                        return
                    else:
                        num = 0

                anime = animes[num]

                episode = anime['current_episode'] + 1

                if episode > anime['last_episode_torrent']:
                    logger.error("No more episodes")
                    return
                else:
                    logger.info("Watching episode {} / {} / {}".format(episode, anime['last_episode_torrent'], anime['episodes']))

                root = self.torrent.get_torrent_path(anime['hash'])
                episode_path = os.path.join(root, self.torrent.get_episode_path(anime['hash'], episode))
                subtitle_path = os.path.join(root, self.torrent.get_subtitle_path(anime['hash'], episode))

                error = self.player.play(episode_path, subtitle_path)

                if not error:
                    self.cursor.execute("UPDATE anime SET current_episode=?", [episode])
                    self.conn.commit()

                    logger.info("Player closed, episode marked watched")
                    self.update()

                else:
                    logger.info("Player closed with error, episode not marked watched")
                    logger.info("Exiting watch mode")
                    break

    def update(self):
        logger.info("Start update")

        self.cursor.execute("SELECT * FROM anime WHERE watch=1")
        self.conn.commit()
        for anime in self.cursor.fetchall():
            #shift = anime['download_episodes'] - anime['current_episode']
            needed = self.default_reserve if anime['reserve_episodes'] == -1 else anime['reserve_episodes']
            needed = needed if needed < anime['last_episode_torrent'] - anime['current_episode'] else anime['last_episode_torrent'] - anime['current_episode']
            download = []
            if needed:
                for i in range(anime['current_episode'] + 1, anime['current_episode'] + 1 + needed):
                    download.append(i)

                self.torrent.load_episodes(anime['hash'], download, [3 if i == 0 else 2 if i == 1 else 1 for i in range(0, needed)])
                self.torrent.resume(anime['hash'])

        logger.info("Update done!")

    def change_watched_episodes(self, hash, watched):
        self.cursor.execute("UPDATE anime SET current_episode=? WHERE hash=?", [watched, hash])
        self.conn.commit()

    def extract_japanese_from_topic(self, topic):
        # del []() and split
        return re.sub("[\(\[].*?[\)\]]", "", topic).split("/")[1].strip()

    def find(self):
        self.cursor.execute("SELECT * FROM anime WHERE last_episode_torrent != episodes AND watch=1")
        self.conn.commit()
        for anime in self.cursor.fetchall():
            self.find_new_episodes(self.extract_japanese_from_topic(anime['topic']), anime['id_torrent'],
                                   anime['last_episode_torrent'], anime['hash'])

    def find_new_episodes(self, name, id_torrent, last_episode, hash):
        animes = self.parser.parse_anime(name)

        episodes_in_torrents = []

        for i, anime in enumerate(animes):
            try:
                episodes_in_torrents.append(int(re.findall(r'\d+', animes[i][3][:animes[i][3].find("из")])[-1]))
            except IndexError:
                episodes_in_torrents.append(0)
            if anime[4].find(str(id_torrent)) != -1:
                num = i
                anime_last_episode = episodes_in_torrents[-1]

        #max_value = max(episodes_in_torrents)
        #max_index = episodes_in_torrents.index(max_value)

        if anime_last_episode > last_episode:
            logger.info("Finded new episodes: " + name + " EP: " + str(anime_last_episode))
            anime = animes[num]
            file = self.parser.get_torrent_file(anime[4])
            logger.info("Replacing torrent, wait...")
            new_hash = self.torrent.replace_torrent(hash, file)
            logger.info("Replace torrent done!")

            self.cursor.execute("UPDATE anime SET topic=?, last_episode_torrent=?, hash=? WHERE hash=?", [anime[3], anime_last_episode, new_hash, hash])
            self.conn.commit()

    def bytes_to(self, bytes, to, bsize=1024):
        """convert bytes to megabytes, etc.
           sample code:
               print('mb= ' + str(bytesto(314575262000000, 'm')))
           sample output:
               mb= 300002347.946
        """

        a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6}
        r = float(bytes)
        for i in range(a[to]):
            r = r / bsize

        return(r)

    def add_anime(self, name, auto=False):
        animes = self.parser.parse_anime(name + self.search_forums)

        if len(animes) == 0:
            logger.error("Anime not found")
            return

        if auto:
            # NOT USE
            for i, anime in enumerate(animes):
                if anime[3].find("1080p") != -1 and anime[3].upper().find("BDREMUX") == -1:
                    num = i
                    break
            if not url:
                for i, anime in enumerate(animes):
                    if anime[3].find("720p") != -1 and anime[3].upper().find("BDREMUX") == -1:
                        num = i
                        break
            if not url:
                for i, anime in enumerate(animes):
                    if anime[3].find("BDRip") != -1 and anime[3].upper().find("BDREMUX") == -1:
                        num = i
                        break
        else:
            x = PrettyTable()
            x.field_names = ["i", "forum", "topic", "id", "size", "s", "l", "c", "date"]
            for i, anime in enumerate(animes):
                add = [i] + list(anime)
                add[1] = fill(add[1], width=15)
                add[2] = fill(add[2], width=70)
                add[4] = str(round(self.bytes_to(add[4], 'g'), 2)) + " GiB"
                add[-1] = time.strftime("%D", time.localtime(add[-1]))
                x.add_row(add)
            print(x.get_string(fields=["i", "forum", "topic", "size", "s", "l", "c", "date"]))
            num = int(input("Type anime number: "))

        id_anime = animes[num][2]

        file = self.parser.get_torrent_file(id_anime)
        if file:
            logger.info("Adding torrent file...")
            hash = self.torrent.add_torrent(file)
            logger.info("Adding torrent file done!")

        episodes = re.findall(r'\d+', animes[num][1][animes[num][1].find("из"):])[0]
        sql_list = [1] + list(animes[num]) + [hash] + [episodes] + [self.torrent.get_last_episode(hash)]
        self.cursor.execute("""INSERT INTO anime(watch, forum, topic, id_torrent, size, s, l, c, date, hash, episodes, last_episode_torrent)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""", sql_list)
        self.conn.commit()

        return hash

def main():
    parser = argparse.ArgumentParser(description='Torrent player')
    parser.add_argument('--add', type=str, default="", help='Search anime on tracker contains in topic WORD1 and WORD2...')
    parser.add_argument('--watched', type=int, default=0, help='Watched series of added anime')
    parser.add_argument('--watch', type=str, default="", help='Watch anime contains in topic WORD1 and WORD2...')
    parser.add_argument('--proxy', type=str, default="", help='Proxy, use auto for auto provided proxy, use socks5://127.0.0.1:9150 for tor')
    parser.add_argument('--update', action='store_true', default=False, help='Manual update')
    parser.add_argument('--find', action='store_true', default=False, help='Find new episodes')
    args = parser.parse_args()
    trp = Trp(args)

if __name__ == '__main__':
    main()
