# About

This repository contains code that requests all metadata from all HAPI servers daily and creates additional metadata and plots. 

* `abouts.py` updates [abouts.json](https://github.com/hapi-server/servers/blob/master/abouts.json), which contains the master list of HAPI servers; see also the [README](https://github.com/hapi-server/servers/) of its repository.

* `catalogs.py` reads `/catalog` responses (which contain a list of datasets) from each server in `abouts.json`. The `/info` response for each dataset from each server is then requested. The catalog response for each server is stored in a subdirectory of [hapi-server.org/meta/catalogs](https://hapi-server.org/meta/catalogs). The `/info` responses for each dataset are stored in a subdirectory of [hapi-server.org/meta/infos](https://hapi-server.org/meta/infos). The file [catalogs-all.json](https://hapi-server.org/meta/catalogs-all.json) contains all `/catalog` and `/info` responses in a single file.

* `availability.py` creates dataset availability plots based on the `{start,stop}Date` found in the dataset `/info` responses. Plots are stored at [hapi-server.org/meta/availabilities/](https://hapi-server.org/meta/availabilities/), and they are visible at [hapi-server.org/servers](https://hapi-server.org/servers) when selecting a server and clicking "View SERVER Time Range Coverage."

* `spase.py` creates partial SPASE records for all datasets of all servers. It uses `spase.json` for configuration information. The output is stored in [https://hapi-server.org/meta/spase/](hapi-server.org/meta/spase/).

# Development

See `etc/crontab.sh` for commands that are executed nightly.

For testing changes to the table configuration using the nightly generated metadata, use

```
rsync -avz weigel@rweigel.dynu.net:git/hapi/server-metadata/data .
pip install -e .

cd ..; pip install git+https://github.com/rweigel/table-ui
cd server-metadata

python ../table-ui/serve.py --config table/tableui.json --port 8052
```

To regenerate table metadata, use

```
python table.py [server]
```