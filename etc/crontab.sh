# Execute from ../;
git config pull.rebase true
if [ ! -d "servers" ]; then
  git clone https://github.com/hapi-server/servers
else
  git -C servers pull
fi
pip install -e .

python abouts.py
git -C servers commit -a -m "Update abouts.json, all.txt, all_.txt [skip ci]"
git  -C servers push

python catalogs.py
python availabilities.py
