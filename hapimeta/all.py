def all(log, use_remote_catalog=False):
  import os
  import utilrsw
  import hapimeta

  cfg_common = hapimeta.config('common')

  if use_remote_catalog:
    url = cfg_common['ALL_FILE_REMOTE']
    file = os.path.join(hapimeta.DATA_DIR, 'tmp', cfg_common['ALL_FILE'])
    log.info(f"Maybe downloading {url} to {file}")
    info = utilrsw.net.get_conditional(url, file=file, stream=True, progress=True)
    if info is None:
      log.error(f"Failed to get {url}")
      return None
    if info['status_code'] == 304:
      log.info(f"Remote file same as cached file. Using cached file: {file}")
    file_path = info['cache_file']
  else:
    file_path = os.path.join(hapimeta.DATA_DIR, cfg_common['LOCAL_ALL'])

  log.info(f'Reading {file_path}')
  return utilrsw.read(file_path)