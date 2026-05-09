def all(log, use_remote_catalog=False):
  import os
  import utilrsw
  import hapimeta

  cfg_common = hapimeta.config('common')

  if use_remote_catalog:
    url = cfg_common['REMOTE_ALL']
    cache_dir = os.path.join(hapimeta.DATA_DIR, 'tmp')
    if not hasattr(utilrsw, 'get'):
      utilrsw.get = utilrsw.net.get_file
    file_path = utilrsw.get(url, logger=log, cache_dir=cache_dir)
  else:
    file_path = os.path.join(hapimeta.DATA_DIR, cfg_common['LOCAL_ALL'])

  log.info(f'Reading {file_path}')
  return utilrsw.read(file_path)