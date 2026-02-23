import utilrsw
import hapimeta

log = hapimeta.logger('abouts')

def abouts(cfg):

  utilrsw.git.clone_or_pull(cfg['repo_dir'], cfg['repo_url'], logger=log)

  for file in cfg['files']:
    last = f'{cfg["repo_dir"]}/{file}'
    default = f'{cfg["repo_dir"]}/defaults/{file}'

    kwargs = {
      "timeout": cfg['timeout'],
      "retries": cfg['retries']
    }
    updated = _update(cfg['servers'], last, default, **kwargs)
    _write(updated, last)

  _write_legacy()

  msg = "Update abouts.json, all.txt, all_.txt [skip ci]"
  utilrsw.git.push(cfg['repo_dir'], cfg['repo_url'], msg, logger=log)


def _equivalent_dicts(old, new, ignore=None):
  """Return True if dicts dicts are same, ignoring certain x_ keys."""
  import json
  import deepdiff

  old_filtered = old
  new_filtered = new
  if ignore is not None:
    old_filtered = {k: v for k, v in old.items() if k not in ignore}
    new_filtered = {k: v for k, v in new.items() if k not in ignore}

  diff = deepdiff.DeepDiff(old_filtered, new_filtered, ignore_order=True)
  diff = json.loads(diff.to_json())

  return diff


def _update(servers, lasts_fname, defaults_fname,
            timeout=20, retries=3, simulate=False):

  keys_added = ['x_LastUpdateAttempt',
                'x_LastUpdateError',
                'x_LastChange',
                'x_LastChangeDiff'
              ]

  log.info(f"Reading default abouts.json from {defaults_fname}")
  try:
    defaults = utilrsw.read(defaults_fname)
  except Exception as e:
    log.error(f"Cannot continue. Error reading {defaults_fname}: {e}")
    exit(1)

  log.info(f"Reading last abouts.json from {lasts_fname}")
  try:
    lasts = utilrsw.read(lasts_fname)
    # Convert array of dicts to dict of dicts keyed by x_url
    lasts_dict = utilrsw.array_to_dict(lasts, key='x_url')
  except Exception as e:
    emsg = f"Error reading {lasts_fname} {e}. "
    emsg += f"Will use contents of {defaults_fname}"
    log.error(emsg)
    return defaults

  abouts_updated = []
  for default in defaults:

    if servers is not None and default['id'] not in servers:
      log.info(f"Skipping {default['id']}.")
      continue

    log.info("")

    x_LastUpdateError = None

    new = {}
    try:
      kwargs = {
        "timeout": timeout,
        "retries": retries,
        "log": log
      }
      new = hapimeta.get(default['x_url'] + '/about', **kwargs)
    except Exception as e:
      x_LastUpdateError = str(e)

    code = utilrsw.get_path(new, ["status", "code"])
    if code is not None and int(code) != 1200:
      status = new.get('status')
      new = {}
      msg = f"{default['x_url']}/about returned status {status}."
      log.info(msg)
      x_LastUpdateError = msg

    if default['x_url'] not in lasts_dict:
      log.info(f"New server found in {lasts_fname}: {default['x_url']}")
    last = lasts_dict.get(default['x_url'], {})

    if simulate and 'contact' in last:
      # Simulate server having contact field that differs from the last about
      # generated based on default, last, and new.
      new['contact'] = last['contact'] + "x"

    if simulate:
      # Simulate a default being updated.
      import random
      default['title'] = f"{last['title']}{random.random()}"

    for key in keys_added:
      if key in last:
        del last[key]

    kwargs = {
      'logger': log,
      'logger_indent': '    '
    }
    log.info("  Merging default about with last about")
    names = ['default about', 'last about']
    about_updated, _ = utilrsw.merge_dicts(default, last, *names, **kwargs)

    log.info("  Merging result of last merge with new about to create updated about")
    names = ['updated about', 'new about']
    about_updated, _ = utilrsw.merge_dicts(about_updated, new, *names, **kwargs)

    about_updated['x_LastUpdateAttempt'] = utilrsw.time.utc_now()

    if x_LastUpdateError is not None:
      about_updated['x_LastUpdateError'] = x_LastUpdateError

    if len(about_updated) != 0:
      diff = _equivalent_dicts(last, about_updated, ignore=keys_added)
      if diff:
        msg = "Change found between updated and last about for "
        msg += f"{about_updated['x_url']}: {diff}"
        log.info(msg)
        about_updated['x_LastChange'] = utilrsw.time.utc_now()
        about_updated['x_LastChangeDiff'] = diff

    abouts_updated.append(about_updated)

  return abouts_updated


def _write_legacy():

  def to_string(abouts, style='simple'):
    lines = ""
    for about in abouts:

      for key in ['title', 'id', 'contact', 'contactID']:
        if key not in about:
          about[key] = ''

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


def _write(abouts, fname):

  import os

  # Update repo file
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts)

  # Update file that is copied to https://hapi-server.org/meta/
  fname = os.path.basename(fname)
  fname = os.path.join(hapimeta.data_dir, fname)
  log.info(f"Writing {fname}")
  utilrsw.write(fname, abouts)


if __name__ == "__main__":
  cfg = hapimeta.config('about')
  abouts(cfg)
