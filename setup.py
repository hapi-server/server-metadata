import json
from setuptools import setup, find_packages

install_requires = ["hapiplot", "hapiclient", "deepdiff", "GitPython", "isodate"]

try:
  # Will work if utilrsw was already installed, for example via pip install -e .
  import utilrsw
except:
  install_requires.append("utilrsw @ git+https://github.com/rweigel/utilrsw")

try:
  # Will work if tableui was already installed, for example via pip install -e .
  import tableui
except:
  install_requires.append("tableui @ git+https://github.com/rweigel/table-ui")


try:
  # Will work if datetick was already installed, for example via pip install -e .
  import datetick
except:
  install_requires.append("datetick @ git+https://github.com/rweigel/datetick")


version = json.load(open('hapimeta/version.json'))['version']
setup(
  name='hapimeta',
  version=version,
  description='A package for metadata from HAPI servers.',
  author='Bob Weigel and Jeremy Faden',
  author_email='rweigel@gmu.edu',
  packages=find_packages(),
  install_requires=install_requires
)