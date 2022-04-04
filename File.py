from DbElement import DbElement

from ParserFiles import ParserFiles

import os
import re

class File(DbElement):
    def __init__(self, path = "", type_id = -1, group = "", vars = None):
        self.id = -1
        self.episode_id = -1
        self.torrent_file_id = -1
        self.path = path
        self.type_id = type_id
        self.group = group
        self.type = ""
        self.priority = 2
        self.progress = 0
        self.size = 0
        self.piece_range = [0, 0] # inclusive
        self.availability = 0

        if vars is not None:
            self.set_with_dict(vars)

    def update(self):
        if not self.path:
            ValueError("Path empty")

        self.type = self._extract_type(self.path)
        self.group = self._extract_group(self.path)

    def _get_extension(self, path):
        filename, file_extension = os.path.splitext(path)
        return file_extension, filename

    def _extract_type(self, path):
        return ParserFiles().get_type(path)

    def _extract_group(self, path):
        # if len path.parts > 2 -> in folder
        return ""

