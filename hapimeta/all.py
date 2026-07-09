def all(log):
  import os
  import utilrsw
  import hapimeta

  args = hapimeta.cli()
  cfg_common = hapimeta.config('common')

  if args.use_remote_catalog:
    url = cfg_common['ALL_FILE_REMOTE']
    file = os.path.join(hapimeta.DATA_DIR, 'tmp', cfg_common['ALL_FILE'])
    log.info(f"Downloading {url} to {file}")
    info = utilrsw.net.get_conditional(url, file=file, stream=True, progress=True)
    if info is None:
      log.error(f"Failed to get {url}")
      return None
    if info['status_code'] == 304:
      log.info(f"Remote file same as cached file. Using cached file: {file}")
    file_path = info['cache_file']
  else:
    file_path = os.path.join(hapimeta.DATA_DIR, cfg_common['ALL_FILE'])

  log.info(f'Reading {file_path}')
  if not os.path.exists(file_path):
    log.error(
      f"File not found: {file_path}. "
      f"Run 'python run.py catalog' first to generate it, "
      f"or pass --use-remote-catalog to download it without locally generating it."
    )
    raise FileNotFoundError(f"File not found: {file_path}")
  all = utilrsw.read(file_path)


  subset = False
  if args.servers is not None:
    subset = True
    all = {server_id: server_meta for server_id, server_meta in all.items() if server_id in args.servers}
  if args.n_servers is not None:
    subset = True
    all = dict(list(all.items())[:args.n_servers])

  server_names = f'all {len(all)} servers' if not subset else f'servers {args.servers}'
  log.info(f'Using {server_names} for generating content')

  return all