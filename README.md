This repository contains code that requests all metadata from all HAPI servers daily.

* `abouts.py` updates [abouts.json](https://github.com/hapi-server/servers/blob/master/abouts.json) file, which contains information for servers that do not support the `/about` endpoint.

* `catalogs.py` reads `/catalog` responses (which contain a list of datasets) from each server in `abouts.json`. The `/info` response for each dataset is then requested. Output is stored at `https://hapi-server.org/meta/catalogs` and `https://hapi-server.org/meta/infos`.

* `availability.py` creates dataset availability plots and html in https://hapi-server.org/meta/infos based on the `{start,stop}Date` found in the dataset `/info` responses.

See `etc/crontab.sh` for commands that are executed for the above.