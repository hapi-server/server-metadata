import os
import utilrsw
from hapimeta import get, logger, data_dir, cli

debug        = True
servers_only = cli() # None to get all servers; otherwise list of server ids.
max_infos    = None # None to get all infos. Use small number to test code.
timeout      = 60   # Set to small value to force failures.
max_workers  = 10   # Number of threads to use for parallel processing.

if debug:
  max_infos = 1

servers_repo = os.path.join(data_dir, '..', 'servers')
files = {
  'abouts': ['abouts.json', 'abouts-dev.json', 'abouts-test.json'],
  'catalogs': os.path.join(data_dir, 'catalogs.json'),
  'catalogs_all': os.path.join(data_dir, 'catalogs-all.json')
}

log = logger('catalogs')

def get_endpoints(abouts, endpoint, servers_only=None):

  results = {}
  for about in abouts:

    now = utilrsw.time.utc_now()
    server_id = about['id']

    if servers_only is not None and server_id not in servers_only:
      log.info(server_id)
      log.info("  Skipping because not in servers_only.")
      continue

    log.info(server_id)
    try:
      result = get(f"{about['x_url']}/{endpoint}", log=log, indent="  ", timeout=timeout)
    except Exception as e:
      log.error(f"  {e}")
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': str(e)
      }

    if endpoint == 'catalog' and 'catalog' not in result:
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': "No catalog node in JSON response."
      }
    if endpoint == 'capabilities' and 'outputFormats' not in result:
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': "No outputFormats node in JSON response."
      }

    if 'HAPI' in result:
      del result["HAPI"]
    if 'status' in result:
      del result["status"]

    fname = f"{data_dir}/{endpoint}/{server_id}.json"
    if 'x_LastUpdateError' in result:
      log.info(f"  Attempting to read last successful /{endpoint} response.")
      try:
        result_last = utilrsw.read(fname)
        log.info(f"  Read last successful /{endpoint} response.")
        # Overwrites x_LastUpdate{Attempt,Error}
        result = {**result_last, **result}
      except Exception:
        log.info(f"  No last successful /{endpoint} response found or read of it failed.")
        continue
    else:
      result['x_LastUpdate'] = now

    results[server_id] = result

    try:
      utilrsw.write(fname, result, logger=log)
    except Exception as e:
      log.error(f"Error writing {fname}: {e}. Exiting with code 1.")
      exit(1)

  return results


def get_infos(cid, catalog, max_infos=None):

  if 'catalog' not in catalog:
    msg = f"  Skipping {cid} because no catalog array."
    log.info(msg)
    return

  n = 1
  for dataset in catalog['catalog']:
    id = dataset['id']
    log.info(id)
    try:
      kwargs = {'log': log, 'indent': "  ", 'timeout': timeout}
      info = get(f"{catalog['about']['x_url']}/info?id={id}", **kwargs)
      info['x_LastUpdate'] = utilrsw.time.utc_now()
    except Exception as e:
      info = {
        'x_LastUpdateError': str(e),
        'x_LastUpdateAttempt': utilrsw.time.utc_now()
      }

    if 'parameters' not in info:
      info = {
        'x_LastUpdateAttempt': utilrsw.time.utc_now(),
        'x_LastUpdateError': "No parameters node in JSON response."
      }

    fname = f"{data_dir}/infos/{cid}/{id}.json"
    if 'x_LastUpdateError' in info:
      log.info("  Attempting to read last successful /info response.")
      try:
        info_last = utilrsw.read(fname)
        log.info("  Read last successful /info response.")
        # Overwrites x_LastUpdate{Attempt,Error}
        info = {**info_last, **info}
      except:
        log.info("  No last successful /info response found.")
        continue
    else:
      info['x_LastUpdate'] = utilrsw.time.utc_now()

    try:
      log.info(f"  Writing {fname}")
      utilrsw.write(fname, info)
    except Exception as e:
      log.error(f"  Error writing {fname}: {e}")

    if 'parameter' in info['parameters']:
      for parameter in info['parameters']:
        if 'bins' in parameter:
          if 'centers' in parameter['bins']:
            del parameter['bins']['centers']
          if 'ranges' in parameter['ranges']:
            del parameter['bins']['ranges']

    dataset['info'] = info

    if max_infos is not None and n >= max_infos:
      log.info(f"Stoping because {max_infos} /info requests made.")
      return

    n = n + 1

  try:
    fname = f"{data_dir}/catalogs/{cid}-all.json"
    log.info(f"  Writing {fname}")
    utilrsw.write(fname, catalog['catalog'])
  except Exception as e:
    log.error(f"Error writing {fname}: {e}. Exiting with code 1.")


def read_abouts(servers_repo, about_files):
  abouts = []
  for file in about_files:
    file = os.path.join(servers_repo, file)
    try:
      abouts.append(utilrsw.read(file))
    except Exception as e:
      log.error(f"Error reading {file}: {e}. Exiting with code 1.")
      exit(1)
  return sum(abouts, [])  # Flatten list of lists.

parts = {}
log.info(40*"-")
log.info("Reading abouts.")
log.info(40*"-")
abouts = read_abouts(servers_repo, files['abouts'])

for endpoint in ['catalog', 'capabilities']:
  log.info(40*"-")
  log.info(f"Starting /{endpoint} requests")
  log.info(40*"-")
  parts[endpoint] = get_endpoints(abouts, endpoint, servers_only=servers_only)

catalogs = []
for about in abouts:
  server_id = about['id']
  if servers_only is not None and server_id not in servers_only:
    continue
  catalog = {'about': about}
  for endpoint in ['catalog', 'capabilities']:
      if server_id in parts[endpoint]:
        catalog[endpoint] = parts[endpoint][server_id]
  catalogs.append(catalog)

try:
  utilrsw.write(files['catalogs'], catalogs, logger=log)
except Exception as e:
  log.error(f"Error writing {files['catalogs']}: {e}. Exiting with code 1.")
  exit(1)

log.info(40*"-")
log.info("Starting /info requests.")
log.info(40*"-")
# catalog['catalog'] is an array of dataset objects with at least a key of
# 'id' (dataset id). get_infos() adds an 'info' key to each dataset object.
if max_workers == 1:
  for cid, catalog in catalogs.items():
    get_infos(cid, catalog, max_infos=max_infos)
else:
  # Build infos for each server in parallel.
  # (/info requests for a each server are sequential.)
  from concurrent.futures import ThreadPoolExecutor
  def call(cid):
    get_infos(cid, catalogs[cid], max_infos=max_infos)
  with ThreadPoolExecutor(max_workers=max_workers) as pool:
    pool.map(call, catalogs.keys())

log.info(40*"-")
log.info("Finished /info requests.")
log.info(40*"-")

for file in ['catalogs_all', 'catalogs']:

  if file == 'catalogs':
    for server in catalogs.keys():
      for dataset in catalogs[server]['catalog']:
        if 'info' in dataset:
          del dataset['info']
        if 'about' in dataset:
          del dataset['about']

  try:
    utilrsw.write(files[file], catalogs, logger=log)
  except Exception as e:
    log.error(f"Error writing {files[file]}: {e}. Exiting with code 1.")
    exit(1)

  file_pkl = files[file].replace('.json', '.pkl')
  try:
    utilrsw.write(file_pkl, catalogs, logger=log)
  except Exception as e:
    log.error(f"Error writing {file_pkl}: {e}. Exiting with code 1.")
    exit(1)
