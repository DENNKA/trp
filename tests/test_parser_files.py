from pathlib import Path
import sys
sys.path.append(".")
import ParserFiles
import File
import pytest
import json

class TestParserFiles:
    def setup_class(self):
        self.parser_files = ParserFiles.ParserFiles()

    def test_find_episode_number(self):
        tests = [
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 01 [13] (BD 1920x1080 x.264 Flac).mkv", 1],
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 12 [24] END (BD 1920x1080 x.264 FLACx2).ass", 12],
                    ["Anime S01EP01.mkv", 1],
                    ["Anime S01EP10.mkv", 10],
                    ["Anime S01EP1.mkv", 1],
                    ["Anime S01E01.mkv", 1],
                    ["Anime S01E1.mkv", 1],
                    ["Anime S01E10.mkv", 10],
                ]
        for path, ep in tests:
            assert self.parser_files._find_episode_number(Path(path)) == ep

    def test_get_type(self):
        tests = [
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 01 [13] (BD 1920x1080 x.264 Flac).mkv", "video"],
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 12 [24] END (BD 1920x1080 x.264 FLACx2).ass", "subtitle"],
                ]
        for path, type_name in tests:
            assert self.parser_files.get_type(Path(path)) == type_name

    def test_detect_extra(self):
        tests = [
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 01 [13] (BD 1920x1080 x.264 Flac).mkv", False],
                    ["Tokyo Ghoul Re (Сезон 4)/[Moozzi2] Tokyo Ghoul Re S2 Saishuushou - 12 [24] END (BD 1920x1080 x.264 FLACx2).ass", False],
                    ["Tokyo Ghoul Re (Сезон 4)/EXTRA/[Moozzi2] Tokyo Ghoul Re S2 [SP07] Parabellum MV (BD 1920x1080 x.264 Flac).mkv", True],
                ]
        for path, bool in tests:
            assert self.parser_files._detect_extra(Path(path)) == bool

    def test_parse(self):
        files = [
                    "Super Anime [1080p]/Super Anime 01 [1080].mkv",
                    "Super Anime [1080p]/Super Anime 01 [1080].ass",
                    "Super Anime [1080p]/Super Anime 10 [1080].mkv",
                    "Super Anime [1080p]/Super Anime 10 [1080].ass",
                ]
        files = [File.File(vars={'path':x}) for x in files]
        root = "/this/is/root"
        episodes, fonts, first, last, errors = self.parser_files.parse(files, root)
        for error in errors:
            raise error
        assert first == 1
        assert last == 10
        assert fonts == []
        assert episodes[0].episode_number == 1
        assert episodes[1].episode_number == 10
        assert episodes[0].files[0] == files[0] and episodes[0].files[1] == files[1]
        assert episodes[1].files[0] == files[2] and episodes[1].files[1] == files[3]

    def test_parse_with_subtitles(self):
        tests = [
                    ["Super Anime [1080p]/Ru subs/Super Group/signs/Super anime 01.ass", "Ru subs/Super Group/signs"],
                    ["Super Anime [1080p]/Ru subs/Super Group/Super anime 01.ass", "Ru subs/Super Group"],
                    ["Super Anime [1080p]/Ru subs/Awesome Group/Super anime 01.Awesome Group.ass", "Ru subs/Awesome Group"],
                    ["Super Anime [1080p]/Ru subs/Awesome Group/fonts/Super awesome font.otf", "Ru subs/Awesome Group"],
                    ["Super Anime [1080p]/Ru subs/signs/Super anime 01.ass", "Ru subs/signs"],
                    ["Super Anime [1080p]/Ru subs/Super anime 01.ass", "Ru subs"],
                    ["Super Anime [1080p]/Ru subs/fonts/Awesome font.ttf", "Ru subs"],
                    ["Super Anime [1080p]/fonts/Super Font.ttf", ""],
                    ["Super Anime [1080p]/Super anime 01.ass", ""],
                    ["Super Anime [1080p]/Super anime 01.mkv", ""],
                ]
        files = [File.File(vars={'path':x[0]}) for x in tests]
        root = "/this/is/root"
        episodes, fonts, first, last, errors = self.parser_files.parse(files, root)
        for error in errors:
            raise error
        assert first == 1 and last == 1
        assert len(episodes) == 2
        assert len(fonts) == 3
        for episode in episodes:
            for file in episode.files:
                for test in tests:
                    if file.path in test[0]:
                        assert file.group == test[1]
                        break
