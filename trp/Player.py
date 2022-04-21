import io
from subprocess import Popen, PIPE

class Player():
    def __init__(self):
        pass

    # in seconds
    def _time_to_return_code(self, position, duration):
        return 0 if (duration - position < 100) else 1

    # 00:00:06 -> 6 secs
    def _string_to_seconds(self, string):
        ftr = [3600,60,1]
        return sum([a * b for a, b in zip(ftr, map(int, string.split(':')))])

    def play(self, server_address, video_file, subtitle_file=None, audio_file=None):
        cmd = ['mpv', server_address + video_file.path, "--term-status-msg=${time-pos} / ${duration}"]
        subtitle_cmd = [f'--sub-file={server_address + subtitle_file.path}'] if subtitle_file else []
        audio_cmd = [f'--audio-file={server_address + audio_file.path}'] if audio_file else []
        process = Popen(cmd + subtitle_cmd + audio_cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        error = 1
        while True:
            line = process.stderr.readline()
            if not line: break
            if line == '\n' or line == '\r': continue
            splits = [x.strip().replace("\x1b[K", "") for x in line.split('/')]
            try:
                if len(splits) > 1:
                    error = self._time_to_return_code(self._string_to_seconds(splits[0]), self._string_to_seconds(splits[1]))
            except ValueError:
                pass

        return error
