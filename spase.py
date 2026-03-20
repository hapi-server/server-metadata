import os
import utilrsw

from hapimeta import cli, logger

log = logger('spase')

all_file = 'data/catalogs-all.pkl'
servers = utilrsw.read(all_file)

servers_keep = cli()

# Set to True to read info from data/info directory instead of from the catalog.
# Use this for testing to avoid having to re-run the catalog step after making
# changes to the info files.
reread_info = True

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


def add_Parameter(Spase, dataset, map):
  parameters = utilrsw.get_path(dataset, 'info.parameters')
  if parameters is not None:
    Parameters = []
    for parameter in parameters:
      Parameter = utilrsw.map_dict(parameter, map)
      Parameters.append(Parameter)
    Spase['NumericalData']['Parameter'] = Parameters


def add_AccessInformation(Spase, dataset, about, capabilities, formatMap, template):

  import copy

  def script_info():

    # Defaults to use if update fails.
    languages = ['IDL', 'Javascript', 'MATLAB', 'Python', 'Autoplot', 'curl', 'wget']
    try:
      url = "https://hapi-server.org/servers/?return=script-options"
      response = utilrsw.net.get_json(url)
      languages = {}
      for element in response['data']:
        language = element.get('label', '')
        language = language.split('/')[0]
        languages[language] = True
      languages = list(languages.keys())
    except Exception as e:
      log.warning(f"Unable to get script languages from {url}: {e}")

    languages = ', '.join(languages)
    language_formats = []
    for language in languages.split(', '):
      language_formats.append(f"x_Script.{language.strip()}")

    return languages, language_formats

  def formats(capabilities):
    outputFormats = utilrsw.get_path(capabilities, 'outputFormats', default=['csv'])

    Formats = []
    for fmt in outputFormats:
      if fmt not in formatMap:
        #log.warning(f"Unknown output format: {fmt}. Skipping.")
        continue
      Formats.append(config['formatMap'][fmt])
    return Formats

  def description(about):

    def extra(type):
      desc = ""
      type_capitalized = type.capitalize()
      note = utilrsw.get_path(about, type)
      if note is not None:
        if isinstance(note, str):
          desc = f"{type_capitalized}: {note}"
        if isinstance(note, list):
          notes = ""
          for i, n in enumerate(note):
            notes += f"{i+1}. {n}; "
          notes = notes.rstrip('; ')
          desc = f"{type_capitalized}s: {notes}"
      return desc

    desc = ""
    description = utilrsw.get_path(about, 'description')
    contact = utilrsw.get_path(about, 'contact')
    contactID = utilrsw.get_path(about, 'contactID')

    if description is None and contact is None and contactID is None:
      return None
    if description is not None:
      desc += description

    if contact and contactID:
      if contact == contactID:
        desc = f"{desc} (Contact: {contact})"
      else:
        desc = f"{desc} (Contact: {contact} <{contactID}>)"
    if not contact and contactID:
      desc = f"{desc} (Contact: <{contactID}>)"
    if contact and not contactID:
      desc = f"{desc} (Contact: {contact})"

    serverCitation = utilrsw.get_path(about, 'serverCitation')
    if serverCitation is not None:
      desc = f"{desc}. Server Citation: {serverCitation} (see dataset description for citing the dataset)"

    note = extra('note')
    if note:
      desc = f"{desc}. {note}"

    warning = extra('warning')
    if warning:
      desc = f"{desc}. {warning}"

    return desc + "."

  data_formats = formats(capabilities)

  languages, language_formats = script_info()

  template = copy.deepcopy(template)
  for i in range(len(template)):
    url = template[i]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
    template[i]['AccessURL']['URL'] = url
    template[i]['AccessURL']['ProductKey'] = dataset['id']

  desc = description(about)
  if desc is not None:
    template[0]['AccessURL']['Description'] = desc
  template[0]['AccessURL']['Format'] = data_formats

  desc = template[1]['AccessURL']['Description'].format(languages=languages)
  template[1]['AccessURL']['Description'] = desc
  template[1]['AccessURL']['Format'] = language_formats

  Spase['NumericalData']['AccessInformation'] = template


def add_SpatialMapping(Spase, dataset):

  geoLocation = utilrsw.get_path(dataset, 'info.geoLocation')

  if False and (geoLocation is not None):
    # We discussed putting a warning in the description. This is not a good option
    # because the description will become detached from the value. I think we
    # should just do the conversion calculation and note that the
    # calculation has been made in the description.
    Spase['NumericalData']['SpatialMapping'] = {
      "centerLongitude": geoLocation[0],
      "centerLatitude": geoLocation[1]
    }
    if len(geoLocation) > 2:
      Spase['NumericalData']['SpatialMapping']['centerElevation'] = geoLocation[2]
    desc = "The SpatialMapping values are from the geoLocation object in HAPI metadata. "
    desc += "Warning: In SPASE, centerLongitude and centerLatitude are in defined to be in GEO and "
    desc += "centerElevation in WGS84. In HAPI, their equivalents are defined to be in WGS84. "
    desc += "The values given for centerLongitude and centerLatitude are direct copies "
    desc += "of content in the HAPI geoLocation and have not "
    desc += "been converted from WGS84 to GEO."
    Spase['NumericalData']['SpatialMapping']['Description'] = desc

  point = utilrsw.get_path(dataset, 'info.location.point')
  if point is not None:
    coordinateSystemName = utilrsw.get_path(dataset, 'info.location.coordinateSystemName')
    # TODO: 1. Check coordinateSystemSchema and verify that 'GEO' is a valid 
    #          name and it means the same thing as GEO in SPASE.
    #       2. If vectorComponents, verify that they contain latitude, longitude,
    #          and altitude and adjust what elements of point correspond to 
    #          centerLongitude, centerLongitude, and centerElevation.
    if coordinateSystemName == 'GEO':
      Spase['NumericalData']['SpatialMapping'] = {
        "centerLongitude": point[0],
        "centerLatitude": point[1]
      }
      if len(point) > 2:
        Spase['NumericalData']['SpatialMapping']['centerElevation'] = point[2]


