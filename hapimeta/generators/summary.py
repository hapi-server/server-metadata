import os

import pandas

import hapimeta

cfg = hapimeta.config('catalogs')
log = hapimeta.logger('catalogs')

def run():

  log.info('Generating catalog summary file.')

  args = hapimeta.cli()
  servers_only = args.servers or None

  all = hapimeta.all(log)

  # Double catalog (['catalog']['catalog']) needed because response from
  # /catalog includes a catalog key that contains the list of datasets
  catalogs = {server_id: all[server_id]['catalog']['catalog'] for server_id in all}

  summary_file = os.path.join(hapimeta.DATA_DIR, 'catalogs-summary.txt')

  # Create catalogs-summary.txt with columns of ID, # of datasets, # of parameters
  rows = []
  for server_id, catalog in catalogs.items():
    if not catalog:
      log.warning(f"Server {server_id} has no catalog.")
      continue

    if servers_only is not None and server_id not in servers_only:
      log.info(f"Skipping server {server_id} because it is not in the list of servers to process.")
      continue

    datasets = catalog
    n_datasets = len(catalog)
    n_parameters = 0
    for dataset in datasets:
      if 'info' in dataset:
        info = dataset['info']
      else:
        log.warning(f"Dataset in server {server_id}/{dataset.get('id', '<unknown>')} has no info element.")
        n_parameters = -1
        continue

      if 'parameters' in info:
        parameters = info.get('parameters', [])
        n_parameters += len(parameters)
      else:
        log.warning(f"Dataset of server {server_id}/{dataset.get('id', '<unknown>')} has no info/parameter element.")
        n_parameters = -1
        continue

    rows.append((server_id, n_datasets, n_parameters))

  summary = pandas.DataFrame(rows, columns=['ID', '# datasets', '# parameters'])
  summary.insert(0, '', [f'{index}.' for index in range(1, len(summary) + 1)])
  summary.loc[len(summary)] = {
    '': '',
    'ID': 'Total',
    '# datasets': summary['# datasets'].sum(),
    '# parameters': summary['# parameters'].sum(),
  }

  with open(summary_file, 'w') as f:
    f.write(summary.to_string(index=False) + '\n')

  log.info(f"Wrote {summary_file}")

if __name__ == '__main__':
  run()