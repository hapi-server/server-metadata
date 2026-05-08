# Usage:
#   python availability.py [server_id1,server_id2,...]

import os
import datetime

import pandas

import utilrsw
import hapiclient

import hapimeta

cfg = hapimeta.config('availabilities')
log = hapimeta.logger('availabilities')


def write(fname, data, logger=None):
  if not os.path.exists(os.path.dirname(fname)):
    os.makedirs(os.path.dirname(fname), exist_ok=True)
  try:
    log.info(f'Writing {fname}')
    utilrsw.write(fname, data, logger=logger)
  except Exception as exc:
    log.error(f'Error writing {fname}: {exc}')
    raise exc


def plot(server, server_url, server_dir, title, datasets, starts, stops,
         lines_per_plot=None,
         fig_width=None, fig_height=None):

  if lines_per_plot is None:
    lines_per_plot = cfg['lines_per_plot']
  if fig_width is None:
    fig_width = cfg['fig_width_pixels']/cfg['dpi']
  if fig_height is None:
    fig_height = cfg['fig_height_pixels']/cfg['dpi']

  import math

  import matplotlib.pyplot as plt
  plt.rcParams['svg.fonttype'] = 'none'
  plt.rcParams['font.family'] = ['Times New Roman', 'DejaVu Sans']

  import datetick

  special_chars = {
    'ts': '\u2002',
    'rarrow': '\u2192 ',
    'larrow': '\u2190'
  }
  server_file = os.path.basename(server)

  def newfig():
    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_figheight(fig_height)
    fig.set_figwidth(fig_width)
    return fig, ax

  def config(ax, starts_min, stops_max, title=None, left_margin=None, right_margin=None):

    if title is not None:
      ax.text(0.5, 1.0, title, transform=ax.transAxes, va='top', ha='center', fontsize=10, backgroundcolor='white')
    ax.set_xlim([starts_min, stops_max])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.grid(axis='x', which='minor', alpha=0.5, linestyle=':')
    ax.grid(axis='x', which='major', color='k', alpha=0.5)
    ax.set_yticks(ticks=[])
    datetick.datetick('x')
    if left_margin is not None and right_margin is not None:
      plt.subplots_adjust(left=left_margin, right=right_margin)
    plt.subplots_adjust(top=1.0, bottom=0.03)

  def id_strip(id):
    for key, value in special_chars.items():
      id = id.strip().replace(value, '')
    return id

  def savefig(fn):

    if 'svg' in cfg['savefig_fmts']:
      _fname = os.path.join(server_dir, 'svg', f'{server_file}.{fn}.svg')
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f'{_fname}')
      utilrsw.svg.svglinks(_fname, link_attribs={'target': '_blank'}, debug=cfg['debug_svglinks'])

    if 'png' in cfg['savefig_fmts']:
      _fname = os.path.join(server_dir, 'png', f'{server_file}.{fn}.png')
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f'{_fname}', dpi=cfg['dpi'])

    return f'{server_file}.{fn}'

  def draw(ax, n, lines_per_plot, starts, stops, datasets, start_text, max_len=None):
    gid_bar = f'https://hapi-server.org/servers/#server={server}&dataset={id_strip(datasets[n])}'
    gid_txt = f'https://hapi-server.org/plot/?server={server_url}&dataset={id_strip(datasets[n])}&format=gallery&usecache=true&usedatacache=true&mode=thumb'

    y = lines_per_plot - n
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color = colors[n % len(colors)]
    ax.plot([starts[n], stops[n]], [y, y], gid=gid_bar, linewidth=0.5)
    rect = plt.Rectangle(
              (starts[n], y - 0.5),
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
      'color': color,
      'verticalalignment': 'center',
      'size': 8,
      'gid': gid_txt,
      'bbox': dict(facecolor='white', alpha=0.5, pad=0, lw=0)
    }
    ax.text(stops[n], y, label, **text_kwargs)
    if start_text[n] is not None:
      text_kwargs['horizontalalignment'] = 'right'
      ax.text(starts[n], y, start_text[n], **text_kwargs)

  n_plots = math.ceil(len(datasets)/lines_per_plot)
  pad = max(1, math.ceil(math.log10(n_plots + 1)))
  stops_max = datetime.datetime.now() + datetime.timedelta(days=5*365)
  starts_min = datetime.datetime(1960, 1, 1, 0, 0, 0)
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
    draw(ax, n, lines_per_plot, starts, stops, datasets, start_text, max_len=max_len)

  config(ax, starts_min, stops_max)
  left_margin, bottom_margin, width, height = ax.get_position().bounds
  if cfg['debug_layout']:
    savefig('all-before-tight-layout')
    print(f'Left margin: {left_margin}')
    print(f'Bottom margin: {bottom_margin}')
    print(f'Width: {width}')
    print(f'Height: {height}')
  fig.tight_layout()
  left_margin, bottom_margin, width, height = ax.get_position().bounds
  if cfg['debug_layout']:
    savefig('all-after-tight-layout')
    print(f'Left margin: {left_margin}')
    print(f'Bottom margin: {bottom_margin}')
    print(f'Width: {width}')
    print(f'Height: {height}')
  right_margin = width + left_margin

  fn = 0
  files = []
  fig, ax = newfig()
  for n in range(len(datasets)):
    draw(ax, n, lines_per_plot, starts, stops, datasets, start_text)
    if (n + 1) % lines_per_plot == 0:
      fn = fn + 1
      fn_padded = f'{fn:0{pad}d}'
      title_ = title + f' | {fn}/{n_plots}'
      config(ax, starts_min, stops_max, title_, left_margin, right_margin)
      file = savefig(fn_padded)
      files.append(file)

      fig, ax = newfig()

  if (n + 1) % lines_per_plot != 0:
    fn = fn + 1
    fn_padded = f'{fn:0{pad}d}'
    title_ = title + f' | {fn}/{n_plots}'
    config(ax, starts_min, stops_max, title_, left_margin, right_margin)
    file = savefig(fn_padded)
    files.append(file)

  return files


