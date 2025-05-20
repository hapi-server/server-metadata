# Usage:
#   python availability.py [server_id1,server_id2,...]

import os
import sys
import pandas

import utilrsw

from datetime import datetime, timedelta
from hapiclient import hapitime2datetime
from hapimeta import logger_kwargs

log = utilrsw.logger(**logger_kwargs)

debug_layout = False
debug_svglinks = False
# Number of time range bars per plot
lines_per_plot = 50
# File formats to save. 'png' and 'svg' are supported.
savefig_fmts = ['svg', 'png']

dpi        = 300
fig_width  = 3840           # pixels
fig_width  = fig_width/dpi  # inches
fig_height = 2160           # pixels
fig_height = fig_height/dpi # inches

out_dir           = 'data' # Output directory
base_dir          = os.path.join(out_dir, 'availabilities') # Base directory
catalogs_all_file = f'{out_dir}/catalogs-all.pkl' # Input file

def write(fname, data, logger=None):
  try:
    log.info(f"Writing {fname}")
    utilrsw.write(fname, data, logger=logger)
  except Exception as e:
    log.error(f"Error writing {fname}: {e}")
    raise e

def plot(server, server_url, server_dir, title, datasets, starts, stops,
         lines_per_plot=lines_per_plot,
         fig_width=fig_width, fig_height=fig_height):

  import math
  import numpy

  import matplotlib.pyplot as plt
  # The following is needed to prevent Matplotlib from writing
  # text as paths. If text is written as paths, the SVG file will not
  # be searchable using CTRL+F.
  plt.rcParams['svg.fonttype'] = 'none'
  plt.rcParams['font.family'] = 'times new roman'

  from datetick import datetick

  special_chars = {
    'ts': ' ',       # Unicode thin space
    'rarrow': '→ ',  # Unicode right arrow
    'larrow': '←'    # Unicode left arrow
  }

  def newfig():
    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_figheight(fig_height)
    fig.set_figwidth(fig_width)
    return fig, ax

  def config(ax, starts_min, stops_max, title=None, left_margin=None, right_margin=None):

    if title is not None:
      ax.text(0.5, 1.0, title, transform=ax.transAxes, va='top', ha='center', fontsize=10, backgroundcolor='white',)
      #ax.set_title(title)
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
    plt.subplots_adjust(top=1.0, bottom=0.03)

  def id_strip(id):
    for key, value in special_chars.items():
      id = id.strip().replace(value, '')
    return id

  def savefig(fn):

    if 'svg' in savefig_fmts:
      _fname = os.path.join(server_dir, "svg", f"{server}.{fn}.svg")
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f"{_fname}")
      utilrsw.svglinks(_fname, link_attribs={'target': '_blank'}, debug=debug_svglinks)

    if 'png' in savefig_fmts:
      _fname = os.path.join(server_dir, "png", f"{server}.{fn}.png")
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f"{_fname}", dpi=dpi)

    return f"{server}.{fn}"

  def draw(ax, n, starts, stops, datasets, start_text, max_len=None):
    gid_bar = f"https://hapi-server.org/servers/#server={server}&dataset={id_strip(datasets[n])}"
    gid_txt = f"https://hapi-server.org/plot/?server={server_url}&dataset={id_strip(datasets[n])}&format=gallery&usecache=true&usedatacache=true&mode=thumb"

    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color = colors[n % len(colors)]
    line, = ax.plot([starts[n], stops[n]], [n, n], gid=gid_bar, linewidth=0.5)
    rect = plt.Rectangle(
              (starts[n], n - 0.4),
              stops[n] - starts[n],
              0.8,
              color=color, alpha=1, gid=gid_bar)
    rect.set_linewidth(0)
    ax.add_patch(rect)

    if max_len is None:
      label = datasets[n].rstrip()
    else:
      label = f'{datasets[n]:{max_len}s}'

    text_kwargs = {
      #'family': 'monospace', # Causes extra right padding in SVG
      'color': color,
      'verticalalignment': 'center',
      'size': 8,
      'gid': gid_txt,
      'bbox': dict(facecolor='white', alpha=0.5, pad=0, lw=0)
    }
    ax.text(stops[n], n, label, **text_kwargs)
    if start_text[n] is not None:
      text_kwargs['horizontalalignment'] = 'right'
      ax.text(starts[n], n, start_text[n], **text_kwargs)

  n_plots = math.ceil(len(datasets)/lines_per_plot)
  pad = math.ceil(math.log10(n_plots))
  starts_min = numpy.min(starts)
  stops_max = datetime.now() + timedelta(days=5*365)
  starts_min = datetime(1960, 1, 1, 0, 0, 0)
  max_len = 0
  start_text = []
  for ds in range(len(datasets)):
    datasets[ds] = f"{special_chars['ts']}{datasets[ds]}"
    if stops[ds] > stops_max:
      stops[ds] = stops_max
      datasets[ds] = f"{special_chars['rarrow']}{datasets[ds]}"
    if starts[ds] < starts_min:
      starts[ds] = starts_min
      start_text.append(special_chars['larrow'])
    else:
      start_text.append(None)
    max_len = max(max_len, len(datasets[ds]))

  fig, ax = newfig()
  for n in range(len(datasets)):
    draw(ax, n, starts, stops, datasets, start_text, max_len=max_len)

  config(ax, starts_min, stops_max)
  l, b, w, h = ax.get_position().bounds
  if debug_layout:
    file = savefig('all-before-tight-layout')
    print(f"Left margin: {l}")
    print(f"Bottom margin: {b}")
    print(f"Width: {w}")
    print(f"Height: {h}")
  fig.tight_layout()
  l, b, w, h = ax.get_position().bounds
  if debug_layout:
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
    draw(ax, n, starts, stops, datasets, start_text)
    if (n + 1) % lines_per_plot == 0:
      fn = fn + 1
      fn_padded = f"{fn:0{pad}d}"
      title_ = title + f" | {fn}/{n_plots}"
      config(ax, starts_min, stops_max, title_, left_margin, right_margin)
      file = savefig(fn_padded)
      files.append(file)

      fig, ax = newfig()

  # Finish last plot, if needed
  if (n + 1) % lines_per_plot != 0:
    fn = fn + 1
    fn_padded = f"{fn:0{pad}d}"
    title_ = title + f" | {fn}/{n_plots}"
    config(ax, starts_min, stops_max, title_, left_margin, right_margin)
    file = savefig(fn)
    files.append(file)

  return files

