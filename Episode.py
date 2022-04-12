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

    def set_priority(self, priority : int, groups = None):
        # groups : list()
        for file in self.files:
            if groups == None or file.group in groups:
                file.priority = priority

    def get_files_from_type(self, type_name):
        files = []
        for file in self.files:
            if file.type == type_name:
                files.append(file)
        return files