def html(files, server_dir, server):
  import base64
  server_file = os.path.basename(server)

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
      Time range of datasets available from the <a href="https://hapi-server.org/servers/#server=SERVER_ID" target="_blank">SERVER_ID</a> HAPI server. 
      <a href="https://hapi-server.org/meta/availabilities/SERVER_ID/SERVER_FILE.csv" target="_blank">Time range data</a> | 
      <a href="https://hapi-server.org/meta/availabilities/SERVER_ID/" target="_blank">Plot files</a> |
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

  html_content = '\n'.join([line[2:] for line in html_content.split('\n')])
  html_content = html_content[1:]
  divs_svg = ''
  divs_png = ''
  file_svg = None
  file_png = None
  for file in files:
    if 'svg' in cfg['savefig_fmts']:
      file_svg = os.path.join(server_dir, 'svg', f'{file}.svg')
      with open(file_svg, 'rb') as fobj:
        svg_data = fobj.read()
        divs_svg += svg_data.decode('utf-8')
      file = os.path.basename(file)
    if 'png' in cfg['savefig_fmts']:
      file_png = os.path.join(server_dir, 'png', f'{file}.png')
      with open(file_png, 'rb') as fobj:
        png_data = fobj.read()
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        divs_png += f'<img width="100%" src="data:image/png;base64,{png_base64}" alt="{file}">\n'

  html_content = html_content.replace('SERVER_ID', server)
  html_content = html_content.replace('SERVER_FILE', server_file)

  if 'svg' in cfg['savefig_fmts'] and file_svg is not None:
    html_content_svg = html_content
    html_content_svg = html_content_svg.replace('DIVS', divs_svg)
    html_content_svg = html_content_svg.replace('SEARCH', search)
    fname = os.path.join(os.path.dirname(file_svg), f'{server}.html')
    write(fname, html_content_svg)

  if 'png' in cfg['savefig_fmts'] and file_png is not None:
    html_content_png = html_content
    html_content_png = html_content_png.replace('DIVS', divs_png)
    html_content_png = html_content_png.replace('SEARCH', '')
    fname = os.path.join(os.path.dirname(file_png), f'{server}.html')
    write(fname, html_content_png)


