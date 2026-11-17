import os
import re
from urllib.parse import unquote, urlparse

import utilrsw

import hapimeta

cfg = hapimeta.config('spase')
log = hapimeta.logger('spase')

def run():

  log.info('Generating SPASE')
  args = hapimeta.cli()

  # Read in full metadata from catalogs-all.pkl
  all = hapimeta.all(log)

  schema = _read_schema()
  for server_id in all.keys():
    log.info(f'{server_id}')
    spase(
      server_id,
      all[server_id],
      schema,
      max_datasets=args.n_datasets,
      exit_on_exception=args.exit_on_exception,
    )


def spase(server_id, server_meta, schema, max_datasets=None, exit_on_exception=False):

  Spase = _spase_stub()

  catalog = utilrsw.get_path(server_meta, 'catalog.catalog')
  if catalog is None:
    log.error(f"No catalog found for server '{server_id}' in catalogs-all.pkl. Skipping server.")
    return

  s = '' if len(catalog) == 1 else 's'
  log.info(f'  Found {len(catalog)} dataset{s}')

  if max_datasets is not None:
    catalog = catalog[:max_datasets]
    s = '' if len(catalog) == 1 else 's'
    log.info(f'  Processing only {len(catalog)} dataset{s} due to --n-datasets {max_datasets}')


  log.info(f'  Extracting about information for server {server_id} from catalogs-all.pkl')
  about = server_meta.get('about', None)
  log.info(f'  Extracting capabilities information for server {server_id} from catalogs-all.pkl')
  capabilities = server_meta.get('capabilities', None)

  out_path = os.path.join(hapimeta.DATA_DIR, 'spase')

  Spase = _spase_stub()

  log.info('  Processing datasets.')
  for idx, dataset in enumerate(catalog):
    dataset['server'] = server_id
    dataset['server_url'] = about['x_url']
    dataset['dataset'] = dataset['id']

    log.info(f"    {idx+1}. {dataset['id']}")

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

    try:
      _add_NumericalData(Spase, dataset, cfg['config']['hapi2spase']['dataset'])
      _add_ResourceHeader(Spase, dataset, about)
      _add_SpatialCoverage(Spase, dataset)
      _add_AccessInformation(Spase, dataset, about, capabilities, cfg['config']['formatMap'], cfg['config']['AccessInformation'])
      _add_Parameter(Spase, dataset, cfg['config']['hapi2spase']['parameter'])

      # This should be obtained from the SPASE/NumericalData schema
      key_order = ['ResourceID', 'ResourceHeader', 'AccessInformation',
                   'ProviderResourceName', 'MeasurementType', 'TemporalDescription',
                   'SpatialCoverage', 'Caveats', 'Parameter']
      Spase['NumericalData'] = utilrsw.reorder_dict(Spase['NumericalData'], key_order)

      valid = _validate(Spase, schema, exit_on_exception)

      out_file = os.path.join(out_path, server_id, f"{dataset['id']}.xml")
      if valid:
        _write(Spase, out_file)
      else:
        log.error(f"Error validating dataset {dataset['id']} from server {server_id}. Skipping write.")
        if os.path.exists(out_file):
          log.error(f"Found existing file {out_file}. Removing.")
          os.remove(out_file)

    except Exception as e:
      log.error(f"Error processing dataset {dataset['id']} from server {server_id}: {e}")
      if exit_on_exception:
        log.error(f"        Exiting due to error processing dataset {dataset['id']} from server {server_id} and --exit-on-exception command line argument.")
        os._exit(1)
      continue

  return Spase


def _xml_content(Spase):
  import xmltodict

  attr_keys = ('xmlns', 'xmlns:xsi', 'xsi:schemaLocation')
  xml_root = {(f'@{k}' if k in attr_keys else k): v for k, v in Spase.items()}
  return xmltodict.unparse({'Spase': xml_root}, pretty=True, indent='  ')


