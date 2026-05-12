script_dir="$(cd "$(dirname "$0")" && pwd)"

~/anaconda3/bin/conda \
  run -p ~/anaconda3/envs/python3.10.9-cdawmeta \
  --no-capture-output \
  python "$script_dir/crontab.py"
