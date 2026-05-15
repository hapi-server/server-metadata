import hapimeta


def logger(base_name):
  import os
  import utilrsw

  kwargs = {
    'log_dir': os.path.join(hapimeta.DATA_DIR, 'log', 'server-metadata'),
    'console_format': u'%(asctime)s.%(msecs)03dZ %(levelname)s [%(name)s] %(message)s',
    'file_format': u'%(levelname)s %(message)s',
    'datefmt': '%H:%M:%S',
    'color': True,
    'debug_logger': False,
  }
  return utilrsw.logger(base_name, **kwargs)