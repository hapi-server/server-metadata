import os

import utilrsw
import tableui

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

    catalog = servers[server]['catalog']['catalog']
    for dataset in catalog:
      dataset['server'] = server
      dataset['dataset'] = dataset['id']
      del dataset['id']

      utilrsw.rm_paths(dataset, omits, sep='/', ignore_error=True)

      if utilrsw.get_path(dataset, ['info', 'additionalMetadata']) is not None:
        if isinstance(dataset['info']['additionalMetadata'], dict):
          continue

      if utilrsw.get_path(dataset, ['info', 'parameters']) is not None:
        dataset['x_nParams'] = len(dataset['info']['parameters'])
        for parameter in dataset['info']['parameters']:
          parameter['parameter'] = parameter['name']
          del parameter['name']
          if 'units' in parameter and parameter['units'] is None:
            parameter['units'] = ''
          parameter = {
            "server": server,
            "dataset": dataset['dataset'],
            "startDate": utilrsw.get_path(dataset, 'info.startDate', ''),
            "stopDate": utilrsw.get_path(dataset, 'info.stopDate', ''),
            "cadence": utilrsw.get_path(dataset, 'info.cadence', ''),
            **parameter
          }
          if 'bins' in parameter:
            parameter['bins'] = format_bins(parameter['bins'])
          row = utilrsw.flatten_dicts(parameter, simplify=True)
          rows['parameter'].append(reorder_keys(row))

      row = utilrsw.flatten_dicts(dataset, simplify=True)
      rows['dataset'].append(reorder_keys(row))

  return rows

file = os.path.join(data_dir, 'catalogs-all.pkl')
omits = ['info/HAPI', 'info/status', 'info/definitions', 'info/x_LastUpdate']
servers = cli() # None => all servers

rows = compute_rows(file, omits=omits, servers=servers)

config = utilrsw.read(os.path.join(utilrsw.script_info()['dir'], 'table', 'dict2sql.json'))
tableui.dict2sql(rows['dataset'], config['dataset'], logger=log)
tableui.dict2sql(rows['parameter'], config['parameter'], logger=log)

print('See etc/serve.sh for command to serve table.')
