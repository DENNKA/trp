import sqlite3
import configparser
import threading
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
import signal
# signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5.QtWidgets import QApplication
import Gui

import logging

from Proxy import Proxy
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
    force=True,
    handlers=[
        logging.FileHandler("trp.log"),
        logging.StreamHandler()
    ]
)

from Player import Player
from TorrentClient import *
from TorrentTracker import TorrentTrackers
from ParserFiles import ParserFiles
from AnimeList import AnimeLists
from Server import get_server
from Database import Database
from Anime import Anime
from File import File

class Trp():
    def __init__(self, args):
        self.database = Database()
        if args.migrate:
            self.database.migrate()

        self.cfg = cfg = configparser.ConfigParser()
        cfg.read_file(open('settings.cfg'))

        self.download_path = cfg['trp']['download_dir']
        self.default_reserve = int(cfg['trp']['default_reserve'])

        self.search_forums = cfg['Rutracker']['search_forums']
        if self.search_forums:
            self.search_forums = "&f=" + self.search_forums

        self.proxy = Proxy(cfg)

        self.torrent_trackers = TorrentTrackers(cfg, self.proxy)
        self.torrent_clients = TorrentClients(cfg, self.proxy)
        self.anime_lists = AnimeLists(cfg, self.proxy)

        self.player = Player()
        self.parser_files = ParserFiles()

        if args.console == False:
            app = QApplication(sys.argv)
            self.gui = Gui.Window(self, cfg, self.torrent_clients)
            self.gui.showMaximized()
            sys.exit(app.exec_())

        if args.update:
            self.update(args.console)

        if args.find:
            self.find()
            self.update(args.console)

        if args.add:
            anime = self.add_anime(args.add, cfg["trp"]["quality"], cfg.getboolean("trp", "bdremux_only"),
                    cfg["trp"]["torrent_tracker"], cfg["trp"]["torrent_client"], cfg["trp"]["anime_list"], False,  console=True)

            if anime.hash:
                self.update(args.console)

        if args.watch:
            if args.watch == "manual":
                animes = self.database.get_animes()
            else:
                animes = self.database.get_animes_by_name(args.watch)

            anime = animes[
                           self.interactive([x.topic for x in animes], "Select anime: ",
                                            zero_error="Not found anime", return_index=True)
                           ]

            self.watch(args, args.console)

    def start_server(self, port, serve_path, hash, is_available, torrent_file_id):
        self.httpd = get_server(port, serve_path, hash, is_available, torrent_file_id)
        # self.httpd.database = self.database
        # self.httpd.trp = self
        self.server_thread = threading.Thread(None, self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        server_address = "http://127.0.0.1:" + str(port) + "/"
        logger.info("Start video server on " + server_address)
        return server_address

    def shutdown_server(self):
        self.httpd.shutdown()
        self.httpd.socket.close()
        self.server_thread.join()

    def get_is_available(self, anime : Anime):
        return anime.torrent_client.is_available

    def get_full_path(self, anime_name, type):
        anime = self.get_anime(anime_name)
        return os.path.join(anime.download_path, anime.get_file(type).path)

    def get_file(self, anime_name, type):
        return self.get_anime(anime_name).get_file(type)

    def _str_to_classes(self, anime : Anime, raise_on_error=False):
        # torrent_tracker, torrent_client, anime_list strings to class
        if anime.torrent_tracker and type(anime.torrent_tracker) == type(str()):
            anime.torrent_tracker = self.torrent_trackers.get_class(anime.torrent_tracker, raise_on_error)
        if anime.torrent_client and type(anime.torrent_client) == type(str()):
            anime.torrent_client = self.torrent_clients.get_class(anime.torrent_client, raise_on_error)
        if anime.anime_list and type(anime.anime_list) == type(str()):
            anime.anime_list = self.anime_lists.get_class(anime.anime_list, raise_on_error)

    def get_anime(self, anime_name, unnecessary=[]):
        animes = self.database.get_animes_by_name(anime_name)
        if len(animes) == 0:
            raise ValueError("Not found")
        anime = animes[0]
        for var in unnecessary:
            anime.set_variable(var, None)
        self._str_to_classes(anime)
        return anime

    def get_animes(self, unnecessary=[]):
        animes = self.database.get_animes()
        for anime in animes:
            for var in unnecessary:
                anime.set_variable(var, None)
            self._str_to_classes(anime)
        return animes

    def delete_anime(self, anime : Anime, erase_data=False):
        self.database.remove_anime(anime)
        if erase_data:
            anime.torrent_client.remove_torrent(anime.hash, erase_data)

    def watch(self, anime : Anime, console=False, stream=False):
        once = 1
        while stream or once:
            once = 0
            anime.torrent_client.update_files(anime)

            episode_number = anime.episodes_watched + 1

            if anime.anime_list and not anime.id_anime_list:
                anime_list_search_results = anime.anime_list.search(self.extract_japanese_from_topic(anime.topic))
                anime_list_search = anime_list_search_results[0]
                if anime_list_search['episodes'] == anime.total_episodes:
                    logger.info("Finded anime on animelist: " + anime_list_search['name'] + " | " + anime_list_search['russian']
                                + " | type: " + anime_list_search['kind'])
                    anime.id_anime_list = anime_list_search['id']
                    anime.name_translated = anime_list_search['russian'] # TODO: russian to translated
                    self.database.update_anime(anime)
                else:
                    logger.error("Anime not finded on animelist")
            else:
                logger.debug("Anime id on animelist: " + str(anime.id_anime_list))

            if episode_number > anime.last_episode_torrent:
                logger.error("No more episodes")
                break
            else:
                logger.info("Watching episode {} / {} / {}".format(episode_number, anime.last_episode_torrent, anime.total_episodes))

            video_file = anime.get_file("video")
            try:
                subtitle_file = anime.get_file("subtitle")
            except ValueError:
                subtitle_file = None
            try:
                audio_file = anime.get_file("audio")
            except ValueError:
                audio_file = None

            # episode = files[episode_number + shift]
            # episode_path = episode["video"]
            # subtitles_dict = episode["subtitle"]
            # subtitle_group = anime['subtitle_group']
            if stream:
                pass
                # self.httpd.episode_path = video_file.path.replace(root_path, "")
                # episode_address = server_address + "anime"
                # print(episode_address)
                # time.sleep(10)
                # while True:
                #     try:
                #         file_watched_percentage = float(requests.get(server_address + "status").json()['file_watched_percentage'])
                #         if file_watched_percentage and file_watched_percentage > 0.99:
                #             error = 0
                #             break
                #     except Exception:
                #         pass
                #     finally:
                #         time.sleep(2)
            else:
                if video_file.progress > 0.99:
                    server_address = self.start_server(11111, anime.download_path, None, None, None)
                else:
                    anime.torrent_client.enable_sequential_download(anime.hash)
                    server_address = self.start_server(11111, anime.download_path, anime.hash, self.get_is_available(anime), video_file.torrent_file_id)
                episode_address = server_address + video_file.path
                logger.info(f'Start playing {episode_address}')
                error = self.player.play(episode_address, subtitle_file.path, audio_file.path)
                self.shutdown_server()
                if video_file.progress < 0.99:
                    anime.torrent_client.disable_sequential_download(anime.hash)

            # if video_file.progress < 1.0:
            #     self.torrent.disable_sequential_download(anime.hash)
            #     logger.info("Disable sequential download")

            # try:
            #     file_watched_percentage = float(requests.get(server_address + "status").json()['file_watched_percentage'])
            # except Exception as e:
            #     file_watched_percentage = 0.0
            #     logger.error("Can't get watched percentage, set zero")
            #     logger.error(e)

            # needed_file_watched_percentage = 0.90
            # if file_watched_percentage > needed_file_watched_percentage and error == 0:
            if error == 0:

                if anime.anime_list:
                    logger.info("Animelist mark episode watched...")
                    anime.anime_list.mark_one(anime.id_anime_list)
                    logger.info("Animelist mark episode watched done!")

                anime.episodes_watched = episode_number
                self.database.update_anime(anime)

                logger.info("Episode ended, episode marked watched")
                self.update(console)

            else:
                logger.info("Player closed with error, episode not marked watched")
                logger.info("Exiting watch mode")

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

    def _install_fonts(self, fonts):
        logger.info("Installing fonts...")
        os_name = platform.system()
        if os_name == "Windows" or os_name == "Darwin":
            logger.warning("Installing fonts: detected not supported os " + os_name)
            logger.warning("Subtitle contains specific fonts, install they by yourself")
            return
        elif os_name == "Linux":
            for font in fonts:
                subprocess.call(["font-manager", "--install", font])
        logger.info("Installing fonts done!")

    def _select_groups(self, anime : Anime, force=False, console=False):
        if self.cfg.getboolean('trp', 'subtitles') and (anime.subtitle_group == "-1" or force):
            subtitle_groups = anime.get_subtitle_groups()
            if len(subtitle_groups) == 1:
                anime.subtitle_group = subtitle_groups[0]
                logger.info(f'Auto select subtitle group: {anime.subtitle_group}')
            elif len(subtitle_groups) > 1:
                subtitle_groups = ['-1'] + subtitle_groups
                if console:
                    anime.subtitle_group = self.interactive(subtitle_groups, "Select subtitle: ")
                else:
                    anime.subtitle_group = str(self.gui.question(subtitle_groups, "Select subtitle: "))

                fonts = anime.get_files("font")

                try:
                    self._install_fonts(fonts)
                    anime.fonts_installed = 1
                except Exception as e:
                    logger.error("Can't install fonts: " + str(e))

        if self.cfg.getboolean('trp', 'audio') and (anime.audio_group == "-1" or force):
            audio_groups = anime.get_audio_groups()
            if len(audio_groups) == 1:
                anime.audio_group = audio_groups[0]
                logger.info(f'Auto select audio group: {anime.subtitle_group}')
            elif len(audio_groups) > 1:
                audio_groups = ['-1'] + audio_groups
                if console:
                    anime.audio_group = str(self.interactive(audio_groups, "Select audio: "))
                else:
                    anime.audio_group = self.gui.question(audio_groups, "Select audio: ")

    def update(self, console=False):
        logger.info("Start update")

        for anime in self.get_animes(["torrent_tracker", "anime_list"]):
            anime.torrent_client.update_files(anime)
            self._select_groups(anime, console=console)
            self.database.update_anime(anime)

            needed = self.default_reserve if anime.reserve_episodes == -1 else anime.reserve_episodes
            needed = needed if needed < anime.last_episode_torrent - anime.episodes_watched else anime.last_episode_torrent - anime.episodes_watched
            download = []
            hash = anime.hash
            # files = self.parser_files.files_to_episodes(anime.get_files(), self.torrent.get_root(hash))
            # shift = files['first_episode'] - 1
            try:
                anime.get_episode(-1).set_priority(0)
            except ValueError:
                pass
            try:
                anime.get_episode(0).set_priority(0)
                anime.get_episode(0).set_priority(3, [anime.subtitle_group, anime.audio_group])
            except ValueError:
                pass
            if needed:
                priorities = [3 if i == 0 else 2 if i == 1 else 1 for i in range(0, needed)]
                for i in range(anime.episodes_watched + 1, anime.episodes_watched + 1 + needed):
                    # download.append(i + shift)
                    download.append(i)

                for i in range(anime.episodes_watched + 1 + needed, anime.last_episode_torrent + 1):
                    priorities.append(0)
                    download.append(i)

                for ep, priority in zip(download, priorities):
                    try:
                        episode = anime.get_episode(ep)
                        episode.set_priority(priority, [anime.subtitle_group, anime.audio_group])
                    except ValueError as e:
                        logger.error(e)
                        return

                logger.debug("Priorities: " + str(dict(zip(download, priorities))))

                anime.torrent_client.update_files(anime)
                self.database.update_anime(anime)
                # self.torrent.load_episodes(hash, download, [3 if i == 0 else 2 if i == 1 else 1 for i in range(0, needed)])
                anime.torrent_client.resume(hash)

        logger.info("Update done!")

    def extract_japanese_from_topic(self, topic):
        # del []() and split
        return re.sub("[\(\[].*?[\)\]]", "", topic).split("/")[1].strip()

    def find(self):
        for anime in self.database.get_animes_not_finished():
            self._find_new_episodes(anime)

    def _find_new_episodes(self, anime_find : Anime):
        animes = anime_find.torrent_tracker.parse_anime(self.extract_japanese_from_topic(anime_find.topic))

        episodes_in_torrents = []

        anime_last_episode = 0

        for i, anime in enumerate(animes):
            try:
                episodes_in_torrents.append(int(re.findall(r'\d+', anime.topic[:anime.topic.find("из")])[-1]))
            except IndexError:
                episodes_in_torrents.append(0)
            if anime.id_torrent == anime_find.id_torrent:
                num = i
                anime_last_episode = episodes_in_torrents[-1]

        if anime_last_episode < 1:
            return

        anime_finded = animes[num]

        #max_value = max(episodes_in_torrents)
        #max_index = episodes_in_torrents.index(max_value)

        if anime_last_episode > anime_find.last_episode_torrent:
            logger.info("Finded new episodes: " + anime_finded.topic + " EP: " + str(anime_last_episode))
            file = self.parser.get_torrent_file(anime_finded.id_torrent)
            logger.info("Replacing torrent, wait...")
            anime_find.torrent_client.replace_torrent(anime_find, file) # anime_find auto updated in torrent
            logger.info("Replace torrent done!")

            self.database.update_anime(anime_find)

        else:
            logger.info("No new episodes: {} EP: {} / {}".format(anime_find.topic, anime_find.last_episode_torrent, anime_last_episode))

    def save_cfg(self):
        with open('settings.cfg', 'w') as configure:
            self.cfg.write(configure)

    def bytes_to(self, bytes, to, bsize=1024):
        """
            convert bytes to megabytes, etc.
        """

        a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6}
        r = float(bytes)
        for i in range(a[to]):
            r = r / bsize

        return(r)

    def get_quality_list(self):
        # -1 is manual
        quality_list = [-1, 0, 480, 720, 1080, 1440, 2160]
        return quality_list

    def add_anime(self, name, quality, bdremux_only, torrent_tracker, torrent_client, anime_list, instant_play, console=False):
        # quality 1080 -> index in quality_list, -1 is manual

        quality_list = self.get_quality_list()

        anime_with_classes = Anime()
        anime_with_classes.torrent_tracker = torrent_tracker
        anime_with_classes.torrent_client = torrent_client
        anime_with_classes.anime_list = anime_list
        self._str_to_classes(anime_with_classes, True)

        animes = anime_with_classes.torrent_tracker.parse_anime(name + self.search_forums)

        if len(animes) == 0:
            raise ValueError("Anime not found")

        anime = None

        if quality != -1:
            quality = quality_list.index(int(quality))
            quality = quality_list[quality]
            for a in animes:
                topic_lower = a.topic.lower()
                if topic_lower.find(str(quality)) != -1 and (not bdremux_only or topic_lower.find("bdremux") != -1):
                    anime = a
                    break
                if quality == 0:
                    founded = True
                    for q in quality_list[1:]:
                        if topic_lower.find(str(q)) == -1:
                            founded = False
                            break
                    if not founded:
                        anime = a
                        break
        else:
            x = PrettyTable()
            x.field_names = ["i", "forum", "topic", "id", "size", "s", "l", "c", "date"]
            add = list()
            for i, anime in enumerate(animes):
                add = [i, fill(anime.forum, width=12), fill(anime.topic, width=60), str(round(self.bytes_to(anime.size, 'g'), 2)) + " GiB",
                        anime.seeds, anime.leechs, anime.downloads, time.strftime("%D", time.localtime(anime.torrent_date))]
                x.add_row(add)
            print(x.get_string(fields=["i", "forum", "topic", "size", "s", "l", "c", "date"]))
            num = int(input("Type anime number: "))
            anime = animes[num]

        if anime == None:
            raise ValueError("Anime not selected")

        anime.torrent_tracker = anime_with_classes.torrent_tracker
        anime.torrent_client = anime_with_classes.torrent_client
        anime.anime_list = anime_with_classes.anime_list

        file = anime.torrent_tracker.get_torrent_file(anime.id_torrent)
        anime.total_episodes = anime.torrent_tracker.get_total_episodes(anime.id_torrent, anime.topic)

        if (file == ""):
            raise ValueError("Parser not returned file")

        hash = ""

        try:

            logger.info("Adding torrent file...")
            hash = anime.torrent_client.add_torrent(file, self.download_path)
            logger.info("Adding torrent file done!")

            if hash == "" or hash == None:
                raise ValueError("Torrent client not return hash")

            anime.hash = hash
            if instant_play:
                anime.torrent_client.enable_sequential_download(anime.hash)

            errors = anime.torrent_client.update_files(anime)
            if not console:
                self.gui.display_errors(errors)

            total_episodes = re.findall(r'\d+', anime.topic[anime.topic.find("из"):])[0]
            anime.total_episodes = total_episodes
            self.database.update_anime(anime)

        except Exception as e:
            if hash != "":
                anime.torrent_client.remove_torrent(hash)
                anime.hash = ""
            raise

        return anime

def main():
    parser = argparse.ArgumentParser(description='Torrent player')
    parser.add_argument('--add', type=str, default="", help='Search anime on tracker contains in topic WORD1 and WORD2...')
    parser.add_argument('--watch', type=str, default="", help='Watch anime contains in topic WORD1 and WORD2...')
    parser.add_argument('--update', action='store_true', default=False, help='Manual update')
    parser.add_argument('--find', action='store_true', default=False, help='Find new episodes')
    parser.add_argument('--migrate', action='store_true', default=False, help='Migrate from old database to new')
    parser.add_argument('--port', type=int, default=11111, help='Stream server port')
    parser.add_argument('--console', action='store_true', default=False, help='Console mode')
    args = parser.parse_args()
    trp = Trp(args)

if __name__ == '__main__':
    main()
