def all(log):

  import os
  from urllib.parse import quote

  import hapimeta
  import utilrsw

  args = hapimeta.cli()
  cfg_common = hapimeta.config('common')

  files = (
    {server_id: f'catalog/{server_id}-all.pkl' for server_id in args.servers}
    if args.servers is not None else {None: cfg_common['ALL_FILE']}
  )

  all = {}
  for server_id, relative_path in files.items():
    if args.use_remote_catalog:
      url = f"{cfg_common['DATA_DIR_REMOTE'].rstrip('/')}/{quote(relative_path, safe='/')}"
      file = os.path.join(hapimeta.DATA_DIR, 'tmp', relative_path)
      os.makedirs(os.path.dirname(file), exist_ok=True)
      log.info(f"Downloading {url} to {file}")
      info = utilrsw.net.get_conditional(url, file=file, stream=True, progress=True)
      if info is None:
        log.error(f"Failed to get {url}")
        return None
      if info['status_code'] == 304:
        log.info(f"  Remote file same as cached file. Using cached file: {file}")
      file_path = info['cache_file']
    else:
      file_path = os.path.join(hapimeta.DATA_DIR, relative_path)

    log.info(f'Reading {file_path}')
    if not os.path.exists(file_path):
      command = 'python run.py catalogs'
      if server_id is not None:
        command += f' --servers {server_id}'
      log.error(
        f"File not found: {file_path}. "
        f"Run '{command}' first to generate it, "
        f"or pass --use-remote-catalog to download it without locally generating it."
      )
      raise FileNotFoundError(f"File not found: {file_path}")
    if server_id is None:
      all = utilrsw.read(file_path)
    else:
      all[server_id] = utilrsw.read(file_path)


  subset = False
  if args.servers is not None:
    subset = True
    if not all:
      log.error('No server ids provided in --servers.')
      exit(1)
  if args.n_servers is not None:
    subset = True
    all = dict(list(all.items())[:args.n_servers])

  server_names = f'all {len(all)} servers' if not subset else f'servers {args.servers}'
  log.info(f'Using {server_names} for generating content')

  return all