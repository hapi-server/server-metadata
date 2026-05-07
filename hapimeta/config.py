def config(part):
  import os
  import json

  fname = os.path.join(os.path.dirname(__file__), '..', 'run.json')
  with open(fname) as fin:
    run_config = json.load(fin)

  cfg = run_config[part].copy()

  return cfg