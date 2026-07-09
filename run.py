import sys
import importlib

import hapimeta


def _email(to, subject, body):
  import smtplib
  from email.mime.text import MIMEText

  msg = MIMEText(body)
  msg['Subject'] = subject
  msg['From'] = to
  msg['To'] = to

  with smtplib.SMTP('localhost') as server:
    server.send_message(msg, from_addr=to, to_addrs=[to])


def main():
  args = hapimeta.cli()
  if args.command is None:
    command_names = importlib.import_module('hapimeta.cli').commands()
  else:
    command_names = [args.command]

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
    try:
      module_name = f'hapimeta.generators.{command_name}'
      module = importlib.import_module(module_name)
      module.run()
    except Exception as e:
      # Trigger the global exception handler, which the logger is configured to
      # handle by writing the exception to the console and to the log file.
      sys.excepthook(type(e), e, e.__traceback__)
      continue

    hapimeta.error.combine()


if __name__ == '__main__':
  main()
