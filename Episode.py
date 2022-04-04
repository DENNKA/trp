from DbElement import DbElement
from File import File

class Episode(DbElement):
    def __init__(self, files = list(), args = None):

        self.files = list()

        self.id = -1
        self.anime_id = -1
        self.episode_number = 0

        if args is not None:
            self.set_with_dict(args)

    def add_file(self, file : File):
        self.files.append(file)

    def set_priority(self, priority : int):
        for file in self.files:
            file.priority = priority