def _write(Spase, out_file):

  xml_content = _xml_content(Spase)
  log.info(f'       Writing {out_file}')
  utilrsw.write(out_file, xml_content)

  if False:
    json_file = out_file.replace('.xml', '.json')
    log.info(f'       Writing {json_file}')
    utilrsw.write(json_file, Spase)


def _read_schema():
  config = cfg['config']['Spase']
  schema_url = _schema_xsd_url(config['SchemaURL'], config['Version'])
  file = os.path.join(hapimeta.DATA_DIR, 'tmp', schema_url.split('/')[-1])
  os.makedirs(os.path.dirname(file), exist_ok=True)
  if not os.path.exists(file):
    log.info(f"Downloading {schema_url} to {file}")
  else:
    log.info(f"Reading {file}")
  response = utilrsw.net.get_conditional(schema_url, file=file, stream=False, progress=False)
  return response['data']


def _validate(Spase, schema, exit_on_exception=False):
  """Validate the in-memory record before writing; return whether it is valid."""
  from lxml import etree

  schema_url = _schema_xsd_url(Spase['xmlns'], Spase['Version'])
  resource_id = Spase['NumericalData'].get('ResourceID', '<unknown ResourceID>')

  try:
    schema = etree.XMLSchema(etree.fromstring(schema))
    log.info(f'       Validating {resource_id} against {schema_url.split("/")[-1]}')
    doc = etree.fromstring(_xml_content(Spase).encode('utf-8'))
    if not schema.validate(doc):
      for error in schema.error_log:
        log.error(f'        {resource_id}: {error}')
      if exit_on_exception:
        raise ValueError(f"SPASE validation failed for {resource_id}")
      return False
    log.info('       Valid')
    return True
  except (etree.LxmlError, ValueError, TypeError) as e:
    log.error(f'       Error validating {resource_id}: {e}')
    if exit_on_exception:
      raise
    return False


def _schema_xsd_url(schema_url, version):
  return f'{schema_url}/spase-{version}.xsd'


def _spase_stub():
  config = cfg['config']['Spase']
  SchemaURL = config.get('SchemaURL', None)
  Version = config.get('Version')
  Spase = {
    'xmlns': SchemaURL,
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xsi:schemaLocation': f'{SchemaURL} {_schema_xsd_url(SchemaURL, Version)}',
    'Version': Version,
    'NumericalData': {
      'AccessInformation': [],
      'Parameter': []
    }
  }
  return Spase


def _normalize_datetime(value):
  """Ensure a date/datetime string has a time component for SPASE schema compliance.

  E.g. '2016-12-31Z' -> '2016-12-31T00:00:00Z'
       '2016-12-31'  -> '2016-12-31T00:00:00Z'
  """
  from hapiclient import hapitime2datetime
  value_dt = hapitime2datetime(value, allow_missing_Z=True)[0]
  return value_dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _add_NumericalData(Spase, dataset, map):
  resource_id = utilrsw.get_path(dataset, 'info.resourceID', default='')
  if not isinstance(resource_id, str) or re.fullmatch(r'[^:]+://[^/]+/.+', resource_id) is None:
    # SPASE schema requires ResourceID to match [^:]+://[^/]+/.+
    resource_id = f"spase://HAPI/{dataset['server']}/{dataset['id']}"
  mapped = utilrsw.map_dict(dataset, map)
  NumericalData = {'ResourceID': resource_id}
  NumericalData.update(mapped)

  # Valid in 2.7.2+
  NumericalData['MeasurementType'] = 'NotProvided'

  # Normalize StartDate/StopDate to full datetime strings required by SPASE schema
  ts = utilrsw.get_path(NumericalData, 'TemporalDescription.TimeSpan')
  if isinstance(ts, dict):
    for key in ('StartDate', 'StopDate'):
      if key in ts:
        ts[key] = _normalize_datetime(ts[key])
  Spase['NumericalData'] = NumericalData


