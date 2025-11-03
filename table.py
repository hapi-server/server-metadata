import utilrsw
import tableui

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
      key_new = f"bin[{idx}]/{key}"
      if isinstance(bin[key], list):
        bins_new[key_new] = ellipsis(bin[key])
      else:
        bins_new[key_new] = bin[key]
  return bins_new

def compute_rows(all_file, omits=[]):
  servers = utilrsw.read(all_file)
  rows = {'dataset': [], 'parameter': []}
  for server in servers:
    if server != 'CDAWeb':
      continue
    catalog = servers[server]['catalog']
    for dataset in catalog:
      dataset['server'] = server

      for omit in omits:
        utilrsw.rm_path(dataset, omit, ignore_error=True)
        utilrsw.rm_path(dataset, omit, ignore_error=True)

      if utilrsw.get_path(dataset, ['info', 'parameters']) is not None:
        dataset['NumParameters'] = len(dataset['info']['parameters'])
        for parameter in dataset['info']['parameters']:
          parameter = {"server": server, "id": dataset['id'], **parameter}
          if 'bins' in parameter:
            parameter['bins'] = format_bins(parameter['bins'])
          row = utilrsw.flatten_dicts(parameter, simplify=True)
          rows['parameter'].append(reorder_keys(row))

      row = utilrsw.flatten_dicts(dataset, simplify=True)
      rows['dataset'].append(reorder_keys(row))

  return rows

config = utilrsw.read('table/dict2sql.json')
omits = [['info', 'HAPI'], ['info', 'status']]
rows = compute_rows('data/catalogs-all.pkl', omits=omits)
tableui.dict2sql(rows['dataset'], config['dataset'])
tableui.dict2sql(rows['parameter'], config['parameter'])

tableui.serve(config='table/tableui.json', port=6001)
