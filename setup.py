import os
import json
from setuptools import setup, find_packages

install_requires = ["hapiplot", "hapiclient", "lxml"]
install_requires.append("datetick @ git+https://github.com/rweigel/datetick")
install_requires.append("utilrsw @ git+https://github.com/rweigel/utilrsw")

version = json.load(open('hapimeta/version.json'))['version']
setup(
  name='hapimeta',
  version=version,
  description='A package for metadata from HAPI servers.',
  author='Bob Weigel, Jeremy Faden',
  author_email='rweigel@gmu.edu',
  packages=find_packages(),
  install_requires=install_requires
)