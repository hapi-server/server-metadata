# Execute from ../ using /bin/zsh -i etc/crontab.sh
# The -i is needed to force it to read .zshrc, which sets conda env

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_dir="$(cd "$script_dir/.." && pwd)"

if [ -z "${CRONTAB_SH_LOGGED:-}" ]; then
  log_dir="$script_dir/../data/log/crontab"
  mkdir -p "$log_dir"
  log_file="$log_dir/crontab-$(/bin/date +%Y%m%d).log"
  export CRONTAB_SH_LOGGED=1
  exec >> "$log_file" 2>&1
fi

cd "$repo_dir" || exit 1

echo $(date +%Y-%m-%d).log > data/lastrun.txt

if [ ! -d "servers" ]; then
  git clone https://github.com/hapi-server/servers
else
  git -C servers pull --rebase
fi

#python --version
#pip install -e .

python abouts.py
git -C servers commit -a -m "Update abouts.json, all.txt, all_.txt [skip ci]"
git  -C servers push
exit 0

python catalogs.py
python availabilities.py
python table.py
