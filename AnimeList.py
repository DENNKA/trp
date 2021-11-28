from shikimori_api import Shikimori

import requests
import json
import os.path


def token_saver(token: dict):
    with open('token.json', 'w') as f:
        f.write(json.dumps(token))


class AnimeList():
    def __init__(self, client_id, client_secret):
        if not os.path.isfile('token.json'):
            self.s_session = Shikimori("trp", client_id=client_id, client_secret=client_secret, token_saver=token_saver)
            print("Go to link and write code to console ", self.s_session.get_auth_url())
            #print("Go to link and write code to console ", "https://shikimori.one/oauth/authorize?client_id={}&redirect_uri={}&response_type=code&scope=".format(client_id, "urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob"))
            code = input('Authorization Code: ')
            #token_url = 'https://shikimori.one/oauth/token'
            #body = {'grant_type' : 'authorization_code',
            #        'client_id' : client_id,
            #        'client_secret' : client_secret,
            #        'code' : code,
            #        }
            #headers = {'User-Agent': 'trp'}

            #r = requests.post(token_url, data=json.dumps(body), headers=headers)
            #print(r.text)
            self.s_session.fetch_token(code)
        with open('token.json') as f:
            token = json.load(f)
        #print(token)
        self.s_session = Shikimori("trp", client_id=client_id, client_secret=client_secret, token=token)
        self.api = self.s_session.get_api()
        #endpoint = "https://shikimori.one/api/v2/user_rates/47790/increment"
        #data = {"ip": "1.1.2.3"}
        #headers = {"Authorization": "Bearer " + token['access_token'], "User-Agent" : "trp"}
        #print(requests.post(endpoint, headers=headers).json())
        #self._load()
        #a = self.api.user_rates.GET(user_id=318989)
        #self._save([318989, a])
        #print(a)

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
        self.api.user_rates(self._get_user_rate_id(id_anime, episodes - 1)).increment.POST()
