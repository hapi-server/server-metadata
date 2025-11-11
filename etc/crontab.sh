# Execute from ../ using /bin/zsh -i etc/crontab.sh
# The -i is needed to force it to read .zshrc, which sets conda env

echo $(date +%Y-%m-%d).log > data/lastrun.txt

if [ ! -d "servers" ]; then
  git clone https://github.com/hapi-server/servers
else
  git -C servers pull --rebase
fi

python --version
pip install -e .

python abouts.py
git -C servers commit -a -m "Update abouts.json, all.txt, all_.txt [skip ci]"
git  -C servers push

python catalogs.py
python availabilities.py
python table.py
