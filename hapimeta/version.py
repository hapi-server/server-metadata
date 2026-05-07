def version():
  import json
  import os

  fname = open(os.path.join(os.path.dirname(__file__), 'version.json'))
  return json.load(fname)['version']