def _add_Parameter(Spase, dataset, map):
  parameters = utilrsw.get_path(dataset, 'info.parameters')
  if parameters is not None:
    Parameters = []
    for parameter in parameters:
      Parameter = utilrsw.map_dict(parameter, map)
      Parameters.append(Parameter)
      units = parameter.get('units', None)
      if isinstance(units, str) and parameter['units'].lower() == 'UTC':
        Parameter['Support'] = {'SupportQuantity': 'Temporal'}
      else:
        Parameter['Mixed'] = {'MixedQuantity': 'Other'}

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


    def get_and_strip(field):
      value = utilrsw.get_path(about, field)
      if value is not None:
        value = value.rstrip('.').strip()
        if value == '':
          value = None
      return value

    desc = default_desc
    about_title = get_and_strip('title')
    if about_title is not None:
      desc = about_title

    about_description = get_and_strip('description')
    if about_description is not None:
      desc = f'{desc}. {about_description}'

    if False:
      server_citation = get_and_strip('serverCitation')
      if server_citation is not None:
        desc = f'{desc}. Server Citation: {server_citation}'

    contact = get_and_strip('contact')
    if contact is not None:
      desc = f'{desc}. Contact: {contact}'

    contactID = get_and_strip('contactID')
    if contactID is not None:
      desc = f'{desc}. ContactID: {contactID}'

    note = extra('note')
    if note:
      desc = f'{desc}. {note}'

    warning = extra('warning')
    if warning:
      desc = f'{desc}. {warning}'

    return desc.rstrip('.') + '.'

  data_formats = formats(capabilities)


  AccessInformation = copy.deepcopy(template)

  DOI = utilrsw.get_path(Spase, ['NumericalData.ResourceHeader.DOI'], None)
  if DOI is None:
    see = 'See ResourceHeader/Description for information on citing the dataset'
  else:
    see = f'See ResourceHeader/DOI: {DOI} for information on citing the dataset'

  serverCitation = utilrsw.get_path(about, 'serverCitation')
  if serverCitation is not None:
    serverCitation = f'Repository (data provider) Citation: {serverCitation} ({see}).'
  else:
    serverCitation = f'No serverCitation provided in HAPI /about response for this server ({see}).'

  RepositoryID = about.get('x_SPASE', {}).get('RepositoryID', None)

  hapi_server_id = about.get('id', None)
  Name = "HAPI Server"
  for i in range(len(AccessInformation)):
    if RepositoryID is not None:
      AccessInformation[i]['RepositoryID'] = RepositoryID
    AccessInformation[i]['AccessURL']['Name'] = Name
    if hapi_server_id is not None:
      AccessInformation[i]['AccessURL']['Name'] = f"{hapi_server_id} {Name}"
    AccessInformation[i]['AccessURL']['ProductKey'] = dataset['id']
    AccessInformation[i]['Acknowledgement'] = serverCitation

  desc_default = AccessInformation[0]['AccessURL']['Description']
  desc = description(about, desc_default)
  if desc is not None:
    AccessInformation[0]['AccessURL']['Description'] = desc
  url = AccessInformation[0]['AccessURL']['URL'] = dataset['server_url']
  AccessInformation[0]['AccessURL']['URL'] = url
  AccessInformation[0]['Format'] = data_formats

  url = AccessInformation[1]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
  AccessInformation[1]['AccessURL']['URL'] = url
  AccessInformation[1]['Format'] = data_formats + AccessInformation[1]['Format']

  if False:
    languages, language_formats = script_info()

    desc = AccessInformation[2]['AccessURL']['Description'].format(languages=languages)
    AccessInformation[2]['AccessURL']['Description'] = desc
    url = AccessInformation[2]['AccessURL']['URL'].format(server=dataset['server'], dataset=dataset['id'])
    AccessInformation[2]['AccessURL']['URL'] = url
    AccessInformation[2]['Format'] = language_formats
  else:
    del AccessInformation[2]

  licenseURL = utilrsw.get_path(dataset, 'info.licenseURL')
  if licenseURL is not None:
    if isinstance(licenseURL, str):
      licenseURL = [licenseURL]

    Rights = []
    for url in licenseURL:
      Right = {'RightsURI': url}
      parsed = urlparse(url)
      path_parts = parsed.path.rstrip('/').split('/')
      if parsed.hostname in ('spdx.org', 'www.spdx.org') and len(path_parts) >= 3 and path_parts[-2] == 'licenses':
        identifier = unquote(path_parts[-1])
        identifier = identifier.removesuffix('.html')
        if identifier:
          Right = {
            'SchemeURI': f'https://spdx.org/licenses/{identifier}.html',
            'RightsIdentifierScheme': 'SPDX',
            'RightsIdentifier': identifier,
            'RightsURI': url
          }
      Rights.append(Right)

    for i in range(len(AccessInformation)):
      # RightsList occurs at most once, while Rights may occur multiple times.
      AccessInformation[i]['RightsList'] = {'Rights': copy.deepcopy(Rights)}

  # TODO: These should be obtained from SPASE schema, not hardcoded here.
  access_info_key_order = ['RepositoryID', 'Availability', 'AccessRights',
                           'RightsList', 'AccessURL', 'Format',
                           'Acknowledgement']
  access_url_key_order = ['Name', 'URL', 'Style', 'ProductKey', 'Description',
                          'Language']
  for i in range(len(AccessInformation)):
    AccessInformation[i]['AccessURL'] = utilrsw.reorder_dict(
      AccessInformation[i]['AccessURL'], access_url_key_order
    )
    AccessInformation[i] = utilrsw.reorder_dict(AccessInformation[i], access_info_key_order)

  Spase['NumericalData']['AccessInformation'] = AccessInformation


