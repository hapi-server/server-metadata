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
      body = f"Error running {module_name}: {e}"
      print(body)
      if args.email_on_exception:
        try:
          _email('rweigel@gmu.edu', "Uncaught hapimeta/run.py exception", body)
        except Exception as e2:
          print(f"Error sending email: {e2}")
      continue
    hapimeta.error.combine()


if __name__ == '__main__':
  main()
