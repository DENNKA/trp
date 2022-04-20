import re
import anitopy
from pathlib import Path
from collections import defaultdict

import Episode

import logging
logger = logging.getLogger(__name__)

class SingletonForParserFiles(object):
    def __new__(self, *args, **kwargs):
        try:
            return self._instance
        except AttributeError:
            val = self._instance = object.__new__(self, *args, **kwargs)

            self.video_extensions = ['mkv', 'avi', 'mp4']
            self.subtitle_extensions = ['ass', 'srt']
            self.audio_extensions = ['mka', 'ac3']
            self.font_extensions = ['ttf', 'ttc', 'otf']
            self.picture_extensions = ['jpg', 'jpeg', 'png']

            zip1 = zip(self.video_extensions + self.subtitle_extensions + self.audio_extensions + self.font_extensions + self.picture_extensions,
                       ["video" for i in range(len(self.video_extensions))] +
                       ["subtitle" for i in range(len(self.subtitle_extensions))] +
                       ["audio" for i in range(len(self.audio_extensions))] +
                       ["fonts" for i in range(len(self.font_extensions))]
                       )
            self.extension_dict = dict(zip1)

            self.subtitles_folder_names = ['sub', 'subs', 'субтитры']

            return val

class CantParseEpisodeNumber(Exception):
    def __init__(self, file):
        super().__init__("Can't parse episode number " + str(file))

class ParserFiles(SingletonForParserFiles):
    def __init__(self):
        self.exceptions = []

    def get_type(self, path : Path):
        try:
            return self.extension_dict[path.suffix.lstrip('.').lower()]
        except KeyError:
            return "unknown"

    def _find_episode_number(self, path : Path):
        parsed = anitopy.parse(path.name)
        try:
            return int(parsed['episode_number'].lstrip('0'))
        except Exception as e:
            logger.warning(f'WARNING: use secondary parse method, file: {str(path)}')
            logger.debug(str(e))
            try:
                return int(re.search(r"\b(?:e(?:p(?:isode)?)?|0x|S\d\dEP?)?\s*?(\d{1,4})\b", path.name, re.IGNORECASE).group(1))
            except Exception as e:
                logger.error("Can't parse episode number " + str(e))
                raise CantParseEpisodeNumber(path)

    def _get_subtitles_folders(self, paths : list):
        subtitles_folders = [x.parts[1:-1] for x in paths if Path(x.parts[1]).suffix == ""  # folders
                             and len([name for name in self.subtitles_folder_names if(name in str(x.parts[1]).lower())])]  # folder contains self.subtitles_folder_names
        return subtitles_folders

    def _detect_extra(self, path : Path):
        bool = any(x in str(path).lower() for x in ["creditless", "bonus", "extra", "special"]) # ! only lower case
        if bool:
            return bool
        return any(x.lower() in ["nc"] for x in path.parts) # ! only lower case

    def parse(self, files : list, root : str):
        """
        files: list of files (TORRENT_NAME/file1)
        root: torrent download location (/disk/TORRENTS_FOLDER)
        return list(Episode()) - episodes, list(File()) - fonts, first episode, last episode
        """

        self.exceptions = []

        episodes = defaultdict(Episode.Episode)
        fonts = list()

        paths = [Path(file.path) for file in files]
        # root_anime = Path(root) / Path(paths[0].parts[0])
        # files_dict = defaultdict(lambda: defaultdict(list))

        # subtitles_folders = self._get_subtitles_folders(paths)

        # subtitle_in_folder = 1 if len(subtitles_folders) else 0
        subtitle_in_folder = 0

        for path, file in zip(paths, files):
            file.type = self.get_type(path)
            if file.type != "fonts":
                if self._detect_extra(path):
                    file.group = str('/'.join(path.parts[1:])).rstrip('.')
                    episodes[-1].add_file(file)
                    continue

                try:
                    file_episode = self._find_episode_number(path)
                except CantParseEpisodeNumber as e:
                    self.exceptions.append(e)
                    episodes[-1].add_file(file)
                    continue

                if file.type == "subtitle":
                    file.group = str('/'.join(path.parts[1 + subtitle_in_folder:-1])).rstrip('.')
                    episodes[file_episode].add_file(file)
                else:
                    episodes[file_episode].add_file(file)
            else:
                file.group = str('/'.join(path.parts[1 + subtitle_in_folder:-2])).rstrip('.')
                episodes[0].add_file(file)
                fonts.append(file)

        for episode_number, episode in episodes.items():
            episode.episode_number = episode_number

        first_episode = min(filter(lambda e: isinstance(e, int) and e > 0, episodes.keys()))
        last_episode = max(filter(lambda e: isinstance(e, int) and e > 0, episodes.keys()))

        return list(episodes.values()), fonts, first_episode, last_episode, self.exceptions

if __name__ == "__main__":
    import pickle
    pf = ParserFiles()
    with open('add_files.pkl', 'rb') as f:
        x = pickle.load(f)
    episodes, fonts, first_episode, last_episode, errors = pf.parse(x[0], x[1])
    for episode in episodes:
        print([f'{x.path} - {x.group.upper()}' for x in episode.files], episode.episode_number)
    for error in errors:
        print(error)
    print([x.path for x in fonts])
    print(first_episode, last_episode)
