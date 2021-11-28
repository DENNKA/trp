import mpv

def log_handler(level, prefix, text):
    print("PLAYER: ", level, prefix, text)

class Player():
    def __init__(self):
        self.player = mpv.MPV(log_handler=log_handler, input_default_bindings=True, input_vo_keyboard=True, osc=True)

    def play(self, file, subtitles=None):
        self.player.play(file)
        self.player.wait_until_playing()
        self.player.sub_add(subtitles)
        try:
            self.player.wait_for_playback()
        except mpv.ShutdownError:
            return 1
        except Exception as e:
            print(e)
            return 1
        else:
            return 0
