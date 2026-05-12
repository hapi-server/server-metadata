import sys
import importlib

import hapimeta


def main():
  args = hapimeta.cli()
  if args.command is None:
    command_names = importlib.import_module('hapimeta.cli').commands()
  else:
    command_names = [args.command]

  breakpoint()
  for command_name in command_names:
    sys.argv = [sys.argv[0]]
    if args.servers is not None:
      sys.argv.extend(['--servers', ','.join(args.servers)])
    if args.n_servers is not None:
      sys.argv.extend(['--n-servers', str(args.n_servers)])
    if args.n_datasets is not None:
      sys.argv.extend(['--n-datasets', str(args.n_datasets)])
    if args.use_remote_catalog:
      sys.argv.append('--use-remote-catalog')
    module_name = f'hapimeta.generators.{command_name}'
    module = importlib.import_module(module_name)
    module.run()
    hapimeta.error.combine()


if __name__ == '__main__':
  main()