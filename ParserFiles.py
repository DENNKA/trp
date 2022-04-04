import re
from pathlib import Path
from collections import defaultdict

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
                       ["fonts" for i in range(len(self.font_extensions))] +
                       ["fonts" for i in range(len(self.picture_extensions))] # FIXME: "fonts"
                       )
            self.extension_dict = dict(zip1)

            self.subtitles_folder_names = ['sub']

            return val

class ParserFiles(SingletonForParserFiles):
    def __init__(self):
        pass

    def get_type(self, path : str):
        try:
            return self.extension_dict[Path(path).suffix.lstrip('.').lower()]
        except KeyError:
            return "fonts" # FIXME: "fonts"

    def files_to_episodes(self, files, root, data=None):
        """
        files: list of files (TORRENT_NAME/file1)
        root: torrent download location (/disk/TORRENTS_FOLDER)
        data: list data. Replacing path with data (path[i] = data[i])
        Returns dict (path is joined root and file path)
        {
            episode_number : { video : path, subtitle : { group_name1 : path, group_name2 : path }, audio : path }
            fonts : { group_name1 : [path1, path2], group_name2 : [path1, path2] }
        }
        """
        paths = [Path(file) for file in files]
        root_anime = Path(root) / Path(paths[0].parts[0])
        files_dict = defaultdict(lambda: defaultdict(list))

        subtitles_folders = [x for x in root_anime.iterdir() if x.is_dir()  # folders
                             and len([name for name in self.subtitles_folder_names if(name in str(x).lower())])]  # folder contains self.subtitles_folder_names

        subtitle_in_folder = 1 if len(subtitles_folders) else 0

        for i, path in enumerate(paths):
            file_type = self.extension_dict[path.suffix.lstrip('.').lower()]
            if data is None:
                append_data = str(root / path)
            else:
                append_data = data[i]
            if file_type != "fonts":
                if str(path).lower().find("creditless") != -1:
                    files_dict["creditless"][str(Path(*path.parts[1:]))] = append_data
                    continue
                file_episode = int(re.search(r'\d+', path.stem).group())
                if file_type == "subtitle":
                    try:
                        files_dict[file_episode][file_type][str(Path(*path.parts[1 + subtitle_in_folder:-1]))] = append_data
                    except TypeError:
                        files_dict[file_episode][file_type] = defaultdict()
                        files_dict[file_episode][file_type][str(Path(*path.parts[1 + subtitle_in_folder:-1]))] = append_data
                        pass
                else:
                    files_dict[file_episode][file_type] = append_data
            else:
                files_dict[file_type][str(Path(*path.parts[1 + subtitle_in_folder:-2]))].append(str(root / path))

        files_dict['first_episode'] = min(filter(lambda e: isinstance(e, int), files_dict.keys()))

        return files_dict
