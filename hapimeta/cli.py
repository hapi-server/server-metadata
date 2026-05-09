import hapimeta


def commands():
  import pkgutil
  import hapimeta.generators

  command_names = []
  for module_info in pkgutil.iter_modules(hapimeta.generators.__path__):
    if module_info.name == '__init__':
      continue
    command_names.append(module_info.name)
  return sorted(command_names)


def cli():
  # Usage
  #    python run.py [generator] [--servers server1,server2,...]
  # where generator is one of abouts, catalogs, availabilities, table,

  import os
  import argparse
  import sys

  import utilrsw

  available_commands = tuple(commands())

  servers_help = 'Comma-separated list of server IDs'
  catalogs_file = os.path.join(hapimeta.DATA_DIR, 'catalogs.pkl')
  try:
    server_ids = sorted(utilrsw.read(catalogs_file).keys())
    if server_ids:
      servers_help += f". Choices: {', '.join(server_ids)}"
  except Exception:
    pass

  ALL_FILE_REMOTE = hapimeta.config('common')['ALL_FILE_REMOTE']

  epilog = [
    'Examples:',
    '  python run.py',
    '  python run.py abouts',
    '  python run.py abouts --servers server1,server2',
    'python run.py --servers server1,server2'
  ]
  command_list = ', '.join(available_commands)

  parser = argparse.ArgumentParser(
    description='Process metadata for all servers or a comma-separated subset.',
    epilog='\n'.join(epilog),
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    'command',
    nargs='?',
    default=None,
    metavar='command',
    help=f'Task to run. Choices: {command_list}',
  )
  parser.add_argument(
    '--servers',
    default=None,
    help=servers_help,
  )
  parser.add_argument(
    '--n-servers',
    type=int,
    default=None,
    help='Process at most this many servers. Ignored when --servers is given.',
  )
  parser.add_argument(
    '--n-datasets',
    type=int,
    default=None,
    help='Process at most this many datasets per server.',
  )
  parser.add_argument(
    '--use-remote-catalog',
    action='store_true',
    help=f'Use {ALL_FILE_REMOTE} instead of {hapimeta.DATA_DIR}/catalogs-all.pkl',
  )

  args, _ = parser.parse_known_args()

  if args.command is not None and args.command not in available_commands:
    parser.error(f'Unknown command: {args.command}')

  if args.n_servers is not None and args.n_servers < 0:
    parser.error('--n-servers must be >= 0')
  if args.n_datasets is not None and args.n_datasets < 0:
    parser.error('--n-datasets must be >= 0')

  if args.servers is None:
    args.servers = None
    return args

  args.servers = [server.strip() for server in args.servers.split(',') if server.strip()]
  if args.n_servers is not None:
    print('Warning: --n-servers ignored because --servers was provided', file=sys.stderr)
    args.n_servers = None

  return args