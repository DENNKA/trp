import re
import anitopy
import pickle

from Episode import Episode
import DbElement
from File import File
from ParserFiles import ParserFiles

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]:%(filename)s:%(funcName)s(%(lineno)d) : %(message)s",
)

class Anime(DbElement.DbElement):
    def __init__(self, vars = None):

        self.episodes = list()
        self.fonts = list()

        self.id = -1
        self.watch = 0
        self.topic = ""
        self.name_japanese = ""
        self.name_translated = ""
        self.episodes_watched = 0
        self.total_episodes = 0
        self.last_episode_torrent = 0
        self.date_added = 0
        self.subtitle_group = "-1"
        self.audio_group = "-1"
        self.fonts_installed = 0
        self.first_episode = 0

        self.torrent_tracker = None
        self.id_torrent = 0
        self.size = 0
        self.seeds = 0
        self.leechs = 0
        self.downloads = 0
        self.torrent_date = 0
        self.forum_id = 0
        self.forum = ""

        self.torrent_client = None
        self.reserve_episodes = -1
        self.hash = ""
        self.download_path = ""
        self.sequential_download = 0

        self.anime_list = None
        self.id_anime_list = 0

        if vars is not None:
            self.set_with_dict(vars)

    # def add_episode(self, files = list(), args = None):
    #     self.episodes.append(Episode(files, args))

    def update(self):
        pass

    def get_files_current_episode(self):
        return self.get_episode(self.episodes_watched + 1).files

    def get_files(self, type=None, group=None):
        files = list()
        for ep in self.episodes:
            if type is None:
                files += ep.files
            else:
                for file in files:
                    if file.type == type and (not group or group == file.group):
                        files += [file]
        return files

    def _find_episode_number(self, path : str):
        return int(re.search(r"\b(?:e(?:p(?:isode)?)?|0x|S\d\dE)?\s*?(\d{2,3})\b", path.split("/")[-1], re.IGNORECASE).group(1))

    def _first_number(self, string : str):
        return int(re.search(r'\d+', string).group())

    def add_files(self, files : list):
        with open('add_files.pkl', 'wb') as f:
            pickle.dump([files, self.download_path], f)
        self.episodes, self.fonts, self.first_episode, self.last_episode_torrent, errors = ParserFiles().parse(files, root=self.download_path)
        for number in range(self.first_episode, self.last_episode_torrent + 1):
            episode = self.get_episode(number)
            if len(episode.get_files_from_type("video")) == 0:
                logger.critical("Video not found from episode: " + str(number))
        return errors

    def add_file(self, file : File):
        if file.type == "fonts":
            self.fonts.append(file)
            return

        parsed = anitopy.parse(file.path.split("/")[-1])
        try:
            episode_number = int(parsed['episode_number'].lstrip('0'))
        except Exception:
            print(f'WARNING: use secondary parse method, file: {file.path}')
            episode_number = self._find_episode_number(file.path)

        new_episode = True
        for ep in self.episodes:
            if ep.episode_number == episode_number:
                new_episode = False
                episode = ep
                break

        if new_episode:
            episode = Episode()
            episode.episode_number = episode_number
            self.episodes.append(episode)

        episode.add_file(file)

        if episode_number > self.last_episode_torrent:
            self.last_episode_torrent = episode_number

        return episode_number

    def get_file(self, type : str):
        for file in self.get_files_current_episode():
            if type == file.type:
                if type == "subtitle" and self.subtitle_group == file.group:
                    return file
                elif type == "voice" and self.audio_group == file.group:
                    return file
                return file

        raise ValueError("{} file not found: {}".format(type.title(), self.topic))

    def reset_files(self):
        self.episodes = list()
        self.fonts = list()

    def _get_groups(self, type):
        groups = list()
        for file in self.get_files():
            if file.type == type and file.group not in groups:
                groups.append(file.group)
        return groups

    def get_subtitle_groups(self):
        return self._get_groups("subtitle")

    def get_audio_groups(self):
        return self._get_groups("audio")

    def add_episode(self, episode : Episode):
        self.episodes.append(episode)

    def get_episode(self, episode_number):
        for ep in self.episodes:
            if ep.episode_number == episode_number:
                return ep
        raise ValueError(f'Episode {episode_number} not found')
