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

If you want use proxy setup settings.cfg:  
add `proxy = http://PROXY:PORT` to [trp] for entire application (proxy for client and animelist is not implemented yet) or to specific module (for example [Rutracker]).  
Also supported proxy from pool (e. g. `pool://http://127.0.0.1:8000/proxy`)

### Update
```
git pull
# migrate try to update database schema (if database not changed it's not necessary)
# always backup database before migrate!
cp anime.db anime.db.backup
python trp/trp.py --console --migrate
# no output is ok
```

## Console usage

```
usage: trp.py [-h] [--add ADD] [--watch WATCH] [--update] [--find] [--migrate] [--port PORT]
              [--console]

Torrent player

options:
  -h, --help     show this help message and exit
  --add ADD      Search anime on tracker contains in topic WORD1 and WORD2...
  --watch WATCH  Watch anime contains in topic WORD1 and WORD2...
  --update       Manual update
  --find         Find new episodes
  --migrate      Migrate from old database to new
  --port PORT    Stream server port
  --console      Console mode

```

### Examples

Add anime "Mirai nikki" (you get table in console (on windows use normal console emulator) type number what anime you want to add)  
```python3.8 trp.py --console --add "Mirai nikki"```

Watch anime interactive (you get list anime, type number what anime you want to watch)  
```python3.8 trp.py --console --watch manual```

Watch anime "Mirai nikki" (if result 2+ you got a list)  
```python3.8 trp.py --console --watch "Mirai nikki"```

Try to find new episodes on tracker  
```python3.8 trp.py --console --find```

## Bugs
Open issue if you find bug also you can try to fix it by yourself. Some bugs can fixed by editing anime.db (sqlite)
