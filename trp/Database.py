import sqlite3
import os

from Anime import Anime
from Episode import Episode
from File import File

class Database:
    def __init__(self):
        table_exist = os.path.isfile("anime.db")
        self.conn = sqlite3.connect("anime.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        if not table_exist:
            self.create_table()

    # for class only
    def _get_name(self, class1):
        return class1.__class__.__name__.lower()

    def _add_quotes(self, l : list):
        return ["'" + x + "'" for x in l]

    def _update_row(self, update_class):
        class_name = self._get_name(update_class)
        self.cursor.execute("select * from {} limit 1".format(class_name))
        columns = [i[0] for i in self.cursor.description if i[0] != 'id']
        vars = list()
        for column in columns:
            vars.append(update_class.get_variable(column))

        sql = ""
        try:
            if update_class.id == -1:
                sql = 'INSERT INTO {} ({}) VALUES ({})'.format(class_name, ', '.join(self._add_quotes(columns)), ', '.join(['?' for _ in range(len(vars))]))
                self.cursor.execute(sql, vars)
                update_class.id = self.cursor.lastrowid
            else:
                sql = 'UPDATE {} SET ({}) = ({}) WHERE id = ?'.format(class_name, ', '.join(self._add_quotes(columns)), ', '.join(['?' for _ in range(len(vars))]))
                self.cursor.execute(sql, vars + [update_class.id])
        except Exception as e:
            print(sql)
            print(vars, update_class.id)
            raise

    def update_anime(self, anime : Anime):
        anime.update()
        self._update_row(anime)
        for episode in anime.episodes:
            episode.anime_id = anime.id
            self._update_row(episode)
            for file in episode.files:
                file.episode_id = episode.id
                self._update_row(file)
        self.conn.commit()

    def remove_anime(self, anime : Anime):
        sql = "DELETE FROM anime WHERE id=?"
        self.cursor.execute(sql, [anime.id])
        sql = "SELECT id FROM episode WHERE anime_id=?"
        self.cursor.execute(sql, [anime.id])
        episodes_id = [x['id'] for x in self.cursor.fetchall()]
        sql = "DELETE FROM episode WHERE anime_id=?"
        self.cursor.execute(sql, [anime.id])
        for episode_id in episodes_id:
            sql = "DELETE FROM file WHERE episode_id=?"
            self.cursor.execute(sql, [episode_id])
        self.conn.commit()

    # def get_anime(self):
    #     sql = "SELECT * FROM anime ORDER BY id DESC"
    #     self.cursor.execute(sql)
    #     self.conn.commit()
    #     return self.cursor.fetchall()

    def get_animes_by_name(self, name):
        words = name.split(" ")
        sql = """SELECT * FROM anime WHERE topic LIKE '%""" + """%' AND topic LIKE '%""".join(words) + """%' COLLATE NOCASE"""
        self.cursor.execute(sql)
        self.conn.commit()
        animes = self.cursor.fetchall()
        columns = [i[0] for i in self.cursor.description]
        animes_out = list()
        for anime in animes:
            anime_out = Anime(dict(zip(columns, anime)))
            self._get_episodes(anime_out)
            animes_out.append(anime_out)
        return animes_out

    def get_anime(self, id):
        sql = "SELECT * FROM anime WHERE id = ?"
        self.cursor.execute(sql, [id])
        anime = self.cursor.fetchall()[0]
        columns = [i[0] for i in self.cursor.description]
        self.conn.commit()
        anime = Anime(dict(zip(columns, anime)))
        self._get_episodes(anime)
        return anime

    def get_animes_not_finished(self):
        return self.get_animes(where="last_episode_torrent != total_episodes")

    def get_animes(self, where="1"):
        sql = f'SELECT * FROM anime WHERE {where} ORDER BY id DESC'
        self.cursor.execute(sql)
        animes = self.cursor.fetchall()
        columns = [i[0] for i in self.cursor.description]
        self.conn.commit()
        animes_out = list()
        for anime in animes:
            anime_out = Anime(dict(zip(columns, anime)))
            self._get_episodes(anime_out)
            animes_out.append(anime_out)
        return animes_out

    def _get_episodes(self, anime : Anime):
        sql = "SELECT * FROM episode WHERE anime_id=?"
        self.cursor.execute(sql, [anime.id])
        episodes_db = self.cursor.fetchall()
        columns = [i[0] for i in self.cursor.description]
        self.conn.commit()
        for episode_db in episodes_db:
            episode = Episode(args=dict(zip(columns, episode_db)))
            self._get_files(episode)
            anime.add_episode(episode)

    def _get_files(self, episode : Episode):
        # sql = "SELECT * FROM file JOIN files_types ON file.type_id == files_types.id WHERE episode_id = ?"
        sql = "SELECT * FROM file WHERE episode_id = ?"
        self.cursor.execute(sql, [episode.id])
        files_db = self.cursor.fetchall()
        columns = [i[0] for i in self.cursor.description]
        self.conn.commit()
        for file_db in files_db:
            file = File(vars=dict(zip(columns, file_db)))
            episode.files.append(file)

    def _create_table(self, class_type):
        vars_in_class = vars(class_type)
        variables = list()
        for var_name, value in vars_in_class.items():
            extra = "DEFAULT"
            type_value = type(value)
            if (type_value == type(list()) or type_value == type(dict())):
                continue
            type_name = ""
            default_value = value
            if (type_value == type(int())):
                type_name = "INTEGER"
                if (var_name == "date_added"):
                    default_value = "CURRENT_TIMESTAMP"
                    type_name = "DATETIME"
                elif (var_name == "id"):
                    default_value = ""
                    extra = "PRIMARY KEY AUTOINCREMENT"
            elif (type_value == type(str()) or type_value == type(None)):
                type_name = "TEXT"
                default_value = '\'\''
            else:
                raise ValueError("Unknown type: " + str(type_value) + ": " + str(default_value))
            variables.append('"{}" {} {} {}'.format(var_name, type_name, extra, default_value))

        variables = ', '.join(variables)

        class_name = str(class_type.__class__.__name__).lower()

        self.cursor.execute('CREATE TABLE "{}" ({})'.format(class_name, variables))

        self.conn.commit()

    def get_file_type_id(self, type):
        sql = "SELECT id FROM files_types WHERE type=?"
        self.cursor.execute(sql, [type])
        id = self.cursor.fetchone()['id']
        self.conn.commit()
        return id

    def create_table(self):
        self.cursor.execute('CREATE TABLE "files_types" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "type" TEXT DEFAULT "")')
        self.cursor.execute('INSERT INTO "files_types" ("id", "type") VALUES (0, "video"), (1, "subtitle"), (2, "audio")')
        self.conn.commit()
        self._create_table(Anime())
        self._create_table(Episode())
        self._create_table(File())

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
            try:
                self.cursor.execute(sql, list(rowDict.values()))
            except Exception as e:
                print(sql)
                print(list(rowDict.values()))
                raise
        self.conn.commit()
