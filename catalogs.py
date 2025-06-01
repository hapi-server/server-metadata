import os
import utilrsw
from hapimeta import get, logger_kwargs, data_dir

debug        = True
servers_only = None # None to get all servers; otherwise list of server ids.
max_infos    = None # None to get all infos. Use small number to test code.
timeout      = 60   # Set to small value to force failures.
max_workers  = 10   # Number of threads to use for parallel processing.

if debug:
  servers_only = ["SuperMAG"]
  #max_infos = 1

files = {
  'abouts': os.path.join(data_dir, 'abouts.json'),
  'catalogs': os.path.join(data_dir, 'catalogs.json'),
  'catalogs_all': os.path.join(data_dir, 'catalogs-all.json')
}

log = utilrsw.logger(**logger_kwargs)

def get_catalogs(abouts, servers_only=None):

  catalogs = {}
  for about in abouts:

    now = utilrsw.utc_now()
    server_id = about['id']

    if servers_only is not None and server_id not in servers_only:
      log.info(server_id)
      log.info("  Skipping because not in servers_only.")
      continue

    log.info(server_id)
    try:
      catalog = get(f"{about['x_url']}/catalog", log=log, indent="  ", timeout=timeout)
    except Exception as e:
      log.error(f"  {e}")
      catalog = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': str(e)
      }

    if 'catalog' not in catalog:
      catalog = {
        'x_LastUpdateAttempt': now,
        'x_LastUpdateError': "No catalog node in JSON response."
      }

    catalog['about'] = about

    if 'HAPI' in catalog:
      del catalog["HAPI"]
    if 'status' in catalog:
      del catalog["status"]

    fname = f"{data_dir}/catalogs/{server_id}.json"
    if 'x_LastUpdateError' in catalog:
      log.info("  Attempting to read last successful /catalog response.")
      try:
        catalog_last = utilrsw.read(fname)
        log.info("  Read last successful /catalog response.")
        # Overwrites x_LastUpdate{Attempt,Error}
        catalog = {**catalog_last, **catalog}
      except:
        log.info("  No last successful /catalog response found.")
        continue
    else:
      catalog['x_LastUpdate'] = now

    catalog_reordered = {}
    if 'x_LastUpdate' in catalog:
      catalog_reordered['x_LastUpdate'] = catalog['x_LastUpdate']
    if 'x_LastUpdateAttempt' in catalog:
      catalog_reordered['x_LastUpdateAttempt'] = catalog['x_LastUpdateAttempt']
    if 'x_LastUpdateError' in catalog:
      catalog_reordered['x_LastUpdateError'] = catalog['x_LastUpdateError']
    catalog_reordered['about'] = catalog['about']
    catalog_reordered['catalog'] = catalog['catalog']

    catalogs[server_id] = catalog_reordered

    try:
      utilrsw.write(fname, catalog_reordered)
    except:
      log.error(f"Error writing {fname}. Exiting with code 1.")
      exit(1)

  return catalogs

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
      info = get(f"{catalog['about']['x_url']}/info?id={id}", timeout=timeout, log=log, indent="  ")
      info['x_LastUpdate'] = utilrsw.utc_now()
    except Exception as e:
      info = {
        'x_LastUpdateError': str(e),
        'x_LastUpdateAttempt': utilrsw.utc_now()
      }

    if 'parameters' not in info:
      info = {
        'x_LastUpdateAttempt': utilrsw.utc_now(),
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
      info['x_LastUpdate'] = utilrsw.utc_now()

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
  abouts = utilrsw.read(files['abouts'])
except Exception as e:
  log.error(f"Error reading {files['abouts']}: {e}")
  exit(1)

log.info(40*"-")
log.info("Starting /catalog requests.")
log.info(40*"-")

catalogs = get_catalogs(abouts, servers_only=servers_only)

log.info(40*"-")
log.info("Finished /catalog requests.")
log.info(40*"-")

try:
  utilrsw.write(files['catalogs'], catalogs)
except:
  log.error(f"Error writing {files['catalogs']}. Exiting with code 1.")
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

# Remove error log file if empty.
f = os.path.join(logger_kwargs['log_dir'], "catalogs.errors.log")
utilrsw.rm_if_empty(f)
