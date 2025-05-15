# Usage:
#   python samples.py [server_id1,server_id2,...]

import os
import sys
import pickle
import pandas
import warnings

import utilrsw

from datetime import datetime, timedelta
from hapiclient import hapitime2datetime
from hapimeta import logger_kwargs

log = utilrsw.logger(**logger_kwargs)

warnings.filterwarnings("ignore", message="missing from current font.")

# Number of servers to process in parallel (> 1 not working b/c
# matplotlib not used in thread-safe manner)
max_workers    = 1
lines_per_plot = 50     # Number of time range bars per plot
# File formats to save. 'png' and 'svg' are supported.
savefig_fmts = ['svg', 'png']

dpi        = 300
fig_width  = 3840           # pixels
fig_width  = fig_width/dpi  # inches
fig_height = 2160           # pixels
fig_height = fig_height/dpi # inches

out_dir           = 'data/availability'     # Output directory
catalogs_all_file = 'data/catalogs-all.pkl' # Input file

def process_server(server, catalogs_all):

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

  lines = []
  datasets = []
  starts = []
  stops = []
  log.info(f"server: {server} | {len(catalogs_all['catalog'])} datasets")
  for dataset in catalogs_all['catalog']:
    if 'info' not in dataset:
      log.error(f"  {server}/{dataset['id']}: No 'info' key")
      print(server, dataset['id'], None, None)
      continue

    if 'parameters' not in dataset['info']:
      log.error(f"  {server}/{dataset['id']}: No 'parameters' key")
      print(server, dataset['id'], None, None)
      continue

    info = dataset['info']

    startDate, sampleStartDate = extract_time(info, 'startDate')
    stopDate, sampleStopDate = extract_time(info, 'stopDate')

    parameters = dataset['info']['parameters']
    log.info("")
    log.info(f"  dataset: {dataset['id']}")
    log.info(f"  {len(parameters)} parameters")
    log.info(f"  startDate = {startDate}")
    log.info(f"  stopDate = {stopDate}")
    log.info(f"  sampleStartDate = {sampleStartDate}")
    log.info(f"  sampleStopDate  = {sampleStopDate}")

    for i, parameter in enumerate(parameters):
      log.info(f"     {i}. {parameter['name']}")

catalogs_all = utilrsw.read(catalogs_all_file)

servers_only = None
if len(sys.argv) > 1:
  servers_only = sys.argv[1].split(',')
  log.info(f"Generating sample plots for {servers_only}")
else:
  log.info(f"Generating sample plots for all servers in {catalogs_all_file}")

servers = []
for server in catalogs_all.keys():
  if servers_only is not None and server not in servers_only:
    continue
  servers.append(server)

if max_workers == 1:
  dfs = []
  for server in servers:
    process_server(server, catalogs_all[server])

# Remove error log file if empty.
utilrsw.rm_if_empty("log/samples.errors.log")
