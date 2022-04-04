import io
import mpv
from subprocess import Popen, PIPE

def log_handler(level, prefix, text):
    print("PLAYER: ", level, prefix, text)

class Player():
    def __init__(self):
        self.player = mpv.MPV(log_handler=log_handler, input_default_bindings=True, input_vo_keyboard=True, osc=True)

    # in seconds
    def _time_to_return_code(self, position, duration):
        return 0 if (duration - position < 100) else 1

    # 00:00:06 -> 6 secs
    def _string_to_seconds(self, string):
        ftr = [3600,60,1]
        return sum([a * b for a, b in zip(ftr, map(int, string.split(':')))])

    def play(self, file, subtitles=None):
        # process = Popen(['mpv', file, "--term-status-msg='${time-pos} / ${duration}'"], stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True)
        process = Popen(['mpv', file, "--term-status-msg=${time-pos} / ${duration}"], stdout=PIPE, stderr=PIPE, universal_newlines=True)
        # stdout, stderr = process.communicate()
        # while True:
            # out = process.stdout.read(20)
            # print(out)
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
