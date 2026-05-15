import os
import utilrsw

import hapimeta

cfg = hapimeta.config('spase')
log = hapimeta.logger('spase')

def spase(server_id, server_meta, max_datasets=None):

  Spase = _spase_stub()

  catalog = utilrsw.get_path(server_meta, 'catalog.catalog')
  if catalog is None:
    log.error(f"No catalog found for server '{server_id}' in catalogs-all.pkl. Skipping server.")
    return

  if max_datasets is not None:
    catalog = catalog[:max_datasets]

  log.info(f'  {len(catalog)} datasets')

  about = server_meta.get('about', None)
  capabilities = server_meta.get('capabilities', None)

  out_path = os.path.join(hapimeta.DATA_DIR, 'spase')

  Spase = _spase_stub()

  for idx, dataset in enumerate(catalog):
    dataset['server'] = server_id
    dataset['server_url'] = about['x_url']
    dataset['dataset'] = dataset['id']

    log.info(f"  {idx+1}. {dataset['id']}")

    if cfg['reread_info']:
      info_dir = os.path.join(hapimeta.DATA_DIR, cfg['info_path'], server_id)
      info_file = os.path.join(info_dir, f"{dataset['id']}.json")

      try:
        info_dict = utilrsw.read(info_file)
      except Exception:
        msg = f"  reread_info = True but unable to read info file {info_file} "
        msg += f"for server {server_id}, dataset {dataset['id']}. Using info from catalog."
        log.error(msg)
        continue
      dataset['info'] = info_dict
      log.info(f"  reread_info = True => overriding info from catalogs-all.pkl with that in {info_file}.")

    _add_NumericalData(Spase, dataset, cfg['config']['hapi2spase']['dataset'])
    _add_ResourceHeader(Spase, dataset, about)
    _add_SpatialMapping(Spase, dataset)
    _add_AccessInformation(Spase, dataset, about, capabilities, cfg['config']['formatMap'], cfg['config']['AccessInformation'])
    _add_Parameter(Spase, dataset, cfg['config']['hapi2spase']['parameter'])

    out_file = os.path.join(out_path, server_id, f"{dataset['id']}.json")
    log.info(f'Writing {out_file}')
    utilrsw.write(out_file, Spase)

  return Spase


def run():

  log.info('Generating SPASE')
  args = hapimeta.cli()
  all = hapimeta.all(log)

  for server_id in all.keys():
    log.info(f'{server_id}')
    spase(server_id, all[server_id], max_datasets=args.n_datasets)


def _spase_stub():
  config = cfg['config']['Spase']
  SchemaURL = config.get('SchemaURL', None)
  Version = config.get('Version')
  Spase = {
    'xmlns': SchemaURL,
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xsi:schemaLocation': f'{SchemaURL} {SchemaURL}/spase-{Version}.xsd',
    'Version': Version,
    'NumericalData': {
      'AccessInformation': [],
      'Parameter': []
    }
  }
  return Spase


def _add_NumericalData(Spase, dataset, map):
  NumericalData = utilrsw.map_dict(dataset, map)
  Spase['NumericalData'] = NumericalData


def _add_Parameter(Spase, dataset, map):
  parameters = utilrsw.get_path(dataset, 'info.parameters')
  if parameters is not None:
    Parameters = []
    for parameter in parameters:
      Parameter = utilrsw.map_dict(parameter, map)
      Parameters.append(Parameter)
    Spase['NumericalData']['Parameter'] = Parameters


