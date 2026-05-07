import hapimeta


def store(server, dataset, message, logger):
  logger.error(f"    {server} {dataset}: {message}")

  if server not in store.errors:
    store.errors[server] = {}

  if dataset not in store.errors[server]:
    store.errors[server][dataset] = []

  store.errors[server][dataset].append(message.lstrip())

store.errors = {}


def combine():
  """
  Combine all generator files under
    data/log/server-metadata/errors/servers/parts/SERVER/
  into a single file
    data/log/server-metadata/errors/servers/SERVER.json.
  """

  """Not thread safe. Assumes generators are run sequentially."""

  import os
  import json

  errors_dir = os.path.join(hapimeta.DATA_DIR, 'log', 'server-metadata', 'errors')
  parts_dir = os.path.join(errors_dir, 'parts')

  if not os.path.isdir(parts_dir):
    return

  for root, _, files in os.walk(parts_dir):
    json_files = sorted([file for file in files if file.endswith('.json')])
    if not json_files:
      continue

    combined = {}
    for file in json_files:
      fname = os.path.join(root, file)
      with open(fname) as fin:
        errors = json.load(fin)

      for dataset, messages in errors.items():
        if dataset not in combined:
          combined[dataset] = []
        combined[dataset].extend(messages)

    server = os.path.relpath(root, parts_dir)
    out_fname = os.path.join(errors_dir, f'{server}.json')
    os.makedirs(os.path.dirname(out_fname), exist_ok=True)
    with open(out_fname, 'w') as fout:
      json.dump(combined, fout, indent=2)


def write(server, generator, logger):
  import os
  import utilrsw

  fdir = os.path.join(hapimeta.DATA_DIR, 'log', 'server-metadata', 'errors')
  fname = os.path.join(fdir, 'parts', server, f'{generator}.json')
  if os.path.exists(fname):
    logger.info(f"Removing existing error file {fname}.")
    os.remove(fname)
  if server in store.errors:
    errors = store.errors[server]
    utilrsw.write(fname, errors, logger=logger)