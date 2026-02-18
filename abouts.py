import os

import utilrsw
from hapimeta import get, logger, data_dir, cli

log = logger('abouts')

# Reads and write to servers/ subdir, which must be created by cloning
# https://github.com/hapi-server/servers in same dir as this script.

simulate = False # Set to True to simulate updates for a few servers
fnames   = ['', '-dev', '-test'] # Files to process are named abouts{fname}.json
servers  = cli()  # None => all servers
timeout  = 10     # Request timeout in seconds
retries  = 3      # Number of retries for requests
if simulate:
  fnames  = ['']
  servers = ['CDAWeb']
  timeout = 1
  retries = 0

def equivalent_dicts(old, new, ignore=None):
  """Return True if dicts dicts are same, ignoring certain x_ keys."""
  import json
  import deepdiff

  if ignore is not None:
    old_filtered = {k: v for k, v in old.items() if k not in ignore}
    new_filtered = {k: v for k, v in new.items() if k not in ignore}

  diff = deepdiff.DeepDiff(old_filtered, new_filtered, ignore_order=True)
  diff = json.loads(diff.to_json())

  return diff


def merge_dicts(base, override, base_name='base', override_name='override', depth=0):

  import copy
  import json
  import deepdiff

  new = copy.deepcopy(base)
  for key, value in override.items():

    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
      merge_dicts(base[key], value,
                  base_name=base_name, override_name=override_name, depth=depth+1)
    else:
      if key not in base:
        log.info(f"    Adding {key} = '{value}' from {override_name}")
        new[key] = value
      else:
        msgo = f"{key} = '{override[key]}' in {override_name} is"
        if base[key] == value:
          log.info(f"    No update: {msgo} same as in {base_name}.")
        else:
          msg = f"    Update:    {msgo} different from {base_name} '{base[key]}'. "
          msg += f"Using {override_name} value."
          log.info(msg)
          new[key] = value

  diff = deepdiff.DeepDiff(base, new, ignore_order=True)
  diff = json.loads(diff.to_json())
  if not diff and depth == 0:
    log.info("    No updates needed.")

  return new


def update(abouts_last_fname, abouts_default_fname):

  keys_added = ['x_LastUpdateAttempt',
                'x_LastUpdateError',
                'x_LastChange',
                'x_LastChangeDiff'
              ]

  log.info(f"Reading default abouts.json from {abouts_default_fname}")
  try:
    abouts_default = utilrsw.read(abouts_default_fname)
  except Exception as e:
    log.error(f"Cannot continue. Error reading {abouts_default_fname}: {e}")
    exit(1)

  log.info(f"Reading last abouts.json from {abouts_last_fname}")
  try:
    abouts_last = utilrsw.read(abouts_last_fname)
  except Exception as e:
    emsg = f"Error reading {abouts_last_fname} {e}. "
    emsg += f"Will use contents of {abouts_default_fname}"
    log.error(emsg)
    return abouts_default

  abouts_updated = []
  for about_default in abouts_default:

    if servers is not None and about_default['id'] not in servers:
      log.info(f"Skipping {about_default['id']}.")
      continue

    log.info("")

    x_LastUpdateError = None

    about_new = {}
    try:
      about_new = get(about_default['x_url'] + '/about', timeout=timeout, log=log)
    except Exception as e:
      x_LastUpdateError = str(e)

    code = utilrsw.get_path(about_new, ["status", "code"])
    if code is not None and int(code) != 1200:
      about_new = {}
      msg = f"{about_default['x_url']}/about returned status {about_new['status']}."
      log.info(msg)
      x_LastUpdateError = msg

    about_last_dict = utilrsw.array_to_dict(abouts_last, key='x_url')
    if about_default['x_url'] not in about_last_dict:
      log.info(f"New server found in {abouts_last_fname}: {about_default['x_url']}")
    about_last = about_last_dict.get(about_default['x_url'], {})

    if simulate and 'contact' in about_last:
      # Simulate server having contact field that differs from the last about
      # generated based on default, last, and new.
      about_new['contact'] = about_last['contact'] + "x"

    if simulate:
      # Simulate a default being updated.
      import random
      about_default['title'] = f"{about_last['title']}{random.random()}"

    for key in keys_added:
      if key in about_last:
        del about_last[key]

    # Merge abouts. _new overrides _last, which overrides _default.
    log.info("  Merging default about with last about")
    about_updated = merge_dicts(about_default, about_last, 'default about', 'last about')

    log.info("  Merging result of last merge with new about to create updated about")
    about_updated = merge_dicts(about_updated, about_new, 'updated about', 'new about')

    about_updated['x_LastUpdateAttempt'] = utilrsw.time.utc_now()

    if x_LastUpdateError is not None:
      about_updated['x_LastUpdateError'] = x_LastUpdateError

    if len(about_updated) != 0:
      diff = equivalent_dicts(about_last, about_updated, ignore=keys_added)
      if diff:
        msg = "Change found between updated and last about for "
        msg += f"{about_updated['x_url']}: {diff}"
        log.info(msg)
        about_updated['x_LastChange'] = utilrsw.time.utc_now()
        about_updated['x_LastChangeDiff'] = diff

    abouts_updated.append(about_updated)

  return abouts_updated


def write_legacy():

  def to_string(abouts, style='simple'):
    lines = ""
    for about in abouts:
      for key in ['title', 'id', 'contact', 'contactID']:
        if key not in about:
          abouts[key] = ''

      if style == 'simple':
        lines += f"{about['x_url']}\n"
      else:
        lines += f"{about['x_url']}, {about['title']}, {about['id']}, "
        lines += f"{about['contact']}, {about['contactID']}\n"

    return lines

  base = utilrsw.read('servers/abouts.json')
  test = utilrsw.read('servers/abouts-test.json')

  abouts_all = base + test

  abouts_all_str = to_string(abouts_all, style='detailed')
  fname = 'servers/all_.txt'
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts_all_str)

  abouts_all_str = to_string(abouts_all, style='simple')
  fname = 'servers/all.txt'
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts_all_str)


  dev = utilrsw.read('servers/abouts-dev.json')

  abouts_all_str = to_string(dev + test, style='detailed')
  fname = 'servers/dev.txt'
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts_all_str)


def write(abouts, fname, legacy=False):

  # Update repo file
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts)

  # Update file that is copied to https://hapi-server.org/meta/
  fname = os.path.basename(fname)
  fname = os.path.join(data_dir, fname)
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts)


script_info = utilrsw.script_info()
if not os.path.exists(script_info['path']):
  log.error(f"The directory {script_info['dir']} does not have a subdir 'servers'.")
  log.error("Create it by cloning https://github.com/hapi-server/servers.")
  exit(1)

write_legacy()

for fname in fnames:
  abouts_last_fname = f'servers/abouts{fname}.json'
  abouts_default_fname = f'servers/defaults/abouts{fname}.json'

  abouts_updated = update(abouts_last_fname, abouts_default_fname)

  write(abouts_updated, abouts_last_fname, legacy=True)