def _add_SpatialCoverage(Spase, dataset):
  geoLocation = utilrsw.get_path(dataset, 'info.geoLocation')

  if geoLocation is not None:
    Spase['NumericalData']['SpatialCoverage'] = {
      'CoordinateSystem': {
        'CoordinateRepresentation': 'Spherical',
        'CoordinateSystemName': 'WGS84'
      },
      'CenterLatitude': geoLocation[1],
      'CenterLongitude': geoLocation[0]
    }
    if len(geoLocation) > 2:
      Spase['NumericalData']['SpatialCoverage']['CenterElevation'] = geoLocation[2]
    Spase['NumericalData']['SpatialCoverage']['Description'] = "Longitude and Latitude are given in degrees. Elevation is given in meters."

  #point = utilrsw.get_path(dataset, 'info.location.point')
  # TODO: Can do mapping of vectorComponents of latitude, longitude, and altitude.
  #       If anything else, can't map.
  #       Can map coordinate system if coordinateSystemSchema is SPASE in HAPI metadata.
  #       Otherwise, would need to develop custom mapping for other coordinateSystemSchemas.


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
      'Description': 'hapi-server.org Data Explorer page for dataset'
    }]

    resourceURL = utilrsw.get_path(dataset, 'info.resourceURL')
    if resourceURL is not None and resourceURL != url:
      InformationURLs.append({
        'Name': 'Resource URL from HAPI metadata',
        'URL': resourceURL,
        'Description': 'The URL in the resourceURL field in the HAPI /info response for this dataset.'
      })

    additionalMetadata = utilrsw.get_path(dataset, 'info.additionalMetadata')
    if additionalMetadata is not None:
      if isinstance(additionalMetadata, dict):
        additionalMetadata = [additionalMetadata]

      for additional in additionalMetadata:
        InformationURL = {'Name': '', 'URL': ''}
        desc = []

        if 'contentURL' not in additional and 'content' not in additional:
          log.error(f"{dataset['id']}: additionalMetadata entry missing one of 'contentURL' or 'content'")
          continue

        if 'contentURL' in additional:
          InformationURL['URL'] = additional['contentURL']

        if 'content' in additional:
          url = f"{dataset['server_url']}/info?dataset={dataset['id']}"
          desc.append('Additional metadata content is available in the additionalMetadata node in the given URL.')
          InformationURL['URL'] = url

        if 'name' in additional:
          InformationURL['Name'] = additional['name']
        else:
          InformationURL['Name'] = 'Additional metadata'

        if 'aboutURL' in additional:
          desc.append(f"Metadata description: {additional['aboutURL']}")

        if 'schemaURL' in additional:
          desc.append(f"Metadata schema: {additional['schemaURL']}")


        note = 'The information in this InformationURL node is derived from an additionalMetadata node in HAPI /info response'

        if desc:
          InformationURL['Description'] = f'{" ".join(desc)}. {note}'
        else:
          InformationURL['Description'] = note

        InformationURLs.append(InformationURL)

    return InformationURLs

  if 'ResourceHeader' not in Spase['NumericalData']:
    Spase['NumericalData']['ResourceHeader'] = {}

  resource_header = Spase['NumericalData']['ResourceHeader']
  if not resource_header.get('ResourceName'):
    resource_header['ResourceName'] = dataset['id']

  Spase['NumericalData']['ResourceHeader']['InformationURL'] = informationURLs(dataset)

  now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
  Spase['NumericalData']['ResourceHeader']['ReleaseDate'] = now

  x_SPASE = about.get('x_SPASE', {})
  PersonID = x_SPASE.get('PersonID', 'spase://SMWG/Person/UNKNOWN')
  Contacts = [{'PersonID': PersonID, 'Role': 'HostContact'}]

  # Need to add from dataset/info/contact
  #Contacts.append({'PersonID': 'UNKNOWN', 'Role': 'GeneralContact'})

  Spase['NumericalData']['ResourceHeader']['Contact'] = Contacts

  extra = ""
  title = utilrsw.get_path(dataset, 'title')
  if title is None:
    dataset_id = utilrsw.get_path(dataset, 'id')
    if dataset_id is not None:
      extra += f"HAPI dataset id: {dataset_id}. "
  else:
    extra += f'HAPI title: {title}. '

  for field in ['datasetCitation', 'resourceID', 'citation']:
    value = utilrsw.get_path(dataset, f'info.{field}')
    if value is not None:
      DOI = extract_doi(value)
      if DOI is not None:
        Spase['NumericalData']['ResourceHeader']['DOI'] = DOI

      # This is not in mapping spreadsheet.
      extra += f'HAPI {field}: {value}. '

  extra = extra.strip()

  # info/description was mapped to
  #   Spase['NumericalData']['ResourceHeader']['Description']
  # already based on mapping in run.json.
  desc = Spase['NumericalData']['ResourceHeader'].get('Description', '')
  desc = desc.rstrip('.')
  if desc == '':
    desc = extra
  else:
    if extra == '':
      desc = f'{desc}.'
    else:
      desc = f'{desc}. {extra}'

  coda = 'The ReleaseDate is the date that this SPASE record was generated by an automated process. Changes are not tracked so the ReleaseDate may change when no changes have occured.'
  if desc != '':
    desc = desc.rstrip('.')
    desc = f'{desc}. {coda}'
  else:
    desc = coda

  Spase['NumericalData']['ResourceHeader']['Description'] = desc

  Note = ("This release date is the date the initial SPASE record is created "
          "by an automated process that does not currently track changes. "
          "The automation process updates the metadata without updating this date. "
          "This is not a revision event, it is an initial creation event.")

  Spase['NumericalData']['ResourceHeader']['RevisionHistory'] = {
    'RevisionEvent': {
      'ReleaseDate': now,
      'Note': Note
    }
  }

  # SPASE schema requires InformationURL after ReleaseDate/DOI/Contact
  rh_key_order = ['ResourceName', 'AlternateName', 'DOI', 'ReleaseDate', 'RevisionHistory',
                   'Description', 'Acknowledgement', 'PublicationInfo', 'Contact',
                   'InformationURL', 'Association', 'PriorID']
  Spase['NumericalData']['ResourceHeader'] = utilrsw.reorder_dict(
    Spase['NumericalData']['ResourceHeader'], rh_key_order
  )


if __name__ == '__main__':
  run()