def html(files, server_dir):
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
    <style>
      /* Force scrollbar to show on OS-X (so user knows it is scrollable */
      /* https://simurai.com/blog/2011/07/26/webkit-scrollbar */
      /* Needed here for when this page is in an iframe */
      body::-webkit-scrollbar {
        -webkit-appearance: none;
        width: 7px;
        height: 7px;
      }
      body::-webkit-scrollbar-thumb {
          border-radius: 4px;
          background-color: rgba(0,0,0,.5);
          box-shadow: 0 0 1px rgba(255,255,255,.5);
      }
    </style>
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
      Time range of datasets available from the <a href="https://hapi-server.org/servers/#server=TITLE" target="_blank">TITLE</a> HAPI server. 
      <a href="https://hapi-server.org/meta/availabilities/TITLE/TITLE.csv" target="_blank">Time range data</a> | 
      <a href="https://hapi-server.org/meta/availabilities/TITLE/" target="_blank">Plot files</a> |
      <a href="https://github.com/hapi-server/server-metadata" target="_blank">Plot generation code</a>
    SEARCH
    DIVS
  </body>
  </html>
  """

  search = """
    <br>
    <b>Search:</b>
    <ul style="margin-top:0.2em; margin-bottom:0.2em; padding-inline-start: 1.5em;">
      <li>Use <script>document.write(searchKey());</script> to search for a dataset.</li>
      <li>Click a dataset name to view information about dataset.</li>
      <li>Click a bar to view plots of parameters in dataset.</li>
    </ul>
  """

  # Remove leading two spaces from each line
  html_content = "\n".join([line[2:] for line in html_content.split("\n")])
  html_content = html_content[1:] # Remove first line break
  divs_svg = ""
  divs_png = ""
  for file in files:
    if 'svg' in savefig_fmts:
      file_svg = os.path.join(server_dir, "svg", f"{file}.svg")
      with open(file_svg, "rb") as f:
        svg_data = f.read()
        divs_svg += svg_data.decode('utf-8')
      file = os.path.basename(file)
    if 'png' in savefig_fmts:
      file_png = os.path.join(server_dir, "png", f"{file}.png")
      with open(file_png, "rb") as f:
        png_data = f.read()
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        divs_png += f'<img width="100%" src="data:image/png;base64,{png_base64}" alt="{file}">\n'

  html_content = html_content.replace("TITLE", server)

  if 'svg' in savefig_fmts:
    html_content_svg = html_content
    html_content_svg = html_content_svg.replace("DIVS", divs_svg)
    html_content_svg = html_content_svg.replace("SEARCH", search)
    fname = os.path.join(os.path.dirname(file_svg), f'{server}.html')
    write(fname, html_content_svg)

  if 'png' in savefig_fmts:
    html_content_png = html_content
    html_content_png = html_content_png.replace("DIVS", divs_png)
    html_content_png = html_content_png.replace("SEARCH", "")
    fname = os.path.join(os.path.dirname(file_png), f'{server}.html')
    write(fname, html_content_png)

def process_server(server, catalogs_all):

  def extract_time(info, key):
    if key not in info:
      log.error(f"{server} {dataset['id']}: key '{key}' is not in info")
      return None, None

    if info[key] is None:
      log.error(f"{server} {dataset['id']}: info[{key}] is None")
      return None, None

    if info[key].strip() == "":
      log.error(f"{server} {dataset['id']}: info[{key}].strip() = ''")
      return None, None

    hapitime = info[key]
    try:
      dt = hapitime2datetime(hapitime, allow_missing_Z=True)
      dt = dt[0].replace(tzinfo=None)
    except Exception as e:
      import traceback
      trace = traceback.format_exc()
      log.error(f"{server} {dataset['id']}: hapitime2datetime({hapitime}) returned:\n{trace}")
      return None, None

    return info[key], dt

  lines = []
  datasets = []
  starts = []
  stops = []
  log.info(f"{len(catalogs_all['catalog'])} datasets")
  for dataset in catalogs_all['catalog']:

    if 'info' not in dataset:
      log.error(f"{server} {dataset['id']}: No 'info' key")
      print(server, dataset['id'], None, None)
      continue

    info = dataset['info']

    startDate, startDate_datetime = extract_time(info, 'startDate')
    stopDate, stopDate_datetime = extract_time(info, 'stopDate')

    if startDate_datetime is not None and stopDate_datetime is not None:
      line_str = [server, dataset["id"], startDate, stopDate]
      log.info(", ".join(line_str))
      line = [server, dataset["id"], startDate_datetime, stopDate_datetime]
      lines.append(line)
      stops.append(stopDate_datetime)
      starts.append(startDate_datetime)
      datasets.append(dataset['id'])

  df = pandas.DataFrame(lines, columns=["server", "dataset", "start", "stop"])

  server_dir = os.path.join(base_dir, server)
  fname = os.path.join(server_dir, f'{server}.csv')
  write(fname, df)

  #log.info(f"Plotting availability for {server}")
  server_url = catalogs_all['about']['url']
  x_LastUpdate = catalogs_all['x_LastUpdate']
  title = f"{server} | {server_url} | {len(datasets)} datasets | {x_LastUpdate}"
  files = plot(server, server_url, server_dir, title, datasets, starts, stops,
               lines_per_plot=lines_per_plot,
               fig_width=fig_width, fig_height=fig_height)

  for savefig_fmt in savefig_fmts:
    fname = os.path.join(server_dir, savefig_fmt, f"{server}.json")
    log.info(f"Writing {fname}")
    write(fname, files)

  html(files, server_dir)

  return df

catalogs_all = utilrsw.read(catalogs_all_file)

servers_only = None
if len(sys.argv) > 1:
  servers_only = sys.argv[1].split(',')
  log.info(f"Generating availability for {servers_only}")
else:
  log.info(f"Generating availability for all servers in {catalogs_all_file}")

servers = []
for server in catalogs_all.keys():
  if servers_only is not None and server not in servers_only:
    continue
  servers.append(server)

dfs = []
for server in servers:
  df = process_server(server, catalogs_all[server])
  dfs.append(df)
dfs = pandas.concat(dfs, ignore_index=True)
write(f"{base_dir}/availabilities.pkl", df)
write(f"{base_dir}/availabilities.csv", df)

# Remove error log file if empty.
utilrsw.rm_if_empty(os.path.join("log", "availabilities.errors.log"))