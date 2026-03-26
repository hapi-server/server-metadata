import os
import datetime

import utilrsw
import tableui

import hapiclient
from hapimeta import logger, data_dir, cli

log = logger('table')

def reorder_keys(d):
  # move keys starting with 'x_' to the end, preserving relative order
  x_items = [(k, d[k]) for k in d.keys() if k.startswith('x_')]
  other_items = [(k, d[k]) for k in d.keys() if not k.startswith('x_')]
  newd = {}
  for k, v in other_items:
    newd[k] = v
  for k, v in x_items:
    newd[k] = v
  return newd


def format_bins(bins):
  def ellipsis(arr):
    if len(arr) > 5:
      return arr[0:2] + ['...'] + arr[-2:]
    return arr

  bins_new = {}
  for idx, bin in enumerate(bins):
    for key in bin:
      key_new = f"bins[{idx}]/{key}"
      if isinstance(bin[key], list):
        bins_new[key_new] = ellipsis(bin[key])
      else:
        bins_new[key_new] = bin[key]

  return bins_new


def normalize_datetime(time_str):
  try:
    time_str = str(time_str).strip()
    dt = hapiclient.hapitime2datetime(time_str)[0]
    if dt.tzinfo is None:
      dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
  except Exception as e:
    log.error(f"Error normalizing time: {time_str}. Error: {e}")
    return None


def compute_rows(all_file, servers=None, omits=[]):

  servers_keep = servers
  servers = utilrsw.read(all_file)

  rows = {
    'dataset': [],
    'parameter': []
  }

  for server in servers:
    if servers_keep is not None and server not in servers_keep:
      continue

    log.info(f"Processing server: {server}")

    catalog = utilrsw.get_path(servers[server], 'catalog/catalog', sep='/')
    if catalog is None:
      log.error(f"Could not find catalog for server: {server}. Skipping server.")
      continue

    for dataset in catalog:
      dataset['server'] = server
      dataset['dataset'] = dataset['id']
      del dataset['id']

      utilrsw.rm_paths(dataset, omits, sep='/', ignore_error=True)

      if utilrsw.get_path(dataset, ['info', 'additionalMetadata']) is not None:
        if isinstance(dataset['info']['additionalMetadata'], dict):
          continue

      parameters = utilrsw.get_path(dataset, ['info', 'parameters'])
      if parameters is None:
        msg = "Could not find parameters for dataset: "
        msg += f"{server}/{dataset['dataset']}. Skipping dataset."
        log.error(msg)
        continue

      dataset['x_nParams'] = len(parameters)
      startDate = utilrsw.get_path(dataset, 'info.startDate', '')
      stopDate = utilrsw.get_path(dataset, 'info.stopDate', '')
      dataset['x_startDate'] = normalize_datetime(startDate)
      dataset['x_stopDate'] = normalize_datetime(stopDate)
      for parameter in parameters:
        parameter['parameter'] = parameter['name']
        del parameter['name']
        if 'units' in parameter and parameter['units'] is None:
          parameter['units'] = ''
        parameter = {
          "server": server,
          "dataset": dataset['dataset'],
          "startDate": startDate,
          "x_startDate": normalize_datetime(startDate),
          "stopDate": stopDate,
          "x_stopDate": normalize_datetime(stopDate),
          "cadence": utilrsw.get_path(dataset, 'info.cadence', ''),
          **parameter
        }

        if 'bins' in parameter:
          if isinstance(parameter['bins'], list):
            try:
              parameter['bins'] = format_bins(parameter['bins'])
            except Exception as e:
              msg = "Error formatting bins for parameter: "
              msg += f"{server}/{dataset['dataset']}/{parameter['parameter']}. Error: {e}"
              log.error(msg)

        row = utilrsw.flatten_dicts(parameter, simplify=True)
        rows['parameter'].append(reorder_keys(row))

      row = utilrsw.flatten_dicts(dataset, simplify=True)
      rows['dataset'].append(reorder_keys(row))

  return rows


file = os.path.join(data_dir, 'catalogs-all.pkl')
omits = ['info/HAPI', 'info/status', 'info/definitions']
servers = cli() # None => all servers

rows = compute_rows(file, omits=omits, servers=servers)

p = [utilrsw.script_info()['dir'], 'table', 'dict2sql.json']
config = utilrsw.read(os.path.join(*p))
tableui.dict2sql(rows['dataset'], config['dataset'], logger=log)
tableui.dict2sql(rows['parameter'], config['parameter'], logger=log)

print('See etc/serve-table.sh for command to serve table.')
