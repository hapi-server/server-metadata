import importlib

from hapimeta.config import config
from hapimeta.version import version

__version__ = version()

DATA_DIR = config('common')['DATA_DIR']

cli = importlib.import_module('hapimeta.cli').cli
error = importlib.import_module('hapimeta.error')
get = importlib.import_module('hapimeta.get').get
logger = importlib.import_module('hapimeta.logger').logger

__all__ = [
  'version',
  '__version__',
  'config',
  'DATA_DIR',
  'get',
  'logger',
  'cli',
  'error',
]