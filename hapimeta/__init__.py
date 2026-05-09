import importlib
import importlib.metadata

try:
  __version__ = importlib.metadata.version('hapimeta')
except importlib.metadata.PackageNotFoundError:
  __version__ = '0.0.1'


from hapimeta.config import config

DATA_DIR = config('common')['DATA_DIR']

all    = importlib.import_module('hapimeta.all').all
cli    = importlib.import_module('hapimeta.cli').cli
error  = importlib.import_module('hapimeta.error')
get    = importlib.import_module('hapimeta.get').get
logger = importlib.import_module('hapimeta.logger').logger

__all__ = [
  '__version__',
  'config',
  'DATA_DIR',
  'all',
  'get',
  'logger',
  'cli',
  'error',
]