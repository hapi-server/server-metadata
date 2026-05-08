#!/usr/bin/env python3

import re
import sys
import datetime
import subprocess

from pathlib import Path


ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def strip_ansi(text):
  return ANSI_ESCAPE.sub('', text)


def main():
  script_dir = Path(__file__).resolve().parent
  repo_dir = script_dir.parent

  log_dir = repo_dir / 'data' / 'log' / 'crontab'
  log_dir.mkdir(parents=True, exist_ok=True)

  stamp = datetime.datetime.now().strftime('%Y%m%d')
  log_file = log_dir / f'crontab-{stamp}.log'
  error_file = log_dir / f'crontab-{stamp}.error.log'

  lastrun_file = repo_dir / 'data' / 'lastrun.txt'
  lastrun_file.write_text(f"{datetime.datetime.now():%Y-%m-%d}.log\n")

  result = subprocess.run(
    [sys.executable, 'run.py'],
    cwd=repo_dir,
    capture_output=True,
    text=True,
  )

  stdout = strip_ansi(result.stdout)
  stderr = strip_ansi(result.stderr)

  with log_file.open('a') as log_handle:
    if stdout:
      log_handle.write(stdout)
    if stderr:
      log_handle.write(stderr)

  if stderr:
    with error_file.open('a') as error_handle:
      error_handle.write(stderr)

  if stdout:
    sys.stdout.write(stdout)
  if stderr:
    sys.stderr.write(stderr)

  return result.returncode


if __name__ == '__main__':
  raise SystemExit(main())