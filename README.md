# trp

Torrent player focused on anime. Works with qbittorrent, mpv, and rutracker

## Install

```
pip3 install -r requirements.txt
# if you want to use socks (tor)
pip3 install requests[socks]

git clone --recurse-submodules https://github.com/DENNKA/trp.git
```

Install Qbittorrent and enable in settings webUI  

### Setup

Replace ALL UPPER CASE words in settings.cfg with yours fields.  
ID of forum you can get in search url with selected forum on tracker (for example in search ...cker.php?f=1105&nm=YOUR+SEARCH+QUERY forum id is 1105)

## Usage

```
usage: trp.py [-h] [--add ADD] [--watched WATCHED] [--watch WATCH] [--proxy PROXY] [--update] [--find]

Torrent player

optional arguments:
  -h, --help         show this help message and exit
  --add ADD          Search anime on tracker contains in topic WORD1 and WORD2...
  --watched WATCHED  Watched series of added anime
  --watch WATCH      Watch anime contains in topic WORD1 and WORD2...
  --proxy PROXY      Proxy, use auto for auto provided proxy, use socks5://127.0.0.1:9150 for tor
  --update           Manual update
  --find             Find new episodes

```

### Examples

Add anime "Mirai nikki" with tor as proxy (you get table in console (on windows use normal console emulator) type number what anime you want to add)  
```python3.8 trp.py --add "Mirai nikki" --proxy socks5://127.0.0.1:9150```

Watch anime interactive (you get list anime, type number what anime you want to watch)  
```python3.8 trp.py --watch manual```

Watch anime "Mirai nikki" (if result 2+ you got a list)  
```python3.8 trp.py --watch "Mirai nikki"```

Try to find new episodes on tracker  
```python3.8 trp.py --find```

## Bugs
Open issue if you find bug also you can try to fix it by yourself. Some bugs can fixed by editing anime.db (sqlite)