def process_server(server, catalog_all):

  def extract_time(info, key):
    if key not in info:
      hapimeta.error.store(server, dataset['id'], f"key '{key}' is not in info.", log)
      return None, None

    if info[key] is None:
      hapimeta.error.store(server, dataset['id'], f'info[{key}] not found.', log)
      return None, None

    if info[key].strip() == '':
      hapimeta.error.store(server, dataset['id'], f"info[{key}].strip() == ''", log)
      return None, None

    hapitime = info[key]
    try:
      dt = hapiclient.hapitime2datetime(hapitime, allow_missing_Z=True)
      dt = dt[0].replace(tzinfo=None)
    except Exception:
      import traceback
      trace = traceback.format_exc()
      msg = f'hapitime2datetime({hapitime}) returned:\n{trace}'
      hapimeta.error.store(server, dataset['id'], msg, log)
      return None, None

    return info[key], dt

  lines = []
  ids = []
  starts = []
  stops = []

  datasets = utilrsw.get_path(catalog_all, 'catalog/catalog', sep='/')
  if datasets is None:
    log.info(f'{server}: No datasets found in catalog')
    return None

  log.info(f'{server}: {len(datasets)} datasets')
  for dataset in datasets:

    if 'id' not in dataset:
      hapimeta.error.store(server, '_', "No 'id' key in dataset object", log)
      continue

    log.info(f"  Processing dataset: {dataset['id']}")

    if 'info' not in dataset:
      hapimeta.error.store(server, dataset['id'], 'Missing /info response data.', log)
      continue

    info = dataset['info']

    startDate, startDate_datetime = extract_time(info, 'startDate')
    stopDate, stopDate_datetime = extract_time(info, 'stopDate')

    if startDate_datetime is not None and stopDate_datetime is not None:
      line_str = [server, dataset['id'], startDate, stopDate]
      log.info('    ' + ', '.join(line_str))
      line = [server, dataset['id'], startDate_datetime, stopDate_datetime]
      lines.append(line)
      stops.append(stopDate_datetime)
      starts.append(startDate_datetime)
      ids.append(dataset['id'])

  df = pandas.DataFrame(lines, columns=['server', 'dataset', 'start', 'stop'])

  server_dir = os.path.join(hapimeta.DATA_DIR, 'availabilities', server)
  server_file = os.path.basename(server)
  fname = os.path.join(server_dir, f'{server_file}.csv')
  write(fname, df)

  if len(ids) == 0:
    log.info(f'{server}: No datasets with valid startDate and stopDate found in catalog')
    return df

  log.info('Plotting availabilities')

  server_url = catalog_all['about']['x_url']
  x_LastUpdate = catalog_all['catalog'].get('x_LastUpdate', '')
  title = f'{server} | {server_url} | {len(ids)} datasets | {x_LastUpdate}'

  if cfg['max_datasets'] is not None and len(ids) > cfg['max_datasets']:
    ids = ids[:cfg['max_datasets']]
    starts = starts[:cfg['max_datasets']]
    stops = stops[:cfg['max_datasets']]

  files = plot(server, server_url, server_dir, title, ids, starts, stops,
               lines_per_plot=cfg['lines_per_plot'],
               fig_width=cfg['fig_width_pixels']/cfg['dpi'],
               fig_height=cfg['fig_height_pixels']/cfg['dpi'])

  for savefig_fmt in cfg['savefig_fmts']:
    fname = os.path.join(server_dir, savefig_fmt, f'{server_file}.json')
    log.info(f'Writing {fname}')
    write(fname, files)

  html(files, server_dir, server)

  return df


def run():
  args = hapimeta.cli()
  servers_only = args.servers
  catalogs_all, catalogs_all_file = hapimeta.catalogs_all(log, use_remote_catalog=args.use_remote_catalog)
  if servers_only:
    log.info(f'Generating availability for {servers_only}')
  else:
    log.info(f'Generating availability for all servers in {catalogs_all_file}')

  servers = []
  for server in catalogs_all.keys():
    if servers_only is not None and server not in servers_only:
      continue
    servers.append(server)

  if len(servers) == 0:
    log.error(f'No servers to process. Possible servers: {catalogs_all.keys()}')
    exit(1)

  dfs = []
  for server in servers:
    df = process_server(server, catalogs_all[server])
    hapimeta.error.write(server, 'availabilities', log)
    dfs.append(df)

  dfs = pandas.concat([d for d in dfs if d is not None], ignore_index=True)
  write(os.path.join(hapimeta.DATA_DIR, 'availabilities', 'availabilities.pkl'), dfs)
  write(os.path.join(hapimeta.DATA_DIR, 'availabilities', 'availabilities.csv'), dfs)


if __name__ == '__main__':
  run()