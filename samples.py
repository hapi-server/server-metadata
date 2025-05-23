# Usage:
#   python samples.py --server [server_id1,server_id2,...] --dataset dataset_id
#   prefix server id or dataset id with ^ to trigger regex match.

import os
import datetime

import utilrsw

import hapiclient

from hapimeta import logger_kwargs, data_dir
from hapiplot import hapiplot

log = utilrsw.logger(**logger_kwargs)

savefig_fmts      = ['svg', 'png']
out_dir           = os.path.join(data_dir, 'availability')
catalogs_all_file = os.path.join(data_dir, 'catalogs-all.pkl')

def cli():
  clkws = {
    "server": {
      "help": "server id or comma separated list of server ids."
    },
    "dataset": {
      "help": "dataset id or comma separated list of dataset ids. Escape commas in id with \. Prefix dataset id with ^ to use regex match."
    }
  }

  import io
  import csv
  import argparse

  parser = argparse.ArgumentParser()
  for k, v in clkws.items():
    parser.add_argument(f'--{k}', **v)

  # Note that hyphens are converted to underscores when parsing
  args = vars(parser.parse_args())

  server = None
  if args['server'] is not None:
    server = args['server'].split(',')

  dataset = None
  if args['dataset'] is not None:
    # Use csv.reader to handle escaping commas
    csv_reader = csv.reader(io.StringIO(args['dataset']), escapechar='\\')
    dataset = next(csv_reader)

  return server, dataset

def process_server(catalog_all, server, datasets_only):

  def extract_time(info, key):
    if key not in info:
      log.error(f"  {server}/{dataset['id']}: key '{key}' is not in info")
      return None, None

    if info[key].strip() == "":
      log.error(f"  {server}/{dataset['id']}: info[{key}].strip() = ''")
      return None, None

    hapitime = info[key]
    hapitimeSample = None
    if key == 'startDate' and 'sampleStartDate' in info:
        hapitimeSample = info['sampleStartDate']
    if key == 'stopDate' and 'sampleStopDate' in info:
        hapitimeSample = info['sampleStopDate']

    return hapitime, hapitimeSample

  log.info(f"server: {server} | {len(catalog_all['catalog'])} datasets")
  server_url = catalog_all['about']['url']
  for dataset in catalog_all['catalog']:

    if 'id' not in dataset:
      log.error(f"  No 'id' in metadata: {dataset}. Skipping dataset.")
      continue

    if 'info' not in dataset:
      log.error(f"  id={dataset['id']}: No 'info' key. Skipping.")
      continue

    if datasets_only is not None and dataset['id'] not in datasets_only:
      log.info(f"  id={dataset['id']}: skipping dataset due to --dataset option")
      continue

    if 'parameters' not in dataset['info']:
      log.error(f"  id={dataset['id']}: No 'parameters' key. Skipping dataset.")
      continue

    startDate, sampleStartDate = extract_time(dataset['info'], 'startDate')
    stopDate, sampleStopDate = extract_time(dataset['info'], 'stopDate')

    parameters = dataset['info']['parameters']
    log.info("")
    log.info(f"  id={dataset['id']}")
    log.info(f"  {len(parameters)} parameters")
    log.info(f"  startDate = {startDate}")
    log.info(f"  stopDate = {stopDate}")
    log.info(f"  sampleStartDate = {sampleStartDate}")
    log.info(f"  sampleStopDate  = {sampleStopDate}")
    log.info("  parameters:")

    if sampleStartDate is not None and sampleStopDate is not None:
      startDate = sampleStartDate
      stopDate = sampleStopDate
    else:
      startDate = startDate
      stopDate = hapiclient.hapitime2datetime(startDate, allow_missing_Z=True)[0]
      stopDate = stopDate + datetime.timedelta(days=1)
      stopDate = datetime.strptime(stopDate, "%Y-%m-%dT%H:%M:%S.%fZ")

    for i, parameter in enumerate(parameters):
      log.info(f"     {i}. {parameter['name']}")
      try:
        data, meta = hapiclient.hapi(server_url, dataset['id'], parameter['name'], startDate, stopDate, logging=True)
      except Exception as e:
        log.error(f"  {server} {dataset['id']}: Error getting data: {e}")
        continue
      try:
        import pdb; pdb.set_trace()
        data, meta = hapiplot(data, meta, returnimage=True)
      except Exception as e:
        log.error(f"  {server} {dataset['id']}: Error plotting data: {e}")
        continue

servers_only, datasets_only = cli()

catalogs_all = utilrsw.read(catalogs_all_file)

if servers_only is not None:
  log.info(f"Generating sample plots for servers: {servers_only}")
else:
  log.info(f"Generating sample plots for all servers in {catalogs_all_file}")

if datasets_only is not None:
  log.info(f"Generating sample plots for datasets: {datasets_only}")
else:
  log.info("Generating sample plots for all datasets.")

servers = []
for server in catalogs_all.keys():
  if servers_only is not None and server not in servers_only:
    continue
  servers.append(server)

for server in servers:
  process_server(catalogs_all[server], server, datasets_only)

# Remove error log file if empty.
utilrsw.rm_if_empty(os.path.join("log", "samples.errors.log"))
