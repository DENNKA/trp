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

    def play(self, file, subtitles=None):
        process = Popen(['mpv', file, "--term-status-msg=${time-pos} / ${duration}"], stdout=PIPE, stderr=PIPE, universal_newlines=True)
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
