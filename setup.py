import json
from setuptools import setup, find_packages

install_requires = [
  "hapiplot",
  "hapiclient",
  "deepdiff",
  "GitPython",
  "isodate"
]

install_requires.append("utilrsw[net] @ git+https://github.com/rweigel/utilrsw@main")
install_requires.append("tableui @ git+https://github.com/rweigel/table-ui@main")

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
