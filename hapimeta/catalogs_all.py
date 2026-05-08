def catalogs_all(log, use_remote_catalog=False):
  import os
  import utilrsw
  import hapimeta

  if use_remote_catalog:
    url = 'https://hapi-server.org/meta/catalog-all.pkl'
    cache_dir = os.path.join(hapimeta.DATA_DIR, 'tmp')
    if not hasattr(utilrsw, 'get'):
      utilrsw.get = utilrsw.net.get_file
    file_path = utilrsw.get(url, logger=log, cache_dir=cache_dir)
  else:
    file_path = os.path.join(hapimeta.DATA_DIR, 'catalogs-all.pkl')

  log.info(f'Reading {file_path}')
  return utilrsw.read(file_path), file_path