def _add_AccessInformation(Spase, dataset, about, capabilities, formatMap, template):
  import copy

  def script_info():
    languages = ['IDL', 'Javascript', 'MATLAB', 'Python', 'Autoplot', 'curl', 'wget']
    try:
      url = 'https://hapi-server.org/servers/?return=script-options'
      response = utilrsw.net.get_json(url)
      languages = {}
      for element in response['data']:
        language = element.get('label', '')
        language = language.split('/')[0]
        languages[language] = True
      languages = list(languages.keys())
    except Exception as e:
      log.warning(f'Unable to get script languages from {url}: {e}')

    languages = ', '.join(languages)
    language_formats = []
    for language in languages.split(', '):
      language_formats.append(f'x_Script.{language.strip()}')

    return languages, language_formats

  def formats(capabilities):
    outputFormats = utilrsw.get_path(capabilities, 'outputFormats', default=['csv'])

    Formats = []
    for fmt in outputFormats:
      if fmt not in formatMap:
        continue
      Formats.append(cfg['config']['formatMap'][fmt])
    return Formats

  def description(about, default_desc):
    def extra(type):
      desc = ''
      type_capitalized = type.capitalize()
      note = utilrsw.get_path(about, type)
      if note is not None:
        if isinstance(note, str):
          desc = f'{type_capitalized}: {note}'
        if isinstance(note, list):
          notes = ''
          for i, n in enumerate(note):
            notes += f'{i+1}. {n}; '
          notes = notes.rstrip('; ')
          desc = f'{type_capitalized}s: {notes}'
      return desc

    desc = utilrsw.get_path(about, 'description')
    if desc is None:
      desc = default_desc

    contact = utilrsw.get_path(about, 'contact')
    contactID = utilrsw.get_path(about, 'contactID')

    desc = desc.rstrip('.')
    if contact and contactID:
      if contact == contactID:
        desc = f'{desc}. Contact: {contact}.'
      else:
        desc = f'{desc}. Contact: {contact} <{contactID}>.'
    if not contact and contactID:
      desc = f'{desc}. Contact: <{contactID}>.'
    if contact and not contactID:
      desc = f'{desc}. Contact: {contact}.'

    desc = desc.rstrip('.')

    note = extra('note')
    if note:
      desc = desc.rstrip('.')
      desc = f'{desc}. {note}'

    warning = extra('warning')
    if warning:
      desc = desc.rstrip('.')
      desc = f'{desc}. {warning}'

    return desc.rstrip('.') + '.'

  data_formats = formats(capabilities)


  template = copy.deepcopy(template)

  serverCitation = utilrsw.get_path(about, 'serverCitation')
  DOI = utilrsw.get_path(Spase, ['NumericalData.ResourceHeader.DOI'], None)
  if DOI is None:
    see = 'See ResourceHeader/Description for information on citing the dataset'
  else:
    see = f'See ResourceHeader/DOI: {DOI} for information on citing the dataset'
  if serverCitation is not None:
    serverCitation = f'Server Citation: {serverCitation} ({see}).'
  else:
    serverCitation = f'No serverCitation provided in HAPI /about response for this server ({see}).'

  for i in range(len(template)):
    template[i]['AccessURL']['ProductKey'] = dataset['id']
    template[i]['Acknowledgement'] = serverCitation

  desc = description(about, template[0]['AccessURL']['Description'])
  if desc is not None:
    template[0]['AccessURL']['Description'] = desc
  url = template[0]['AccessURL']['URL'] = dataset['server_url']
  template[0]['AccessURL']['URL'] = url
  template[0]['Format'] = data_formats

  url = template[1]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
  template[1]['AccessURL']['URL'] = url
  template[1]['Format'] = data_formats + template[1]['Format']

  languages, language_formats = script_info()

  desc = template[2]['AccessURL']['Description'].format(languages=languages)
  template[2]['AccessURL']['Description'] = desc
  url = template[2]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
  template[2]['AccessURL']['URL'] = url
  template[2]['Format'] = language_formats

  Spase['NumericalData']['AccessInformation'] = template


def _add_SpatialMapping(Spase, dataset):
  geoLocation = utilrsw.get_path(dataset, 'info.geoLocation')

  if False and (geoLocation is not None):
    Spase['NumericalData']['SpatialMapping'] = {
      'centerLongitude': geoLocation[0],
      'centerLatitude': geoLocation[1]
    }
    if len(geoLocation) > 2:
      Spase['NumericalData']['SpatialMapping']['centerElevation'] = geoLocation[2]
    desc = 'The SpatialMapping values are from the geoLocation object in HAPI metadata. '
    desc += 'Warning: In SPASE, centerLongitude and centerLatitude are in defined to be in GEO and '
    desc += 'centerElevation in WGS84. In HAPI, their equivalents are defined to be in WGS84. '
    desc += 'The values given for centerLongitude and centerLatitude are direct copies '
    desc += 'of content in the HAPI geoLocation and have not '
    desc += 'been converted from WGS84 to GEO.'
    Spase['NumericalData']['SpatialMapping']['Description'] = desc

  point = utilrsw.get_path(dataset, 'info.location.point')
  if point is not None:
    coordinateSystemName = utilrsw.get_path(dataset, 'info.location.coordinateSystemName')
    if coordinateSystemName == 'GEO':
      Spase['NumericalData']['SpatialMapping'] = {
        'centerLongitude': point[0],
        'centerLatitude': point[1]
      }
      if len(point) > 2:
        Spase['NumericalData']['SpatialMapping']['centerElevation'] = point[2]


