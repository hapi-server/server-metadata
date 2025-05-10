# Usage:
#   python availability.py [server_id1,server_id2,...]

import os
import sys
import pickle

from datetime import datetime, timedelta, timezone

from hapimeta import logger, svglinks, write
from hapiclient import hapitime2datetime

log = logger()

max_workers    = 1      # Number of servers to process in parallel
lines_per_plot = 50     # Number of time range plots per page
# File formats to save. 'png' and 'svg' are supported.
savefig_fmts = ['svg', 'png']

dpi        = 300
fig_width  = 3840           # pixels
fig_width  = fig_width/dpi  # inches
fig_height = 2160           # pixels
fig_height = fig_height/dpi # inches

out_dir      = 'data/availability'     # Output directory
catalogs_all = 'data/catalogs-all.pkl' # Input file

all = True
if len(sys.argv) > 1:
  all = False
  servers_only = sys.argv[1].split(',')
  log.info(f"Generating availability for '{servers_only}'")
else:
  log.info(f"Generating availability for all servers in {catalogs_all}")


with open(catalogs_all, 'rb') as f:
  catalogs_all = pickle.load(f)

def _write(fname, data, logger=None):
  try:
    log.info(f"Writing {fname}")
    write(fname, data, logger=logger)
  except Exception as e:
    log.error(f"Error writing {fname}: {e}")
    raise e

