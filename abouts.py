import os

import utilrsw
from hapimeta import get, logger_kwargs, data_dir

log = utilrsw.logger(**logger_kwargs)

# Reads and write to servers subdir, which is
# https://github.com/hapi-server/servers
fname_abt1 = 'servers/abouts.json'
fname_abt2 = os.path.join(data_dir, 'abouts.json')
fname_all1 = 'servers/all_.txt'
fname_all2 = 'servers/all.txt'

def equivalent_dicts(about_old, about_new):
  diff = False

  for key_old, _ in about_old.items():
    if key_old.startswith("x_"):
      continue
    if key_old not in about_new:
      log.info(f"  key '{key_old}' in {fname_abt1} not in /about response. Using {fname_abt1} key/value.")

  log.info("  ---")

  for key_new, val_new in about_new.items():
    if key_new.startswith("x_"):
      continue
    if key_new not in about_old:
      log.info(f"  key '{key_new}' in /about response not in {fname_abt1}. Adding key/value to {fname_abt1}.")
      diff = True
    if not diff and val_new != about[key_new]:
      log.info(f"  {fname_abt1}['{key_new}'] = {about[key_new]} != /about['{key_new}'] = '{about_new[key_new]}'. Replacing {fname_abt1} value.")
      diff = True
  return diff

log.info(f"Reading {fname_abt1}")
abouts = utilrsw.read(fname_abt1)

changed = False
for idx, about in enumerate(abouts):

  log.info("")

  try:
    about_new = get(about['x_url'] + '/about', log=log)
  except Exception as e:
    about['x_LastUpdateAttempt'] = utilrsw.time.utc_now()
    about['x_LastUpdateError'] = str(type(e)) + " " + str(e)
    continue

  code = utilrsw.get_path(about_new, ["status", "code"])
  if code is not None and int(code) != 1200:
    log.info(f"  {about['x_url']}/about returned status {about_new['status']}. Ignoring response and not updating {fname_abt1}.")
    continue

  about['x_LastUpdate'] = utilrsw.time.utc_now()

  if not equivalent_dicts(about, about_new):
    log.info(f"  No difference between {fname_abt1}['{about['id']}'] and {about['x_url']}")
  else:
    changed = True
    about["x_LastUpdateChange"] = utilrsw.time.utc_now()
    abouts[idx] = {**about, **about_new}


if not changed:
  log.info(f"No changes to {fname_abt1}. Updating only x_ fields.")

log.info(f"Writing {fname_abt1}")
utilrsw.write(fname_abt1, abouts)
log.info(f"Writing {fname_abt2}")
utilrsw.write(fname_abt2, abouts)

if True:
  all_file_str1 = ""
  all_file_str2 = ""
  for about in abouts:
    all_file_str1 += f"{about['x_url']}, {about['title']}, {about['id']}, {about['contact']}, {about['contactID']}\n"
    all_file_str2 += f"{about['x_url']}\n"
  log.info(f"Writing {fname_all1}")
  utilrsw.write(fname_all1, all_file_str1)
  log.info(f"Writing {fname_all2}")
  utilrsw.write(fname_all2, all_file_str2)
else:
  msg = f"No changes to {fname_abt1}. Not writing {fname_all1} or {fname_all2}."
  log.info(msg)

# Remove error log file if empty.
f = os.path.join(logger_kwargs['log_dir'], "servers.errors.log")
utilrsw.rm_if_empty(f)
