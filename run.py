import os
import sys
import importlib

import hapimeta


def commands():
  generators_dir = os.path.join(os.path.dirname(__file__), 'hapimeta', 'generators')
  command_names = []
  for name in os.listdir(generators_dir):
    if not name.endswith('.py'):
      continue
    if name == '__init__.py':
      continue
    command_names.append(name[:-3])
  return sorted(command_names)


def main():
  available_commands = commands()
  command, servers = hapimeta.cli(available_commands)
  if command is None:
    command_names = available_commands
  else:
    command_names = [command]

  for command_name in command_names:
    sys.argv = [sys.argv[0]]
    if servers is not None:
      sys.argv.append(','.join(servers))
    module_name = f'hapimeta.generators.{command_name}'
    module = importlib.import_module(module_name)
    module.run()
    hapimeta.error.combine()


if __name__ == '__main__':
  main()