# Execute from ../ using /bin/zsh -i etc/crontab.sh
# The -i is needed to force it to read .zshrc, which sets conda env

TEE=2>&1 | tee etc/log/crontab-$(date +%Y-%m-%d).log

if [ ! -d "servers" ]; then
  git clone https://github.com/hapi-server/servers $TEE
else
  git -C servers pull --rebase $TEE
fi

python --version
pip install -e . $TEE

python abouts.py
git -C servers commit -a -m "Update abouts.json, all.txt, all_.txt [skip ci]" >> $TEE
git  -C servers push $TEE

python catalogs.py
python availabilities.py
