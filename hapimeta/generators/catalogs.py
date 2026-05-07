import os

import utilrsw

import hapimeta

cfg = hapimeta.config('catalogs')
log = hapimeta.logger('catalogs')


def get_endpoint(abouts, endpoint, servers_only=None):

  results = {}
  for about in abouts:

    now = utilrsw.time.utc_now()
    server_id = about['id']

    if servers_only is not None and server_id not in servers_only:
      log.info(server_id)
      log.info("  Skipping because not in servers_only.")
      continue

    log.info(server_id)
    url = f"{about['x_url']}/{endpoint}"
    try:
      result = hapimeta.get(url, log=log, indent="  ", timeout=cfg['timeout'])
    except Exception as exc:
      hapimeta.error.store(server_id, url, str(exc), log)
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': str(exc)
      }

    if endpoint == 'catalog' and 'catalog' not in result:
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': 'No catalog node in JSON response.'
      }
    if endpoint == 'capabilities' and 'outputFormats' not in result:
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': 'No outputFormats node in JSON response.'
      }

    if 'HAPI' in result:
      del result['HAPI']
    if 'status' in result:
      del result['status']

    fname = os.path.join(hapimeta.DATA_DIR, endpoint, f'{server_id}.json')
    if 'x_LastUpdateError' in result:
      log.info(f"  Attempting to read last successful /{endpoint} response from {fname}")
      try:
        result_last = utilrsw.read(fname)
        log.info(f"  Read last successful /{endpoint} response.")
        result = {**result_last, **result}
      except Exception:
        log.info(f"  No last successful /{endpoint} response found or read of it failed.")
        continue
    else:
      result['x_LastUpdate'] = now

    results[server_id] = result

    try:
      utilrsw.write(fname, result, logger=log)
    except Exception as exc:
      log.error(f"Error writing {fname}: {exc}. Exiting with code 1.")
      exit(1)

  return results


def get_infos(server_id, catalog, max_datasets=None):

  if 'catalog' not in catalog:
    msg = f"  Skipping {server_id} because no /catalog response."
    hapimeta.error.store(server_id, '_', msg, log)
    return

  if 'catalog' not in catalog['catalog']:
    msg = f"  Skipping {server_id} because no 'catalog' node in /catalog response."
    hapimeta.error.store(server_id, '_', msg, log)
    return

  if 'about' not in catalog:
    msg = f"  Skipping {server_id} because no /about response."
    hapimeta.error.store(server_id, '_', msg, log)
    return

  if 'x_url' not in catalog['about']:
    msg = f"  Skipping {server_id} because no 'x_url' about node."
    hapimeta.error.store(server_id, '_', msg, log)
    return

  log.info(f"{server_id}")

  n = 1
  for didx, dataset in enumerate(catalog['catalog']['catalog']):

    if 'id' not in dataset:
      msg = f"  Skipping dataset because no 'id' in dataset #{didx}."
      hapimeta.error.store(server_id, '_', msg, log)
      continue

    dataset_id = dataset['id']
    url = f"{catalog['about']['x_url']}/info?id={dataset_id}"

    try:
      kwargs = {'log': log, 'indent': '  ', 'timeout': cfg['timeout']}
      info = hapimeta.get(url, **kwargs)
      info['x_LastUpdate'] = utilrsw.time.utc_now()
    except Exception as exc:
      hapimeta.error.store(server_id, url, str(exc), log)
      info = {
        'x_LastUpdateError': str(exc),
        'x_LastUpdateAttempt': utilrsw.time.utc_now()
      }

    if 'parameters' not in info:
      hapimeta.error.store(server_id, url, 'No parameters node in JSON response.', log)
      info = {
        'x_LastUpdateAttempt': utilrsw.time.utc_now(),
        'x_LastUpdateError': 'No parameters node in JSON response.'
      }

    fname = os.path.join(hapimeta.DATA_DIR, 'infos', server_id, f'{dataset_id}.json')
    if 'x_LastUpdateError' in info:
      log.info('  Attempting to read last successful /info response.')
      try:
        info_last = utilrsw.read(fname)
        log.info('  Read last successful /info response.')
        info = {**info_last, **info}
      except Exception:
        hapimeta.error.store(server_id, url, 'No last successful /info response found.', log)
        continue
    else:
      info['x_LastUpdate'] = utilrsw.time.utc_now()

    try:
      log.info(f"  Writing {fname}")
      utilrsw.write(fname, info)
    except Exception as exc:
      log.error(f"  Error writing {fname}: {exc}")

    if 'parameters' in info:
      for parameter in info['parameters']:
        if 'bins' in parameter:
          if 'centers' in parameter['bins']:
            del parameter['bins']['centers']
          if 'ranges' in parameter['bins']:
            del parameter['bins']['ranges']

    dataset['info'] = info

    if max_datasets is not None and n >= max_datasets:
      log.info(f"Stopping because {max_datasets} /info requests made.")
      hapimeta.error.write(server_id, 'catalogs', log)
      return

    n = n + 1

  try:
    fname = os.path.join(hapimeta.DATA_DIR, 'catalog', f'{server_id}-all.json')
    log.info(f"  Writing {fname}")
    utilrsw.write(fname, catalog['catalog'])
  except Exception as exc:
    log.error(f"Error writing {fname}: {exc}. Exiting with code 1.")

  hapimeta.error.write(server_id, 'catalogs', log)


