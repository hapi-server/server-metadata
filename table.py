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

def compute_rows(all_file, omits=[]):
  servers = utilrsw.read(all_file)
  rows = {'dataset': [], 'parameter': []}
  for server in servers:
    catalog = servers[server]['catalog']
    for i, dataset in enumerate(catalog):
      dataset['server'] = server
      for omit in omits:
        utilrsw.rm_path(dataset, omit, ignore_error=True)
        utilrsw.rm_path(dataset, omit, ignore_error=True)

      if utilrsw.get_path(dataset, ['info', 'parameters']) is not None:
        dataset['NumParameters'] = len(dataset['info']['parameters'])
        for parameter in dataset['info']['parameters']:
          parameter = {"server": server, "id": dataset['id'], **parameter}
          row = utilrsw.flatten_dicts(parameter, simplify=True)
          rows['parameter'].append(reorder_keys(row))

      row = utilrsw.flatten_dicts(dataset, simplify=True)
      rows['dataset'].append(reorder_keys(row))
  return rows

config = {
  "dataset": {
    "name": 'hapi.all.datasets',
    "out_dir": 'data/table',
    "use_all_attributes": True,
    "path_type": "list",
    "omit_attributes": [
      "x_customRequestOptions",
      "parameters"
    ],
    "paths": {
      "/": {
        "server": None,
        "id": None
      }
    }
  },
  "parameter": {
    "name": 'hapi.all.parameters',
    "out_dir": 'data/table',
    "use_all_attributes": True,
    "paths": {
      "/": {
        "server": None,
        "id": None,
        "name": None
      }
    }
  }
}
omits = [['info', 'HAPI'], ['info', 'status']]
rows = compute_rows('data/catalogs-all.pkl', omits=omits)
tableui.dict2sql(rows['dataset'], config['dataset'])
tableui.dict2sql(rows['parameter'], config['parameter'])
