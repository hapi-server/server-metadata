import os
import utilrsw
from hapimeta import get, logger, data_dir, cli, server_error, server_error_write

debug        = False
servers_only = cli() # None to get all servers; otherwise list of server ids.
max_infos    = None  # None to get all infos. Use small number to test code.
timeout      = 60    # Set to small value to force failures.
max_workers  = 10    # Number of threads to use for parallel processing.

if debug:
  # Only get info response from first dataset
  max_infos = 1

servers_repo = os.path.join(data_dir, '..', 'servers')
files = {
  'abouts': ['abouts.json', 'abouts-dev.json', 'abouts-test.json'],
  'catalogs': os.path.join(data_dir, 'catalogs.json'),
  'catalogs_all': os.path.join(data_dir, 'catalogs-all.json')
}

log = logger('catalogs')

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
      result = get(url, log=log, indent="  ", timeout=timeout)
    except Exception as e:
      server_error(server_id, url, str(e), log)
      result = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': str(e)
      }

    if endpoint == 'catalog' and 'catalog' not in result:
      # Treat this as a failed response and (possibly) over-write result with
      #  more specific information.
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
      log.info(f"  Attempting to read last successful /{endpoint} response from {fname}")
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


def get_infos(server_id, catalog, max_infos=None):

  if 'catalog' not in catalog:
    msg = f"  Skipping {server_id} because no /catalog response."
    server_error(server_id, "_", msg, log)
    return

  if 'catalog' not in catalog['catalog']:
    msg = f"  Skipping {server_id} because no 'catalog' node in /catalog response."
    server_error(server_id, "_", msg, log)
    return

  if 'about' not in catalog:
    msg = f"  Skipping {server_id} because no /about response."
    server_error(server_id, "_", msg, log)
    return

  if 'x_url' not in catalog['about']:
    msg = f"  Skipping {server_id} because no 'x_url' about node."
    server_error(server_id, "_", msg, log)
    return

  log.info(f"{server_id}")

  n = 1
  for didx, dataset in enumerate(catalog['catalog']['catalog']):

    if 'id' not in dataset:
      msg = f"  Skipping dataset because no 'id' in dataset #{didx}."
      server_error(server_id, "_", msg, log)
      continue

    dataset_id = dataset['id']

    url = f"{catalog['about']['x_url']}/info?id={dataset_id}"

    try:
      kwargs = {'log': log, 'indent': "  ", 'timeout': timeout}
      info = get(url, **kwargs)
      info['x_LastUpdate'] = utilrsw.time.utc_now()
    except Exception as e:
      server_error(server_id, url, str(e), log)
      info = {
        'x_LastUpdateError': str(e),
        'x_LastUpdateAttempt': utilrsw.time.utc_now()
      }

    if 'parameters' not in info:
      server_error(server_id, url, "No parameters node in JSON response.", log)
      info = {
        'x_LastUpdateAttempt': utilrsw.time.utc_now(),
        'x_LastUpdateError': "No parameters node in JSON response."
      }

    fname = f"{data_dir}/infos/{server_id}/{dataset_id}.json"
    if 'x_LastUpdateError' in info:
      log.info("  Attempting to read last successful /info response.")
      try:
        info_last = utilrsw.read(fname)
        log.info("  Read last successful /info response.")
        # Overwrites x_LastUpdate{Attempt,Error}
        info = {**info_last, **info}
      except:
        server_error(server_id, url, "No last successful /info response found.", log)
        continue
    else:
      info['x_LastUpdate'] = utilrsw.time.utc_now()

    try:
      log.info(f"  Writing {fname}")
      utilrsw.write(fname, info)
    except Exception as e:
      log.error(f"  Error writing {fname}: {e}")

    if 'parameters' in info:
      for parameter in info['parameters']:
        if 'bins' in parameter:
          if 'centers' in parameter['bins']:
            del parameter['bins']['centers']
          if 'ranges' in parameter['bins']:
            del parameter['bins']['ranges']

    dataset['info'] = info

    if max_infos is not None and n >= max_infos:
      log.info(f"Stopping because {max_infos} /info requests made.")
      server_error_write(server_id, log, remove=True)
      return

    n = n + 1

  try:
    fname = f"{data_dir}/catalog/{server_id}-all.json"
    log.info(f"  Writing {fname}")
    utilrsw.write(fname, catalog['catalog'])
  except Exception as e:
    log.error(f"Error writing {fname}: {e}. Exiting with code 1.")

  server_error_write(server_id, log, remove=True)


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


def write(file_name, data, pkl=False):
  try:
    utilrsw.write(file_name, data, logger=log)
  except Exception as e:
    log.error(f"Error writing {file_name}: {e}. Exiting with code 1.")
    exit(1)

  if not pkl:
    return

  file_name = file_name.replace('.json', '.pkl')
  try:
    utilrsw.write(file_name, data, logger=log)
  except Exception as e:
    log.error(f"Error writing {file_name}: {e}. Exiting with code 1.")
    exit(1)


endpoints = {}
log.info(40*"-")
log.info("Reading abouts.")
log.info(40*"-")
abouts = read_abouts(servers_repo, files['abouts'])

"""
Create endpoints dict of form
endpoints
  about
    server_id1
      /about response
    server_id2
      /about response
"""
endpoints['about'] = utilrsw.array_to_dict(abouts, 'id')

"""
Add to endpoints dict so it has form:
endpoints
  about
    server_id1
      /about response
    server_id2
      /about response
    ...
  catalog
    server_id1
      /catalog response
    server_id2
      /catalog response
    ...
  capabilities
    server_id1
      /capabilities response
    server_id2
      /capabilities response
    ...
"""
for endpoint in ['catalog', 'capabilities']:
  log.info(40*"-")
  log.info(f"Starting /{endpoint} requests")
  log.info(40*"-")
  endpoints[endpoint] = get_endpoint(abouts, endpoint, servers_only=servers_only)


"""
Create catalogs dict of form
  server_id1
    about
      /about response
    catalog
      /catalog response which has form
      catalog: [
        [dataset_id1, title1, info1]
        ...
      ]
    capabilities
      /capabilities response
  server_id2
    ...
"""

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

write(files['catalogs'], catalogs, pkl=False)

log.info(40*"-")
log.info("Starting /info requests.")
log.info(40*"-")
"""
Insert into the catalog nodes the /info responses so that the structure is:
catalogs
  server_id1
    catalog
      catalog: [[dataset_id1, title1, info1], ...
  ...
"""
if max_workers == 1:
  for server_id in catalogs.keys():
    if 'catalog' not in catalogs[server_id]:
      continue
    get_infos(server_id, catalogs[server_id], max_infos=max_infos)
else:
  # Build infos for each server in parallel.
  # (/info requests for a each server are sequential.)
  from concurrent.futures import ThreadPoolExecutor
  def call(server_id):
    if 'catalog' not in catalogs[server_id]:
      return
    get_infos(server_id, catalogs[server_id], max_infos=max_infos)
  with ThreadPoolExecutor(max_workers=max_workers) as pool:
    pool.map(call, catalogs.keys())

log.info(40*"-")
log.info("Finished /info requests.")
log.info(40*"-")

write(files['catalogs_all'], catalogs, pkl=True)