def read_abouts(servers_repo, about_files):
  abouts = []
  for file in about_files:
    file = os.path.join(servers_repo, file)
    try:
      abouts.append(utilrsw.read(file))
    except Exception as exc:
      log.error(f"Error reading {file}: {exc}. Exiting with code 1.")
      exit(1)
  return sum(abouts, [])


def write(file_name, data, pkl=False):
  try:
    utilrsw.write(file_name, data, logger=log)
  except Exception as exc:
    log.error(f"Error writing {file_name}: {exc}. Exiting with code 1.")
    exit(1)

  if not pkl:
    return

  file_name = file_name.replace('.json', '.pkl')
  try:
    utilrsw.write(file_name, data, logger=log)
  except Exception as exc:
    log.error(f"Error writing {file_name}: {exc}. Exiting with code 1.")
    exit(1)


def run():
  servers_only = hapimeta.cli()
  max_datasets = 1 if cfg['debug'] else cfg['max_datasets']
  endpoints = {}
  log.info(40*'-')
  log.info('Reading abouts.')
  log.info(40*'-')
  abouts = read_abouts(cfg['servers_repo'], cfg['about_files'])

  endpoints['about'] = utilrsw.array_to_dict(abouts, 'id')

  for endpoint in ['catalog', 'capabilities']:
    log.info(40*'-')
    log.info(f'Starting /{endpoint} requests')
    log.info(40*'-')
    endpoints[endpoint] = get_endpoint(abouts, endpoint, servers_only=servers_only)

  catalogs = {}
  for about in abouts:
    server_id = about['id']
    if servers_only is not None and server_id not in servers_only:
      continue
    catalog = {'about': about}
    for endpoint in ['catalog', 'capabilities']:
      if server_id in endpoints[endpoint]:
        catalog[endpoint] = endpoints[endpoint][server_id]
    catalogs[server_id] = catalog

  write(os.path.join(hapimeta.DATA_DIR, 'catalogs.json'), catalogs, pkl=False)

  log.info(40*'-')
  log.info('Starting /info requests.')
  log.info(40*'-')
  if cfg['max_workers'] == 1:
    for server_id in catalogs.keys():
      if 'catalog' not in catalogs[server_id]:
        continue
      get_infos(server_id, catalogs[server_id], max_datasets=max_datasets)
  else:
    def call(server_id):
      if 'catalog' not in catalogs[server_id]:
        return
      get_infos(server_id, catalogs[server_id], max_datasets=max_datasets)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['max_workers']) as pool:
      pool.map(call, catalogs.keys())

  log.info(40*'-')
  log.info('Finished /info requests.')
  log.info(40*'-')

  write(os.path.join(hapimeta.DATA_DIR, 'catalogs-all.json'), catalogs, pkl=True)


if __name__ == '__main__':
  run()