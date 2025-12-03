import utilrsw

logger = utilrsw.logger('table', log_dir='log')

all_file = 'data/catalogs-all.pkl'
servers = utilrsw.read(all_file)

#servers_keep = None # All servers
servers_keep = ["CDAWeb"] # Only these servers

schema = "https://www.spase-group.org/data/schema"
spase = {
  "xmlns": schema,
  "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
  "xsi:schemaLocation": f"{schema} {schema}/spase-2.7.0.xsd",
  "Version": "2.7.0",
  "NumericalData": {
    "Parameter": []
  }
}

map_dataset = {
  'dataset/id': 'NumericalData/ProviderResourceName',
  'dataset/cadence': 'NumericalData/TemporalDescription/Cadence',
  'dataset/startDate': 'NumericalData/TemporalDescription/TimeSpan/StartDate',
  'dataset/stopDate': 'NumericalData/TemporalDescription/TimeSpan/StopDate'
}
map_parameter = {
  'parameter/name': 'Parameter/ParameterKey',
  'parameter/description': 'Parameter/Description',
  'parameter/units': 'Parameter/Units',
  'parameter/fill': 'Parameter/FillValue'
}

for server in servers:
  if servers_keep is not None and server not in servers_keep:
    continue

  catalog = servers[server]['catalog']
  for dataset in catalog:
    dataset['server'] = server
    dataset['dataset'] = dataset['id']
