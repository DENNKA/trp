from shikimori_api import Shikimori
import oauthlib

import requests
import json
import os.path

from ListClass import ListClass

def token_saver(token: dict):
    with open('token.json', 'w') as f:
        f.write(json.dumps(token))


class AnimeList():
    def __init__(self):
        self.inited = False

    def init(self, cfg):
        if self.inited: return
        self.client_id = cfg['shikimori']['client_id']
        self.client_secret = cfg['shikimori']['client_secret']
        self._login()
        self.api = self.s_session.get_api()
        self.inited = True

    def _login(self, force_token=False):
        if not os.path.isfile('token.json') or force_token:
            self.s_session = Shikimori("trp", client_id=self.client_id, client_secret=self.client_secret, token_saver=token_saver)
            print("Go to link and write code to console ", self.s_session.get_auth_url())
            code = input('Authorization Code: ')
            self.s_session.fetch_token(code)
        with open('token.json') as f:
            token = json.load(f)
        self.s_session = Shikimori("trp", client_id=self.client_id, client_secret=self.client_secret, token=token)

    def _get_user_rate_id(self, id_anime, episodes=0):
        try_n = 2
        while (try_n):
            if os.path.isfile('shikimori.json'):
                data = self._load()
                user_id = data[0]
                for rate in data[1]:
                    if rate['target_id'] == id_anime:
                        return rate['id']
            else:
                user_id = self.api.users.whoami.GET()['id']
            if (try_n == 1):
                break
            self._save([user_id, self.api.user_rates.GET(user_id=user_id)])
            try_n -= 1

        return self.api.user_rates.POST(user_id=user_id, episodes=episodes, target_type="Anime", target_id=id_anime)['id']

    def _load(self):
        with open('shikimori.json') as f:
            data = json.load(f)
        return data

    def _save(self, data):
        with open('shikimori.json', 'w') as f:
            f.write(json.dumps(data))

    def search(self, search, kind=None):
        return self.api.animes.GET(search=search, kind=kind)

    def mark_one(self, id_anime, episodes=1):
        retry = 2
        while retry:
            try:
                self.api.user_rates(self._get_user_rate_id(id_anime, episodes - 1)).increment.POST()
            except oauthlib.oauth2.rfc6749.errors.InvalidGrantError as e:
                print("InvalidGrantError")
                print(e)
                self._login(force_token=True)
            finally:
                retry -= 1

class AnimeLists(ListClass):
    def __init__(self, cfg):
        self.cfg = cfg
        self.classes = {
                'Shikimori': Shikimori(),
                }
