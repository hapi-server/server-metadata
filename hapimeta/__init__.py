__all__ = ['version',
           'mkdir',
           'write',
           'read',
           'utc_now',
           'logger',
           'get',
           'svglinks',
           'version'
        ]

def version():
  import os
  import json
  fname = open(os.path.join(os.path.dirname(__file__),'version.json'))
  return json.load(fname)['version']

__version__ = version()

from utilrsw import mkdir
from utilrsw import write
from utilrsw import read
from utilrsw import utc_now
from utilrsw import svglinks

def logger(file_name=None):
  import os
  import time
  import inspect
  import logging

  # Print to stdout and file_name

  if file_name is None:
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    file_name = os.path.splitext(module.__file__)[0] + ".log"

  mkdir(os.path.dirname(file_name))

  if os.path.exists(file_name):
    os.remove(file_name)

  conf = {
    'handlers': [logging.FileHandler(file_name, 'w', 'utf-8'),
                 logging.StreamHandler()
              ],
    'level': logging.INFO,
    'format': u'%(asctime)s.%(msecs)03dZ %(message)s',
    'datefmt': '%H:%M:%S',
  }
  logging.basicConfig(**conf)

  logging.Formatter.converter = time.gmtime

  return logging.getLogger(__name__)

def get(url, log=None, timeout=20, indent=""):

  assert log is not None, "log keyword argument must be provided"
  # TODO: Handle log=None

  import json
  import requests

  log.info(f"{indent}Getting {url}")
  headers = {'User-Agent': f'hapibot-mirror/{version()}; https://github.com/hapi-server/data-specification/wiki/hapi-bots.md#hapibot-mirror'}
  try:
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status() # Raise an error if response code is not 2xx
  except Exception as e:
    log.error(f"{indent}Error: {e}")
    raise e
  log.info(f"{indent}Got {url}")

  try:
    data = json.loads(response.text)
  except json.JSONDecodeError as e:
    log.error(f"{indent}Error parsing JSON from {url}:\n  {e}")
    raise e
  return data

