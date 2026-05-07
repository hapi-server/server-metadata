from hapimeta.version import version


def get(url, log=None, timeout=20, retries=3, indent=''):

  assert log is not None, 'log keyword argument must be provided'
  # TODO: Handle log=None

  import json
  import requests
  from requests.adapters import HTTPAdapter
  from requests.packages.urllib3.util.retry import Retry

  retries = Retry(total=retries, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])

  log.info(f'{indent}Getting {url}')
  user_agent = f'hapibot-mirror/{version()}; '
  user_agent += 'https://github.com/hapi-server/data-specification/wiki/hapi-bots.md#hapibot-mirror'
  headers = {'User-Agent': user_agent}
  session = requests.Session()
  session.mount('http://', HTTPAdapter(max_retries=retries))
  session.mount('https://', HTTPAdapter(max_retries=retries))

  try:
    response = session.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
  except Exception as exc:
    log.error(f'{indent}Error: {exc}')
    raise exc
  log.info(f'{indent}Got {url}')

  try:
    data = json.loads(response.text)
  except json.JSONDecodeError as exc:
    log.error(f'{indent}Error parsing JSON from {url}:\n  {exc}')
    raise exc
  return data