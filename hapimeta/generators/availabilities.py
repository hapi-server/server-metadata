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

  special_chars = {
    'ts': '\u2002', # en space
    'rarrow': '\u2192 ',
    'larrow': '\u2190'
  }
  server_file = os.path.basename(server)

  def newfig(height=None):
    plt.close('all')
    fig, ax = plt.subplots()
    fig.set_figheight(fig_height if height is None else height)
    fig.set_figwidth(fig_width)
    return fig, ax

  def ax_config(ax, starts_min, stops_max, title=None, fixed_rows=False):

    import datetick

    if title is not None:
      ax.set_title(title, fontsize=10, backgroundcolor='white')

    ax.set_xlim([starts_min, stops_max])
    if fixed_rows:
      ax.set_ylim([0.5, lines_per_plot + 0.5])
    ax.set_yticks(ticks=[])

    for pos in ['top', 'bottom', 'left']:
      ax.spines[pos].set_visible(False)

    ax.grid(axis='x', which='minor', alpha=0.5, linestyle=':')
    ax.grid(axis='x', which='major', color='k', alpha=0.5)

    datetick.datetick('x', axes=ax)

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
      plt.savefig(f'{_fname}', bbox_inches='tight', pad_inches=0)
      utilrsw.svg.svglinks(_fname, link_attribs={'target': '_blank'}, debug=cfg['debug_svglinks'])

    if 'png' in cfg['savefig_fmts']:
      _fname = os.path.join(server_dir, 'png', f'{server_file}.{fn}.png')
      if not os.path.exists(os.path.dirname(_fname)):
        os.makedirs(os.path.dirname(_fname))
      log.info(f'Writing {_fname}')
      plt.savefig(f'{_fname}', dpi=cfg['dpi'], bbox_inches='tight', pad_inches=0)

    return f'{server_file}.{fn}'

  def draw(ax, n, lines_per_plot, starts, stops, datasets,
           start_text, max_len=None, row_n=None):
    base = "https://hapi-server.org"
    gid_bar = f'{base}/servers/#server={server}&dataset={id_strip(datasets[n])}'
    gid_txt = f'{base}/plot/?server={server_url}&dataset={id_strip(datasets[n])}&format=gallery&usecache=true&usedatacache=true&mode=thumb'

    if row_n is None:
      row_n = n
    y = lines_per_plot - row_n
    ax.plot([starts[n], stops[n]], [y, y], gid=gid_bar, linewidth=0.5)

    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color = colors[n % len(colors)]
    kwargs = {
      "color": color,
      "alpha": 1,
      "gid": gid_bar
    }
    height = 0.8
    xy = (starts[n], y - height/2)
    width = stops[n] - starts[n]
    rect = plt.Rectangle(xy, width, height, **kwargs)
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
    if stops[n] <= min(starts):
      ax.text(min(starts), y, label, **text_kwargs)
    else:
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

  starts_min = min(starts)
  stops_max = max(stops)


  height = fig_height
  if len(datasets) < lines_per_plot:
    # Delta is expected hight of title and x-axis labels
    # Ideally we would compute exact value.
    delta = 0.5
    height = delta + (fig_height * len(datasets)/ lines_per_plot)
  fig, ax = newfig(height=height)

  fn = 0
  files = []
  row_n = 0
  for n in range(len(datasets)):
    draw(ax, n, lines_per_plot, starts, stops, datasets, start_text, row_n=row_n)
    row_n += 1
    if (n + 1) % lines_per_plot == 0:
      fn = fn + 1
      fn_padded = f'{fn:0{pad}d}'
      title_ = title + f' | {fn}/{n_plots}'
      ax_config(ax, starts_min, stops_max, title_, fixed_rows=True)
      file = savefig(fn_padded)
      files.append(file)

      remaining_lines = len(datasets) - (n + 1)
      if remaining_lines > 0:
        height = fig_height
        if remaining_lines < lines_per_plot:
          height *= remaining_lines / lines_per_plot
        fig, ax = newfig(height=height)
        row_n = 0

  if (n + 1) % lines_per_plot != 0:
    fn = fn + 1
    fn_padded = f'{fn:0{pad}d}'
    title_ = title + f' | {fn}/{n_plots}'
    ax_config(ax, starts_min, stops_max, title_, fixed_rows=False)
    file = savefig(fn_padded)
    files.append(file)

  return files


def html(files, server_dir, server):
  import base64
  from string import Template

  server_file = os.path.basename(server)

  # Read HTML template from external file
  html_template_path = os.path.join(os.path.dirname(__file__), 'availabilities.html')
  with open(html_template_path, 'r', encoding='utf-8') as f:
    template = Template(f.read())

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

  if 'svg' in cfg['savefig_fmts'] and file_svg is not None:
    html_content_svg = template.substitute(
      title=server,
      server_id=server,
      server_file=server_file,
      search_note_display='block',
      divs=divs_svg
    )
    fname = os.path.join(os.path.dirname(file_svg), f'{server}.html')
    write(fname, html_content_svg)

  if 'png' in cfg['savefig_fmts'] and file_png is not None:
    html_content_png = template.substitute(
      title=server,
      server_id=server,
      server_file=server_file,
      search_note_display='none',
      divs=divs_png
    )
    fname = os.path.join(os.path.dirname(file_png), f'{server}.html')
    write(fname, html_content_png)


def process_server(server, catalog_all, max_datasets=None):

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

  if max_datasets is not None:
    datasets = datasets[:max_datasets]

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

  log.info('Generating availability plots')
  args = hapimeta.cli()
  all = hapimeta.all(log)

  dfs = []
  for server in all.keys():
    df = process_server(server, all[server], max_datasets=args.n_datasets)
    hapimeta.error.write(server, 'availabilities', log)
    dfs.append(df)

  dfs = pandas.concat([d for d in dfs if d is not None], ignore_index=True)
  write(os.path.join(hapimeta.DATA_DIR, 'availabilities', 'availabilities.pkl'), dfs)
  write(os.path.join(hapimeta.DATA_DIR, 'availabilities', 'availabilities.csv'), dfs)


if __name__ == '__main__':
  run()