def add_ResourceHeader(Spase, dataset):

  def extract_doi(doi_string):
    DOI = None
    if doi_string.startswith('https://doi.org/'):
      DOI = doi_string[len('https://doi.org/'):]
    if doi_string.startswith('doi:'):
      DOI = doi_string[len('doi:'):]
    return DOI

  def informationURLs(dataset):
    url_template = "https://hapi-server.org/servers/#server={server}&dataset={dataset}"
    url = url_template.format(server=dataset['server'], dataset=dataset['id'])
    InformationURLs = [{
      "Name": "hapi-server.org",
      "URL": url,
      "Description": "hapi-server.org dataset information page"
    }]

    additionalMetadata = utilrsw.get_path(dataset, 'info.additionalMetadata')
    if additionalMetadata is not None:
      if isinstance(additionalMetadata, dict):
        additionalMetadata = [additionalMetadata]

      for additional in additionalMetadata:

        InformationURL = {"Name": "", "URL": ""}
        desc = ""

        if 'contentURL' not in additional and 'content' not in additional:
          log.error(f"{dataset['id']}: additionalMetadata entry missing one of 'contentURL' or 'content'")
          continue

        if 'contentURL' in additional:
          InformationURL["URL"] = additional['contentURL']

        if 'content' in additional:
          url = f"{dataset['server_url']}/info?dataset={dataset['id']}"
          desc = f"Additional metadata content is available in the additionalMetadata node in: {url}"

        if 'name' in additional:
          InformationURL["Name"] = additional['name']
        else:
          InformationURL['Name'] = "Additional metadata"

        if 'aboutURL' in additional:
          desc += f"Metadata description: {additional['aboutURL']}"
        if 'schemaURL' in additional:
          desc += f". Metadata schema: {additional['schemaURL']}."

        note = "The information in this InformationURL node is derived from an additionalMetadata node in HAPI /info response"
        if desc != "":
          InformationURL['Description'] = f"{desc}. {note}"
        else:
          InformationURL['Description'] = note

        InformationURLs.append(InformationURL)

    return InformationURLs

  Spase['NumericalData']['ResourceHeader']["InformationURL"] = informationURLs(dataset)

  datasetCitation = utilrsw.get_path(dataset, 'info.datasetCitation')
  resourceID = utilrsw.get_path(dataset, 'info.resourceID')

  # If not DOI, need to find place for datasetCitation and resourceID in SPASE
  if datasetCitation is not None:
    DOI = extract_doi(datasetCitation)
    if DOI is not None:
      Spase['NumericalData']['ResourceHeader']['DOI'] = DOI
  else:
    if resourceID is not None:
      DOI = extract_doi(resourceID)
      if DOI is not None:
        Spase['NumericalData']['ResourceHeader']['DOI'] = DOI
      else:
        desc = Spase['NumericalData']['ResourceHeader']['Description']
        desc = desc.rstrip('.')
        extra = f"HAPI resourceID: {resourceID}."
        Spase['NumericalData']['ResourceHeader']['Description'] = f"{desc}. {extra}"


script_path = os.path.dirname(os.path.realpath(__file__))
out_path = os.path.join(script_path, 'data', 'spase')

config_file = os.path.join(script_path, 'spase.json')
config = utilrsw.read(config_file)

Spase = spase_stub(config["Spase"])

for server in servers:
  if servers_keep is not None and server not in servers_keep:
    continue

  log.info(f"Processing server: {server}")

  catalog = utilrsw.get_path(servers[server], 'catalog.catalog')
  if catalog is None:
    log.error(f"No catalog found for server: {server}")
    continue

  about = utilrsw.get_path(servers[server], 'about')
  capabilities = utilrsw.get_path(servers[server], 'capabilities')

  for dataset in catalog:

    dataset['server'] = server
    dataset['server_url'] = about['x_url']
    dataset['dataset'] = dataset['id']

    if reread_info:
      info_file = os.path.join(script_path, 'data', 'infos', server, f"{dataset['id']}.json")
      info_dict = utilrsw.read(info_file)
      dataset['info'] = info_dict
      log.info(f"  reread_info = True => overriding info from {all_file} with that in {info_file}.")

    add_NumericalData(Spase, dataset, config['hapi2spase']['dataset'])
    add_ResourceHeader(Spase, dataset)
    add_SpatialMapping(Spase, dataset)
    add_AccessInformation(Spase, dataset, about, capabilities, config['formatMap'], config['AccessInformation'])
    add_Parameter(Spase, dataset, config['hapi2spase']['parameter'])

    out_file = os.path.join(out_path, server, f"{dataset['id']}.json")
    log.debug(f"Writing {out_file}")
    utilrsw.write(out_file, Spase)
