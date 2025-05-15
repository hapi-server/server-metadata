__all__ = ['version', 'get', 'logger_kwargs']

def version():
  import os
  import json
  fname = open(os.path.join(os.path.dirname(__file__),'version.json'))
  return json.load(fname)['version']

__version__ = version()

logger_kwargs = {
  "log_dir": "log",
  "console_format": u"%(asctime)s.%(msecs)03dZ %(levelname)s %(message)s",
  "file_format": u"%(levelname)s %(message)s",
  "datefmt": "%H:%M:%S",
  "color": True
}

def get(url, log=None, timeout=20, indent=""):

  assert log is not None, "log keyword argument must be provided"
  # TODO: Handle log=None

  import json
  import requests
  from requests.adapters import HTTPAdapter
  from requests.packages.urllib3.util.retry import Retry

  retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])

  log.info(f"{indent}Getting {url}")
  headers = {'User-Agent': f'hapibot-mirror/{version()}; https://github.com/hapi-server/data-specification/wiki/hapi-bots.md#hapibot-mirror'}
  session = requests.Session()
  session.mount('http://', HTTPAdapter(max_retries=retries))
  session.mount('https://', HTTPAdapter(max_retries=retries))

  try:
    response = session.get(url, headers=headers, timeout=timeout)
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
