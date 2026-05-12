#!/usr/bin/env python3

import re
import sys
import datetime
import subprocess
import threading

from pathlib import Path


ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def strip_ansi(text):
  return ANSI_ESCAPE.sub('', text)


def stream_to_outputs(stream, terminal, log_handle):
  for chunk in iter(stream.readline, ''):
    if not chunk:
      break
    terminal.write(chunk)
    terminal.flush()
    log_handle.write(strip_ansi(chunk))
    log_handle.flush()


def stream_stderr(stream, terminal, log_handle, error_handle):
  for chunk in iter(stream.readline, ''):
    if not chunk:
      break
    terminal.write(chunk)
    terminal.flush()
    clean = strip_ansi(chunk)
    log_handle.write(clean)
    log_handle.flush()
    error_handle.write(clean)
    error_handle.flush()


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

  with log_file.open('a') as log_handle, error_file.open('a') as error_handle:
    process = subprocess.Popen(
      [sys.executable, 'run.py'],
      cwd=repo_dir,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      bufsize=1,
    )

    stdout_thread = threading.Thread(
      target=stream_to_outputs,
      args=(process.stdout, sys.stdout, log_handle),
      daemon=True,
    )
    stderr_thread = threading.Thread(
      target=stream_stderr,
      args=(process.stderr, sys.stderr, log_handle, error_handle),
      daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    stdout_thread.join()
    stderr_thread.join()
    returncode = process.wait()

  return returncode


if __name__ == '__main__':
  raise SystemExit(main())