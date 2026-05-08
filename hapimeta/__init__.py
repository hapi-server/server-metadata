import importlib
from importlib.metadata import PackageNotFoundError, version as package_version

from hapimeta.config import config

try:
  __version__ = package_version('hapimeta')
except PackageNotFoundError:
  __version__ = '0.0.1'

DATA_DIR = config('common')['DATA_DIR']

catalogs_all = importlib.import_module('hapimeta.catalogs_all').catalogs_all
cli = importlib.import_module('hapimeta.cli').cli
error = importlib.import_module('hapimeta.error')
get = importlib.import_module('hapimeta.get').get
logger = importlib.import_module('hapimeta.logger').logger

__all__ = [
  '__version__',
  'config',
  'DATA_DIR',
  'catalogs_all',
  'get',
  'logger',
  'cli',
  'error',
]