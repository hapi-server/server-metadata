import hapimeta


def cli(commands=None):
  # Usage
  #    python run.py [generator] [server1,server2,...]
  # where generator is one of abouts, catalogs, availabilities, table,

  import argparse
  import os
  import utilrsw

  if commands is not None:
    commands = tuple(commands)

  servers_help = 'Comma-separated list of server IDs'
  catalogs_file = os.path.join(hapimeta.DATA_DIR, 'catalogs.pkl')
  try:
    server_ids = sorted(utilrsw.read(catalogs_file).keys())
    if server_ids:
      servers_help += f". Choices: {', '.join(server_ids)}"
  except Exception:
    pass

  parser = argparse.ArgumentParser(
    description='Process metadata for all servers or a comma-separated subset.',
    epilog='Examples:\n  python run.py\n  python run.py abouts\n  python run.py abouts server1,server2\n  python run.py server1,server2',
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  if commands is not None:
    command_list = ', '.join(commands)
    parser.add_argument(
      'command',
      nargs='?',
      default=None,
      metavar='command',
      help=f'Task to run. Choices: {command_list}',
    )
  parser.add_argument(
    'servers',
    nargs='?',
    default=None,
    help=servers_help,
  )

  args, _ = parser.parse_known_args()

  if commands is not None:
    command = args.command
    if command is not None and command not in commands:
      if args.servers is not None:
        parser.error(f'Unknown command: {command}')
      args.servers = command
      command = None
  else:
    command = None

  if args.servers is None:
    if commands is not None:
      return command, None
    return None

  servers = [server.strip() for server in args.servers.split(',') if server.strip()]
  print(f'Processing servers: {servers}')
  if commands is not None:
    return command, servers
  return servers