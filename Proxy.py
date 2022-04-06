from proxyscrape import create_collector
import requests

class Proxy():
    def __init__(self, cfg):
        self.cfg = cfg
        self.collector = create_collector('a', 'http')

    def get_proxy(self, class_name):
        if class_name != type(str()):
            class_name = type(class_name).__name__
        proxy = None
        try:
            proxy = self.cfg['trp']['proxy']
        except Exception:
            pass
        try:
            proxy = self.cfg[class_name]['proxy']
        except Exception:
            pass

        if not proxy:
            return None
        if proxy.find("pool://") != -1:
            proxy = requests.get(self.proxy.replace("pool://", "")).text
            return proxy
        if proxy == "auto":
            proxy = self.collector.get_proxy()
            return f'{proxy.type}://{proxy.host}:{proxy.port}'
        return proxy
