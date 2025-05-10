__all__ = ['version',
           'mkdir',
           'write',
           'read',
           'utc_now',
           'logger',
           'get',
           'svglinks',
           'version'
        ]

def version():
  import os
  import json
  fname = open(os.path.join(os.path.dirname(__file__),'version.json'))
  return json.load(fname)['version']

__version__ = version()

from utilrsw import mkdir
from utilrsw import write
from utilrsw import read
from utilrsw import utc_now

def logger(file_name=None):
  import os
  import time
  import inspect
  import logging

  # Print to stdout and file_name

  if file_name is None:
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    file_name = os.path.splitext(module.__file__)[0] + ".log"

  mkdir(os.path.dirname(file_name))

  if os.path.exists(file_name):
    os.remove(file_name)

  conf = {
    'handlers': [logging.FileHandler(file_name, 'w', 'utf-8'),
                 logging.StreamHandler()
              ],
    'level': logging.INFO,
    'format': u'%(asctime)s.%(msecs)03dZ %(message)s',
    'datefmt': '%H:%M:%S',
  }
  logging.basicConfig(**conf)

  logging.Formatter.converter = time.gmtime

  return logging.getLogger(__name__)

def get(url, log=None, timeout=10, indent=""):

  assert log is not None, "log keyword argument must be provided"
  # TODO: Handle log=None

  import json
  import requests

  log.info(f"{indent}Getting {url}")
  headers = {'User-Agent': f'hapibot-mirror/{version()}; https://github.com/hapi-server/data-specification/wiki/hapi-bots.md#hapibot-mirror'}
  try:
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()  # Raise an error if response code is not 2xx
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

def svglinks(file, links=None, link_prefix="", link_attribs=None, file_out=None, debug=False):

  import io
  from lxml import etree

  def print_(*args):
    if debug:
      print(*args)

  def get_link(id, links, link_prefix):

    print_(f"  Found <g> element with id = '{id}'")

    if links is None:
      if id.startswith(f'{link_prefix}http'):
        id = id[len(link_prefix):]
        print_(f"    link = '{id}'")
        return id
      else:
        return None

    link = None
    if isinstance(links, dict):
      if id not in links:
        print_(f"  Warning: id starting with $ not in links dict: {id}")
        return None
      link = links[id]

    if callable(links):
      link = links(id)

    if not isinstance(link, str):
      print_(f"  Warning: link for {id} is not a string: {link}")
      return None

    if link is not None:
      print_(f"    link = '{link}'")
      return link

  with open(file, 'r', encoding='utf-8') as svg_file:
    print_("Reading:", file)
    f = io.StringIO()
    f.write(svg_file.read())

  # Parse the SVG content using lxml
  svg_content = f.getvalue().encode('utf-8')
  root = etree.fromstring(svg_content)

  # Find the <g> element with the desired gid
  for element in root.iter():
    id = element.attrib.get('id')

    if id is None:
      continue

    linkable = id.startswith('http') or id.startswith(link_prefix)
    linkable = linkable and str(element.tag).endswith('g')

    if linkable:
      id = element.attrib.get('id')

      link = get_link(id, links, link_prefix)
      if link is None:
        print_("    No link found. Skipping.")
        continue

      attrib = {'href': link}
      if link_attribs is not None:
        attrib.update(link_attribs)

      # Create the <a> element
      a_element = etree.Element('a', attrib=attrib)

      # Wrap the <g> element with the <a> element
      parent = element.getparent()

      if parent is not None:
          # Replace the <g> element with the <a> element
          parent.replace(element, a_element)

      # Append the <g> element as a child of the <a> element
      a_element.append(element)

  # Convert the modified SVG back to a string
  modified_svg = etree.tostring(root, encoding='unicode', pretty_print=True)

  if file_out is not None:
    file = file_out

  # Save the modified SVG content
  with open(file, 'w') as f:
    print_("Writing:", file)
    f.write(modified_svg)

if __name__ == "__main__":
  import matplotlib.pyplot as plt

  links = {
    "$A Line": "https://www.example.com",
    "$A Text": "https://www.example.com"
  }

  fig, ax = plt.subplots()
  line, = ax.plot([1, 2, 3], [4, 5, 2], gid='$A Line')
  ax.text(2, 4, 'My Line', gid='$A Text')

  # Save the plot as SVG
  plt.savefig('links.svg', format='svg')
  plt.close(fig)

  svglinks('svglinks.svg', links, 'svglinks.modified.svg')