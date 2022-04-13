import sys
import tempfile
from Anime import Anime
sys.path.append("trp")
from TorrentClient import TorrentClients
import configparser
import pytest


cfg = configparser.ConfigParser()
cfg.read("settings.cfg")
@pytest.mark.parametrize(
        ('torrent_client'), [(x) for x in TorrentClients(cfg, None).get_all_classes(False)])
@pytest.mark.high_dependency()
class TestTorrentClient:
    def test_add_update_remove_torrent(self, torrent_client):
        anime = Anime()
        try:
            with tempfile.TemporaryDirectory() as tempdir:
                anime.hash = torrent_client.add_torrent("./trp/tests/test.torrent", tempdir)
                assert anime.hash
                errors = torrent_client.update_files(anime)
                for error in errors:
                    raise error
        except Exception:
            raise
        finally:
            torrent_client.remove_torrent(anime.hash)
