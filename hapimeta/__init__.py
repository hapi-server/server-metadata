__all__ = ['version', 'config', 'data_dir', 'get', 'logger_kwargs']

def version():
  import os
  import json
  fname = open(os.path.join(os.path.dirname(__file__),'version.json'))
  return json.load(fname)['version']

__version__ = version()

data_dir = 'data'

def logger(base_name):
  import utilrsw
  kwargs = {
    "log_dir": "data/log",
    "console_format": u"%(asctime)s.%(msecs)03dZ %(levelname)s %(message)s",
    "file_format": u"%(levelname)s %(message)s",
    "datefmt": "%H:%M:%S",
    "color": True,
    "debug_logger": False
  }
  return utilrsw.logger(base_name, **kwargs)


def cli():
  # Usage
  #    python abouts.py [server1,server2,...]

  import argparse

  parser = argparse.ArgumentParser(
    description='Process metadata for all servers or a comma-separated subset.',
    epilog='Examples:\n  python abouts.py\n  python abouts.py server1,server2',
    formatter_class=argparse.RawDescriptionHelpFormatter
  )
  parser.add_argument(
    'servers',
    nargs='?',
    default=None,
    help='Comma-separated list of server IDs'
  )

  args, _ = parser.parse_known_args()

  if args.servers is None:
    return None

  servers = [server.strip() for server in args.servers.split(',') if server.strip()]
  print(f"Processing servers: {servers}")
  return servers


def get(url, log=None, timeout=20, retries=3, indent=""):

  assert log is not None, "log keyword argument must be provided"
  # TODO: Handle log=None

  import json
  import requests
  from requests.adapters import HTTPAdapter
  from requests.packages.urllib3.util.retry import Retry

  retries = Retry(total=retries, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])

  log.info(f"{indent}Getting {url}")
  user_agent = f'hapibot-mirror/{version()}; '
  user_agent += 'https://github.com/hapi-server/data-specification/wiki/hapi-bots.md#hapibot-mirror'
  headers = {'User-Agent': user_agent}
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


def config(part, simulate=False):

  cfg = {
    'about': {
      "repo_url": 'https://github.com/hapi-server/servers',
      "repo_dir": 'servers',
      "files": [
        'abouts.json',
        'abouts-dev.json',
        'abouts-test.json'],
      "servers": cli(),  # None => all servers
      "simulate": False, # For debugging, internally simulate changes
      "timeout": 10,     # Request timeout in seconds. Use small # to simulate server/network issues
      "retries": 3       # # of retries for requests. Use zero to simulate server/network issues
    }
  }

  return cfg[part]