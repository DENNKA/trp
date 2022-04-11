from DbElement import DbElement

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
        pass
