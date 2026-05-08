script_dir="$(cd "$(dirname "$0")" && pwd)"

/opt/miniconda3/bin/conda \
  run -p /opt/miniconda3/envs/cdawmeta-python-3.10.9 \
  --no-capture-output \
  python "$script_dir/crontab.py"