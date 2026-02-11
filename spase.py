import os
import utilrsw

logger = utilrsw.logger('spase', log_dir='log')

all_file = 'data/catalogs-all.pkl'
servers = utilrsw.read(all_file)

servers_keep = None # All servers
#servers_keep = ["CDAWeb"] # Only these servers
servers_keep = ["TestData3.3"] # Only these servers

def spase_stub(config):
  SchemaURL = config.get("SchemaURL", None)
  Version = config.get("Version")
  Spase = {
    "xmlns": SchemaURL,
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xsi:schemaLocation": f"{SchemaURL} {SchemaURL}/spase-{Version}.xsd",
    "Version": Version,
    "NumericalData": {
      "AccessInformation": [],
      "Parameter": []
    }
  }
  return Spase


def add_NumericalData(Spase, dataset, map):
  NumericalData = utilrsw.map_dict(dataset, map)
  Spase['NumericalData'] = NumericalData
  return None


def add_Parameter(Spase, dataset, map):
  parameters = utilrsw.get_path(dataset, 'info/parameters', sep='/')
  if parameters is not None:
    Parameters = []
    for parameter in parameters:
      Parameter = utilrsw.map_dict(parameter, map)
      Parameters.append(Parameter)
    Spase['NumericalData']['Parameter'] = Parameters
  return None


def add_AccessInformation(Spase, dataset, about, template):
  import copy

  def script_info():
    # TODO: Get languages from https://hapi-server.org/servers/?return=script-options
    languages = ['IDL', 'Javascript', 'MATLAB', 'Python', 'Autoplot', 'curl', 'wget']
    languages = ', '.join(languages)
    language_formats = []
    for language in languages.split(', '):
      language_formats.append(f"x_Script.{language.strip()}")
    return languages, language_formats

  languages, formats = script_info()

  template = copy.deepcopy(template)
  for i in range(len(template)):
    template[i]['AccessURL']['URL'] = template[i]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
    template[i]['AccessURL']['ProductKey'] = dataset['id']

  template[1]['AccessURL']['Description'] = template[1]['AccessURL']['Description'].format(languages=languages)
  template[1]['AccessURL']['Format'] = formats
  Spase['NumericalData']['AccessInformation'] = template
  return None

def add_DOI(Spase, dataset):

  def extract_doi(doi_string):
    DOI = None
    if doi_string.startswith('https://doi.org/'):
      DOI = doi_string[len('https://doi.org/'):]
    if doi_string.startswith('doi:'):
      DOI = doi_string[len('doi:'):]
    return DOI

  #dataset['info']['datasetCitation'] = 'doi:10.1234/dataset1'

  datasetCitation = utilrsw.get_path(dataset, 'info/datasetCitation', sep='/')
  resourceID = utilrsw.get_path(dataset, 'info/resourceID', sep='/')

  if datasetCitation is not None:
    DOI = extract_doi(datasetCitation)
    if DOI is not None:
      Spase['NumericalData']['DOI'] = DOI
  else:
    if resourceID is not None:
      DOI = extract_doi(resourceID)
      if DOI is not None:
        Spase['NumericalData']['DOI'] = DOI

  return None

script_path = os.path.dirname(os.path.realpath(__file__))
out_path = os.path.join(script_path, 'data', 'spase')

config_file = os.path.join(script_path, 'spase.json')
config = utilrsw.read(config_file)

Spase = spase_stub(config["Spase"])

for server in servers:
  if servers_keep is not None and server not in servers_keep:
    continue

  logger.info(f"Processing server: {server}")

  catalog = servers[server]['catalog']
  about = servers[server]['about']
  for dataset in catalog:
    dataset['server'] = server
    dataset['dataset'] = dataset['id']

    #logger.info("Input:\n" + utilrsw.format_dict(dataset, style='json'))

    add_NumericalData(Spase, dataset, config['hapi2spase']['dataset'])
    add_DOI(Spase, dataset)
    add_AccessInformation(Spase, dataset, about, config['AccessInformation'])
    add_Parameter(Spase, dataset, config['hapi2spase']['parameter'])

    #logger.info("Output:\n" + utilrsw.format_dict(Spase, style='json'))

    out_file = os.path.join(out_path, server, f"{dataset['id']}.json")
    logger.debug(f"Writing {out_file}")
    utilrsw.write(out_file, Spase)
