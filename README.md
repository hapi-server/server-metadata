
* `abouts.py` updates `abouts.json` by overwriting what is found in https://github.com/hapi-server/server/about.json
* `catalogs.py` reads all `/info` responses from all servers in `abouts.json`. Output is stored at `https://hapi-server.org/meta/catalogs` and `https://hapi-server.org/meta/infos`.
* `availability.py` creates availability plots and html in https://hapi-server.org/meta/infos.

See `etc/crontab.sh` for commands that are executed to do all of the above.