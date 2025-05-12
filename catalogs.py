import utilrsw
from hapimeta import get, logger_kwargs

debug        = False
data_dir     = 'data'
servers_only = None # None to get all servers; otherwise list of server ids.
max_infos    = None # None to get all infos. Use small number to test code.
timeout      = 60   # Set to small value to force failures.
max_workers  = 10   # Number of threads to use for parallel processing.

if debug:
  servers_only = ['CDAWeb']
  max_infos = 2

files = {
  'servers': 'servers/servers.json',
  'catalogs': 'servers/data/catalogs.json',
  'catalogs_all': 'servers/data/catalogs-all.json',
}

log = utilrsw.logger(**logger_kwargs)

def get_catalogs(servers, servers_only=None):
  catalogs = {}
  for obj in servers['servers']:
    server_id = obj['id']
    if servers_only is not None and server_id not in servers_only:
      log.info(server_id)
      log.info("  Skipping because not in servers_only.")
      continue
    log.info(server_id)
    try:
      catalog = get(f"{obj['url']}/catalog", log=log, indent="  ", timeout=timeout)
    except Exception as e:
      log.error(f"  {e}")
      catalog = {
        'x_LastUpdateAttempt': utilrsw.utc_now(),
        'x_LastUpdateError': str(e)
      }

    if 'catalog' not in catalog:
      catalog = {
        'x_LastUpdateAttempt': utilrsw.utc_now(),
        'x_LastUpdateError': "No catalog node in JSON response."
      }

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
      catalog['x_LastUpdate'] = utilrsw.utc_now()

    catalog['x_URL'] = obj['url']

    catalogs[server_id] = catalog

    try:
      utilrsw.write(fname, catalog)
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
      info = get(f"{catalog['x_URL']}/info?id={id}", timeout=timeout, log=log, indent="  ")
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
      utilrsw.write(fname, info)
    except:
      log.error(f"  Error writing {fname}")

    if 'parameter' in info['parameters']:
      for parameter in info['parameters']:
        if 'bins' in parameter:
          if 'centers' in parameter['bins']:
            del parameter['bins']['centers']
          if 'ranges' in parameter['ranges']:
            del parameter['bins']['ranges']

    if max_infos is not None and n >= max_infos:
      log.info(f"Stoping because {max_infos} /info requests made.")
      return
    n = n + 1

try:
  servers = utilrsw.read(files['servers'])
except Exception as e:
  log.error(f"Error reading {files['servers']}: {e}")
  exit(1)

log.info(40*"-")
log.info("Starting /catalog requests.")
log.info(40*"-")

catalogs = get_catalogs(servers, servers_only=servers_only)

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

try:
  utilrsw.write(files['catalogs_all'], catalogs, logger=log)
except:
  log.error(f"Error writing {files['catalogs_all']}. Exiting with code 1.")
  exit(1)

file_pkl = files['catalogs_all'].replace('.json', '.pkl')
try:
  utilrsw.write(file_pkl, catalogs, logger=log)
except:
  log.error(f"Error writing {file_pkl}. Exiting with code 1.")
  exit(1)

# Remove error log file if empty.
utilrsw.rm_if_empty("catalogs.errors.log")
