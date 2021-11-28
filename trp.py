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
import platform
import subprocess
import shutil
import json

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)


from Player import Player
from Torrent import Torrent
from Parser import ParserRutracker
from ParserFiles import ParserFiles
from AnimeList import AnimeList


class Trp():
    def __init__(self, args):
        if args.migrate:
            self.migrate()
        self.conn = sqlite3.connect("anime.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.create_table()

        cfg = configparser.ConfigParser()
        cfg.read_file(open('settings.cfg'))
        username = cfg['login']['username']
        password = cfg['login']['password']

        qb_server = cfg['qbittorrent']['server']
        qb_username = cfg['qbittorrent']['username']
        qb_password = cfg['qbittorrent']['password']
        qb_download_dir = cfg['qbittorrent']['download_dir']
        self.default_reserve = int(cfg['qbittorrent']['default_reserve'])

        client_id = cfg['shikimori']['client_id']
        client_secret = cfg['shikimori']['client_secret']
        if client_id and client_secret:
            anime_list = AnimeList(client_id, client_secret)
            self.anime_list_on = True
        else:
            self.anime_list_on = False

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
                    sql = """SELECT * FROM anime WHERE topic LIKE '%""" + """%' AND topic LIKE '%""".join(words) + """%' COLLATE NOCASE"""

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
                anime = animes[
                               self.interactive([x['topic'] for x in animes], "Select anime: ",
                                                zero_error="Not found anime", return_index=True)
                               ]
                episode_number = anime['current_episode'] + 1
                hash = anime['hash']
                shikimori_id = anime['shikimori_id']
                id = anime['id']

                if self.anime_list_on and not shikimori_id:
                    anime_list_search_results = anime_list.search(self.extract_japanese_from_topic(anime['topic']))
                    anime_list_search = anime_list_search_results[0]
                    if anime_list_search['episodes'] == anime['episodes']:
                        logger.info("Finded anime on animelist: " + anime_list_search['name'] + " | " + anime_list_search['russian']
                                    + " | type: " + anime_list_search['kind'])
                        shikimori_id = anime_list_search['id']
                        self.cursor.execute("UPDATE anime SET shikimori_id=? WHERE id=?", [shikimori_id, id])
                        self.conn.commit()
                    else:
                        logger.error("Anime not finded on animelist")

                if episode_number > anime['last_episode_torrent']:
                    logger.error("No more episodes")
                    return
                else:
                    logger.info("Watching episode {} / {} / {}".format(episode_number, anime['last_episode_torrent'], anime['episodes']))

                parser_files = ParserFiles()
                files = parser_files.files_to_episodes(self.torrent.get_files_paths(hash), self.torrent.get_root(hash))

                episode = files[episode_number]
                episode_path = episode["video"]
                subtitles_dict = episode["subtitle"]
                subtitle_group = anime['subtitle_group']
                install_fonts = 0
                if subtitle_group and subtitle_group in subtitles_dict.keys() and not args.reset_subtitles_group:
                    group_name = subtitle_group
                else:
                    group_name = self.interactive(list(subtitles_dict.keys()), "Select subtitle: ")
                    self.cursor.execute("UPDATE anime SET subtitle_group=? WHERE id=?", [group_name, id])
                    self.conn.commit()
                    install_fonts = 1

                if (not anime['fonts_installed'] or install_fonts) and group_name in files["fonts"].keys():
                    logger.info("Installing fonts...")
                    os_name = platform.system()
                    font_list = files["fonts"][group_name]
                    if os_name == "Windows" or os_name == "Darwin":
                        logger.warning("Installing fonts: detected not supported os " + os_name)
                        logger.warning("Subtitle contains specific fonts, install they by yourself")
                    elif os_name == "Linux":
                        for font in font_list:
                            subprocess.call(["font-manager", "--install", font])

                        self.cursor.execute("UPDATE anime SET fonts_installed=? WHERE id=?", [1, id])
                        self.conn.commit()
                        #os.makedirs("~/.fonts", exist_ok=True)
                        #shutil.copy2(font, "~/.local/share/fonts/" + font.split('/')[-1])
                        #subprocess.call(["fc-cache"])

                    logger.info("Installing fonts done!")

                error = self.player.play(episode_path, episode["subtitle"][group_name])
                #quit(0)
                if not error:

                    if self.anime_list_on:
                        logger.info("Animelist mark episode watched...")
                        anime_list.mark_one(shikimori_id)
                        logger.info("Animelist mark episode watched done!")

                    self.cursor.execute("UPDATE anime SET current_episode=? WHERE id=?", [episode_number, id])
                    self.conn.commit()

                    logger.info("Player closed, episode marked watched")
                    self.update()

                else:
                    logger.info("Player closed with error, episode not marked watched")
                    logger.info("Exiting watch mode")
                    break

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS "anime" (
	            "id"	INTEGER PRIMARY KEY AUTOINCREMENT,
	            "watch"	INTEGER DEFAULT 0,
	            "forum"	TEXT,
	            "topic"	TEXT,
	            "id_torrent"	INTEGER UNIQUE,
	            "size"	TEXT,
	            "s"	INTEGER,
	            "l"	INTEGER,
	            "c"	INTEGER,
	            "date"	INTEGER,
	            "hash"	TEXT DEFAULT 0 UNIQUE,
	            "current_episode"	INTEGER DEFAULT 0,
	            "download_episodes"	INTEGER DEFAULT 0,
	            "reserve_episodes"	INTEGER DEFAULT -1,
	            "last_episode_torrent"	INTEGER,
	            "episodes"	INTEGER,
	            "date_added"	TEXT DEFAULT CURRENT_TIMESTAMP,
	            "subtitle_group"	TEXT,
	            "fonts_installed"	INTEGER,
	            "shikimori_id"	INTEGER
            )
        """)
        self.conn.commit()

    def migrate(self):
        os.rename("anime.db", ".prev.db")
        self.conn = sqlite3.connect("anime.db")
        self.cursor = self.conn.cursor()

        self.create_table()

        self.cursor.execute("attach database '.prev.db' as prev")
        self.cursor.execute("SELECT * from prev.anime")
        animes = self.cursor.fetchall()
        zip_one = [c[0] for c in self.cursor.description]
        for anime in animes:
            rowDict = dict(zip(zip_one, anime))
            placeholders = ', '.join(['?'] * len(rowDict))
            columns = ', '.join(rowDict.keys())
            sql = "INSERT INTO %s ( %s ) VALUES ( %s )" % ("anime", columns, placeholders)
            self.cursor.execute(sql, list(rowDict.values()))
        self.conn.commit()

    def interactive(self, options, text="", one_skip=True, zero_error=None, return_index=False):
        max = len(options)
        if zero_error and max == 0:
            logger.error(zero_error)
            raise ValueError(zero_error)
        if one_skip and max == 1:
            return 0 if return_index else options[0]
        for i, option in enumerate(options):
          print(i, "|", option)
        while True:
            try:
                num = int(input(text))
            except ValueError:
                num = -1
            if num >= 0 and num < max:
                return num if return_index else options[num]

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
                episodes_in_torrents.append(int(re.findall(r'\d+', animes[i][1][:animes[i][1].find("из")])[-1]))
            except IndexError:
                episodes_in_torrents.append(0)
            if anime[2] == id_torrent:
                num = i
                anime_last_episode = episodes_in_torrents[-1]

        #max_value = max(episodes_in_torrents)
        #max_index = episodes_in_torrents.index(max_value)

        if anime_last_episode > last_episode:
            logger.info("Finded new episodes: " + name + " EP: " + str(anime_last_episode))
            anime = animes[num]
            file = self.parser.get_torrent_file(anime[2])
            logger.info("Replacing torrent, wait...")
            new_hash = self.torrent.replace_torrent(hash, file)
            logger.info("Replace torrent done!")

            self.cursor.execute("UPDATE anime SET topic=?, last_episode_torrent=?, hash=? WHERE hash=?", [anime[0], anime_last_episode, new_hash, hash])
            self.conn.commit()

        else:
            logger.info("No new episodes: {} EP: {} / {}".format(name, last_episode, anime_last_episode))

    def bytes_to(self, bytes, to, bsize=1024):
        """
            convert bytes to megabytes, etc.
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
    parser.add_argument('--reset_subtitles_group', action='store_true', default=False, help='If you want select another tranlater(s)')
    parser.add_argument('--migrate', action='store_true', default=False, help='Migrate from old database to new')
    args = parser.parse_args()
    trp = Trp(args)

if __name__ == '__main__':
    main()