def _add_ResourceHeader(Spase, dataset, about):
  import datetime

  def extract_doi(doi_string):
    DOI = None
    if doi_string.startswith('https://doi.org/'):
      DOI = doi_string[len('https://doi.org/'):]
    if doi_string.startswith('doi:'):
      DOI = doi_string[len('doi:'):]
    return DOI

  def informationURLs(dataset):
    url_template = 'https://hapi-server.org/servers/#server={server}&dataset={dataset}'
    url = url_template.format(server=dataset['server'], dataset=dataset['id'])
    InformationURLs = [{
      'Name': 'hapi-server.org',
      'URL': url,
      'Description': 'hapi-server.org dataset information page'
    }]
    resourceURL = utilrsw.get_path(dataset, 'info.resourceURL')
    if resourceURL is not None:
      InformationURLs.append({
        'Name': 'Resource URL from HAPI metadata',
        'URL': resourceURL,
        'Description': 'The URL is the the resourceURL field in the HAPI /info response for this dataset.'
      })

    additionalMetadata = utilrsw.get_path(dataset, 'info.additionalMetadata')
    if additionalMetadata is not None:
      if isinstance(additionalMetadata, dict):
        additionalMetadata = [additionalMetadata]

      for additional in additionalMetadata:
        InformationURL = {'Name': '', 'URL': ''}
        desc = ''

        if 'contentURL' not in additional and 'content' not in additional:
          log.error(f"{dataset['id']}: additionalMetadata entry missing one of 'contentURL' or 'content'")
          continue

        if 'contentURL' in additional:
          InformationURL['URL'] = additional['contentURL']

        if 'content' in additional:
          url = f"{dataset['server_url']}/info?dataset={dataset['id']}"
          desc = f'Additional metadata content is available in the additionalMetadata node in: {url}'

        if 'name' in additional:
          InformationURL['Name'] = additional['name']
        else:
          InformationURL['Name'] = 'Additional metadata'

        if 'aboutURL' in additional:
          desc += f"Metadata description: {additional['aboutURL']}"
        if 'schemaURL' in additional:
          desc += f". Metadata schema: {additional['schemaURL']}."

        note = 'The information in this InformationURL node is derived from an additionalMetadata node in HAPI /info response'

        if desc != '':
          InformationURL['Description'] = f'{desc}. {note}'
        else:
          InformationURL['Description'] = note

        InformationURLs.append(InformationURL)

    return InformationURLs

  if 'ResourceHeader' not in Spase['NumericalData']:
    Spase['NumericalData']['ResourceHeader'] = {}

  Spase['NumericalData']['ResourceHeader']['InformationURL'] = informationURLs(dataset)

  now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
  Spase['NumericalData']['ResourceHeader']['ReleaseDate'] = now

  PersonID = about.get('x_SPASE_PersonID', 'UNKNOWN')
  Contacts = [{'PersonID': PersonID, 'Role': 'HostContact'}]

  # Need to add from dataset/info/contact
  Contacts.append({'PersonID': 'UNKNOWN', 'Role': 'GeneralContact'})

  Spase['NumericalData']['ResourceHeader']['Contact'] = Contacts

  extra = ""
  for field in ['datasetCitation', 'resourceID', 'citation']:
    value = utilrsw.get_path(dataset, f'info.{field}')
    if value is not None:
      DOI = extract_doi(value)
      if DOI is not None:
        Spase['NumericalData']['ResourceHeader']['DOI'] = DOI

      extra += f'HAPI {field}: {value}. '

  extra = extra.strip()

  desc = Spase['NumericalData']['ResourceHeader'].get('Description', '')
  desc = desc.rstrip('.')
  if desc != '':
    if extra != '':
      desc = f'{desc}. {extra}'
    else:
      desc = f'{desc}.'
  else:
    desc = extra

  coda = 'The ReleaseDate is the date that this SPASE record was generated by an automated process. Changes are not tracked so the ReleaseDate may change when no changes have occured.'
  if desc != '':
    desc = desc.rstrip('.')
    desc = f'{desc}. {coda}'
  else:
    desc = coda

  Spase['NumericalData']['ResourceHeader']['Description'] = desc

if __name__ == '__main__':
  run()