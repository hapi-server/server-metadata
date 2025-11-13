source /Users/weigel/anaconda3/etc/profile.d/conda.sh; conda activate
conda activate python3.10.9-cdawmeta
CONFIG="../table/tableui.json" uvicorn tableui:factory --factory --workers 4 --port 8052 --host 0.0.0.0