def plot(server, server_url, title, datasets, starts, stops,
         lines_per_plot=lines_per_plot,
         fig_width=fig_width, fig_height=fig_height):

  import math
  import numpy

  import matplotlib.pyplot as plt
  #matplotlib.set_loglevel('warning')
  # The following is needed to prevent Matplotlib from writing
  # text as paths. If text is written as paths, the SVG file will not
  # be searchable using CTRL+F.
  plt.rcParams['svg.fonttype'] = 'none'

  from datetick import datetick

  special_chars = {
    'en': ' ',       # Unicode en space # https://unicode-explorer.com/c/2002
    'rarrow': '→ ',  # Unicode right arrow
    'larrow': '←'    # Unicode left arrow
  }

  def newfig():
    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_figheight(fig_height)
    fig.set_figwidth(fig_width)
    return fig, ax

  def config(ax, starts_min, stops_max, title, n_plots, fn_padded=None, left_margin=None, right_margin=None):

    if fn_padded is not None:
      title = f'{title}    page {fn_padded}/{n_plots}'
    ax.set_title(title)
    ax.set_xlim([starts_min, stops_max])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.grid(axis='x', which='minor', alpha=0.5, linestyle=':')
    ax.grid(axis='x', which='major', color='k', alpha=0.5)
    ax.set_yticks(ticks=[])
    datetick('x')
    if left_margin is not None and right_margin is not None:
      plt.subplots_adjust(left=left_margin, right=right_margin)
    plt.subplots_adjust(top=0.93, bottom=0.05)

  def id_strip(id):
    for key, value in special_chars.items():
      id = id.replace(value, '')
    return id

  def savefig(fn):
    base_dir = os.path.join(out_dir, server)

    if 'svg' in savefig_fmts:
      _fname = os.path.join(base_dir, "svg", f"{server}.{fn}.svg")
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f"{_fname}")
      svglinks(_fname, link_attribs={'target': '_blank'}, debug=debug)

    if 'png' in savefig_fmts:
      _fname = os.path.join(base_dir, "png", f"{server}.{fn}.png")
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f"{_fname}", dpi=dpi)

    return f"{server}.{fn}"

  def draw(ax, n, starts, stops, datasets, start_text, max_len):
    gid_bar = f"https://hapi-server.org/servers/#server={server}&dataset={id_strip(datasets[n])}"
    gid_txt = f"https://hapi-server.org/plot/?server={server_url}&dataset={id_strip(datasets[n])}&format=gallery&usecache=true&usedatacache=true&mode=thumb"

    line, = ax.plot([starts[n], stops[n]], [n, n], gid=gid_bar, linewidth=5)
    label = f'{datasets[n]:{max_len}s}'

    text_kwargs = {
      'family': 'monospace',
      'color': line.get_color(),
      'verticalalignment': 'center',
      'size': 8,
      'gid': gid_txt
    }
    ax.text(stops[n], n, label, **text_kwargs)
    if start_text[n] is not None:
      text_kwargs['horizontalalignment'] = 'right'
      ax.text(starts[n], n, start_text[n], **text_kwargs)

  n_plots = math.ceil(len(datasets)/lines_per_plot)
  pad = math.ceil(math.log10(n_plots))
  starts_min = numpy.min(starts)
  stops_max = datetime.now(timezone.utc) + timedelta(days=5*365)
  starts_min = datetime(1960, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
  max_len = 0
  start_text = []
  for ds in range(len(datasets)):
    # prefix with unicode em space
    #   https://unicode-explorer.com/c/2002
    # is needed, otherwise first letter overlaps with bar.
    datasets[ds] = f"{special_chars['en']}{datasets[ds]}"
    if stops[ds] > stops_max:
      stops[ds] = numpy.array([stops_max])
      datasets[ds] = f"{special_chars['rarrow']}{datasets[ds]}"
    if starts[ds] < starts_min:
      starts[ds] = numpy.array([starts_min])
      start_text.append(special_chars['larrow'])
    else:
      start_text.append(None)
    max_len = max(max_len, len(datasets[ds]))

  fig, ax = newfig()
  for n in range(len(datasets)):
    draw(ax, n, starts, stops, datasets, start_text, max_len)

  debug = False
  config(ax, starts_min, stops_max, title, n_plots)
  l, b, w, h = ax.get_position().bounds
  if debug:
    file = savefig('all-before-tight-layout')
    print(f"Left margin: {l}")
    print(f"Bottom margin: {b}")
    print(f"Width: {w}")
    print(f"Height: {h}")
  fig.tight_layout()
  l, b, w, h = ax.get_position().bounds
  if debug:
    file = savefig('all-after-tight-layout')
    print(f"Left margin: {l}")
    print(f"Bottom margin: {b}")
    print(f"Width: {w}")
    print(f"Height: {h}")
  # 2*l instead of l so we have the same margin on the right as on the left
  # (instead of zero on right)
  right_margin = w+l
  left_margin = l

  fn = 0
  files = []
  fig, ax = newfig()
  for n in range(len(datasets)):
    draw(ax, n, starts, stops, datasets, start_text, max_len)
    if (n + 1) % lines_per_plot == 0:
      fn = fn + 1
      fn_padded = f"{fn:0{pad}d}"
      config(ax, starts_min, stops_max, title, n_plots, fn_padded, left_margin, right_margin)
      file = savefig(fn_padded)
      files.append(file)

      fig, ax = newfig()

  # Finish last plot, if needed
  if (n + 1) % lines_per_plot != 0:
    fn = fn + 1
    fn_padded = f"{fn:0{pad}d}"
    config(ax, starts_min, stops_max, title, n_plots, fn_padded, left_margin, right_margin)
    file = savefig(fn)
    files.append(file)

  return files

def html(files):
  import base64

  # Create the HTML content with the embedded PNG data
  html_content = """
  <!DOCTYPE html>
  <html lang="en">
  <script>
  function searchKey() {
    if (navigator.platform.toUpperCase().startsWith("MAC")) {
      return "⌘+F";
    }
    return "Ctrl+F";
  }
  </script>
  <head>
    <link rel="icon" href="data:image/x-icon;base64,AAABAAEAEBAQAAEABAAoAQAAFgAAACgAAAAQAAAAIAAAAAEABAAAAAAAgAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAA/4QAAA0ODwAASP8Ab/8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACIiIgAAAAAAAAAAAAAAAAAAAAAAAAAAADMzMzMzMwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARERERAAAAAAAAAAAAAAAAAAAAAAAAAAAEREREREREREAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//wAA//8AAAP/AAD//wAA//8AAAAPAAD//wAA//8AAP//AAAA/wAA//8AAP//AAAAAAAA//8AAP//AAD//wAA">
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-5X7EXZ3BBW"></script><script>window.dataLayer = window.dataLayer || [];function gtag(){dataLayer.push(arguments);} gtag("js", new Date());gtag("config", "G-5X7EXZ3BBW");</script>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
    <meta name="keywords" content="TITLE HAPI Heliophysics Data Availability UI">
    <meta name="description"
      content="HAPI Server Availability for TITLE; https://github.com/hapi-server/servers">
    <meta name="keywords" content="TITLE">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITLE</title>
  </head>
  <body>
    <h1>TITLE</h1>
    <p>
      Time range of datasets available from the <a href="https://hapi-server.org/servers/#server=TITLE" target="_blank">TITLE</a> HAPI server.
    </p>
    <ul>
      <li>Data for plots: <a href="../TITLE.csv" target="_blank">TITLE.csv</a></li>
      <li><a href="../" target="_blank">Plot files</a></li>
      <li><a href="https://github.com/hapi-server/server-metadata" target="_blank">Plot generation code</a></li>
    </ul>
    SEARCH
    DIVS
  </body>
  </html>
  """

  search = """
    <h2>Search</h2>
    <ul>
      <li>Use <script>document.write(searchKey());</script> to search for a dataset.</li>
      <li>Click a dataset name to view information about dataset.</li>
      <li>Click a bar to view plots of parameters in dataset.</li>
    </ul>
  """

  # Remove leading and trailing whitespace from each line
  html_content = "\n".join([line.strip() for line in html_content.split("\n")])

  divs_svg = ""
  divs_png = ""
  for file in files:
    if 'svg' in savefig_fmts:
      file_svg = os.path.join(out_dir, server, "svg", f"{file}.svg")
      with open(file_svg, "rb") as f:
        svg_data = f.read()
        divs_svg += svg_data.decode('utf-8')
      file = os.path.basename(file)
      divs_svg += f'<img width="100%" src="{file}" alt="{file}">\n'
    if 'png' in savefig_fmts:
      file_png = os.path.join(out_dir, server, "png", f"{file}.png")
      with open(file_png, "rb") as f:
        png_data = f.read()
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        divs_png += f'<img width="100%" src="data:image/png;base64,{png_base64}" alt="{file}">\n'

  html_content = html_content.replace("TITLE", server)

  if 'svg' in savefig_fmts:
    html_content_svg = html_content
    html_content_svg = html_content_svg.replace("DIVS", divs_svg)
    html_content_svg = html_content_svg.replace("SEARCH", search)
    fname = f"{out_dir}/{server}/svg/{server}.html"
    _write(fname, html_content_svg)

  if 'png' in savefig_fmts:
    html_content_png = html_content
    html_content_png = html_content_png.replace("DIVS", divs_png)
    html_content_png = html_content_png.replace("SEARCH", "")
    fname = f"{out_dir}/{server}/png/{server}.html"
    _write(fname, html_content_png)

def process_server(server, catalogs_all):

  def extract_time(info, key):
    if key not in info:
      log.error(f"{server}/{dataset['id']}: key '{key}' not in info")
      return None, None

    if info[key].strip() == "":
      log.error(f"{server}/{dataset['id']}: info[{key}].strip() = ''")
      return None, None

    hapitime = info[key]
    try:
      dt = hapitime2datetime(hapitime, allow_missing_Z=True)
    except e:
      import traceback
      trace = traceback.format_exc()
      log.error(f"{server}/{dataset['id']}: hapitime2datetime({hapitime}) returned:\n{trace}")
      return hapitime, None

    return info[key], dt

  if not all and server not in servers_only:
    return

  lines = ["dataset,start,stop"]
  datasets = []
  starts = []
  stops = []
  log.info(f"{len(catalogs_all['catalog'])} datasets")
  for dataset in catalogs_all['catalog']:
    if 'info' not in dataset:
      log.error(f'No info node for {server}/{dataset["id"]}')
      print(server, dataset['id'], None, None)
      continue

    info = dataset['info']

    startDate, startDate_datetime = extract_time(info, 'startDate')
    if startDate is None:
      startDate = 'Error'
    stopDate, stopDate_datetime = extract_time(info, 'stopDate')
    if stopDate is None:
      stopDate = 'Error'

    line = f"{dataset['id']},{startDate},{stopDate}"
    lines.append(line)
    log.info(line.replace(",", "\t"))

    if startDate_datetime is not None and stopDate_datetime is not None:
      stops.append(stopDate_datetime)
      starts.append(startDate_datetime)
      datasets.append(dataset['id'])

  fname = f"{out_dir}/{server}/{server}.csv"
  _write(fname, "\n".join(lines))

  #log.info(f"Plotting availability for {server}")
  server_url = catalogs_all['x_URL']
  x_LastUpdate = catalogs_all['x_LastUpdate']
  title = f"{server}: {server_url}   {len(datasets)} datasets\n{x_LastUpdate}"
  files = plot(server, server_url, title, datasets, starts, stops,
               lines_per_plot=lines_per_plot,
               fig_width=fig_width, fig_height=fig_height)

  for savefig_fmt in savefig_fmts:
    fname = os.path.join(out_dir, server, savefig_fmt, f"{server}.json")
    log.info(f"Writing {fname}")
    _write(fname, files)

  html(files)

if max_workers == 1:
  for server in catalogs_all.keys():
    process_server(server, catalogs_all[server])
else:
  from concurrent.futures import ThreadPoolExecutor
  def call(server):
    process_server(server, catalogs_all[server])
  with ThreadPoolExecutor(max_workers=max_workers) as pool:
    pool.map(call, catalogs_all.keys())
