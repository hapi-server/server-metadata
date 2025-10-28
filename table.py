# Incomplete and not yet used.
import utilrsw
import tableui

config = {
  "use_all_attributes": True,
  "path_type": "list",
  "omit_attributes": ["x_customRequestOptions"],
  "paths": {
    "/": {
      "server": None,
      "id": None
    }
  }
}

servers = utilrsw.read('data/catalogs-all.pkl')
datasets_combined = []
catalogs = {}
parameters = {}
for server in servers:
  catalogs[server] = servers[server]['catalog']
  for i, dataset in enumerate(catalogs[server]):
    print(f"  {dataset['id']}")
    dataset['server'] = server
    if utilrsw.get_path(dataset, ['info']) is not None:
      del dataset['info']['HAPI']
      del dataset['info']['status']
    if utilrsw.get_path(dataset, ['info', 'parameters']) is not None:
      dataset['NumParameters'] = len(dataset['info']['parameters'])
      parameters[f"{server}{i}"] = dataset['info']['parameters'].copy()
      for p in parameters[f"{server}{i}"]:
        p['server'] = server
        p['id'] = dataset['id']
      del dataset['info']['parameters']
    catalogs[server][i] = utilrsw.flatten_dicts(dataset, simplify=True)

#utilrsw.print_dict(catalogs)
info = tableui.dict2sql(catalogs, config, 'data/table/hapi-all-datasets', out_dir='.')
#utilrsw.print_dict(info)
config = {
  "use_all_attributes": True,
  "path_type": "list",
  "paths": {
    "/": {
      "server": None,
      "id": None,
      "name": None
    }
  }
}

info = tableui.dict2sql(parameters, config, 'data/table/hapi-all-parameters', out_dir='.')
