if [ ! -d "servers" ]; then
  git clone https://github.com/hapi-server/servers
else
  git -C servers pull
fi
pip install -e .

python servers.py
git -C servers commit -a -m "Update servers.json, ... [skip ci]"
git  -C servers push

python catalogs.py
python availability.py