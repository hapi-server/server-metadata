def config(part):
  import os
  import json

  if part != 'common':
    # __init__.py calls config('common') before hapimeta.DATA_DIR is set,
    # which is required by logger. So only import logger if part is not 'common'.
    from .logger import logger
    log = logger(part)

  fname = os.path.join(os.path.dirname(__file__), '..', 'run.json')
  if part != 'common':
    log.info(f"Reading config from {fname}")

  with open(fname) as fin:
    run_config = json.load(fin)

  if part != 'common':
    log.info(f"Extracting {part} from config")

  return run_config[part].copy()