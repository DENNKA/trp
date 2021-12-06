from qbittorrent import Client
import os
import re
import time


class Torrent():
    def __init__(self, server, username, password, download_dir, default_reserve):
        self.qb = Client(server)

        response = self.qb.login(username, password)
        if response != "Ok." and response is not None:
            raise(RuntimeError("Login " + response))
        self.download_dir = download_dir
        self.default_reserve = default_reserve

        self.video_extensions = ['mkv', 'avi', 'mp4']
        self.subtitle_extensions = ['ass', 'srt']
        self.font_extensions = ['ttf', 'otf']

    def _add_file(self, file):
        torrent_file = open(file, 'rb')
        self.qb.download_from_file(torrent_file, savepath=self.download_dir, category="trp", paused=True, sequentialDownload=False, firstLastPiecePrio=False)
        self.wait(3)

    def add_torrent(self, file):

        self._add_file(file)

        hash = self.get_last_torrent_hash()

        files = self.qb.get_torrent_files(hash)

        files_ids_not_subtitles = [item['index'] for item in files if item['index'] not in self.get_ids_subtitles(hash)]
        for id in files_ids_not_subtitles:
            self.qb.set_file_priority(hash, id, 0)
            self.wait()

        self._priority_all_needed(hash)

        return hash

    def get_files_paths(self, hash):
        return [x['name'] for x in self.qb.get_torrent_files(hash)]

    def is_available(self, hash, piece_start, piece_end, piece_size, bytes_start, bytes_end):
        pieces = self.qb.get_torrent_piece_states(hash)
        check_start = int(piece_start + (bytes_start / piece_size))
        check_end = min(int(piece_start + (bytes_end / piece_size)), piece_end)
        print(piece_start, piece_end, piece_size)
        print(bytes_start, bytes_end)
        for i in range(check_start, check_end):
            print(pieces[i], end=" ")
        print()
        for i in range(check_start, check_end):
            if (pieces[i] != 2):
                return False
        return True

    def _get_seq_dl(self, hash):
        for torrent in self.qb.torrents():
            if torrent['hash'] == hash:
                return [torrent['seq_dl'], torrent['f_l_piece_prio']]
        return ValueError("Torrent not found: " + hash)

    def enable_sequential_download(self, hash):
        seq_dl = self._get_seq_dl(hash)
        if seq_dl[0] == False:
            self.qb.toggle_sequential_download(hash)
        if seq_dl[1] == False:
            self.qb.toggle_first_last_piece_priority(hash)

    def disable_sequential_download(self, hash):
        seq_dl = self._get_seq_dl(hash)
        if seq_dl[0] == True:
            self.qb.toggle_sequential_download(hash)
        if seq_dl[1] == True:
            self.qb.toggle_first_last_piece_priority(hash)

    def get_files_data(self, hash):
        return self.qb.get_torrent_files(hash)

    def get_piece_size(self, hash):
        return self.qb.get_torrent(hash)['piece_size']

    def get_root(self, hash):
        return self.qb.get_torrent(hash)['save_path']

    def _priority_all_needed(self, hash):
        ids = self.get_ids_subtitles(hash) + self.get_ids_fonts(hash)
        self._priority_files(hash, ids, [7 for i in range(0, len(ids))])

    def get_ids_fonts(self, hash):
        ids = []  # TODO: need change this shit
        for file in self.qb.get_torrent_files(hash):
            #if file['name']
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if extension.lstrip('.') in self.font_extensions:
                ids.append(file['index'])
        return ids

    def get_episode_path(self, hash, episode):
        for file in self.qb.get_torrent_files(hash):
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if len(file_path) == 1 and extension.lstrip('.') in self.video_extensions:
                if int(re.search(r'\d+', filename).group()) == episode:
                    return os.path.join(*file_path)

    def get_subtitle_path(self, hash, episode):
        subtitle_paths = []
        for file in self.qb.get_torrent_files(hash):
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if extension.lstrip('.') in self.subtitle_extensions:
                if int(re.search(r'\d+', filename).group()) == episode:
                    subtitle_paths.append(os.path.join(*file_path))
        return subtitle_paths

    def get_ids_subtitles(self, hash):
        ids = []
        for file in self.qb.get_torrent_files(hash):
            #if file['name']
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if extension.lstrip('.') in self.subtitle_extensions:
                ids.append(file['index'])


        return ids


    def get_ids_episodes(self, hash):
        ids = {}
        for file in self.qb.get_torrent_files(hash):
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if len(file_path) == 1 and extension.lstrip('.') in self.video_extensions:
                ids[int(re.search(r'\d+', filename).group())] = file['index']
        return ids

    def get_progress_episodes(self, hash):
        ids = {}  # ctrl c and v
        for file in self.qb.get_torrent_files(hash):
            file_path = file['name'].split('/')[1:]
            filename, extension = os.path.splitext(file_path[-1])
            if len(file_path) == 1 and extension.lstrip('.') in self.video_extensions:
                ids[int(re.search(r'\d+', filename).group())] = file['progress']
        return ids

    def get_last_torrent_hash(self):
        return self.qb.torrents(sort="added_on", reverse=True, limit=1)[0]['hash']

    def _priority_files(self, hash, files, priorities):
        for file, priority in zip(files, priorities):
            self.qb.set_file_priority(hash, file, priority)
            self.wait()

    def get_torrent_path(self, hash):
        #return self.qb.get_torrent(hash)['save_path']
        dict = self.qb.sync_main_data()
        path = dict['torrents'][hash]['content_path']
        return path

    def get_last_episode(self, hash):
        ids = self.get_ids_episodes(hash)
        return max(list(ids.keys()))

    def _priority_to_qbittorrent(self, priorities):
        # 0 1 2 3 -> 0 1 6 7
        return [6 if priority == 2 else 7 if priority == 3 else priority for priority in priorities]

    def load_episodes(self, hash, episodes, priorities):
        ids = self.get_ids_episodes(hash)
        self._priority_files(hash, [ids[x] for x in episodes], self._priority_to_qbittorrent(priorities))

    def replace_torrent(self, hash, torrent_file):
        prev_files = self.qb.get_torrent_files(hash)

        prev_names = []
        prev_priorities = []
        for i, file in enumerate(prev_files):
            prev_names.append(file['name'])
            prev_priorities.append(file['priority'])

        self.remove_torrent(hash)
        self._add_file(torrent_file)

        new_hash = self.get_last_torrent_hash()

        files = self.qb.get_torrent_files(new_hash)
        for file in files:
            try:
                priority = prev_priorities[prev_names.index(file['name'])]
            except ValueError:
                priority = 0
            print(priority)
            self._priority_files(new_hash, [file['index']], [priority])

        self._priority_all_needed(hash)

        return new_hash

    def remove_torrent(self, hash):
        self.qb.delete(hash)
        self.wait(3)

    def resume(self, hash):
        self.qb.resume(hash)

    def delete_episode(self, episode):
        None

    def wait(self, seconds=1):
        time.sleep(seconds)
