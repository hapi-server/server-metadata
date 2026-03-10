# Usage: python relations.py

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, DCAT, DCTERMS

# define the HAPI namespace
HAPI = Namespace("http://hapi.org/rdf#")

import hapimeta
log = hapimeta.logger('relations')

all = False
if not all:
  server_id = 'INTERMAGNET'
  observatory = 'aae'

def relations(server_id, observatory=None):
  if server_id == 'INTERMAGNET':
    url = "https://imag-data.bgs.ac.uk/GIN_V1/hapi"

  if server_id == 'WDC':
    url = 'https://wdcapi.bgs.ac.uk/hapi'

  catalog = _catalog(server_id)

  dataset_ids = catalog.keys()
  if observatory is not None:
    # For debugging, keep only IDs that start with aae
    dataset_ids = [id for id in catalog.keys() if id.startswith(observatory)]
    log.info(f"Found {len(dataset_ids)} datasets for server {server_id} and observatory {observatory}")
  else:
    log.info(f"Found {len(dataset_ids)} datasets for server {server_id}")

  observatories = _observatories(dataset_ids, server_id)
  if observatory is not None:
    import utilrsw
    log.info(f"Processing only {server_id}/{observatory}:")
    utilrsw.print_dict(observatories, indent=2)

  g = Graph()

  _head(g, url)
  _provides(g, dataset_ids)
  _definitions(g, dataset_ids, catalog)

  _cadence_relations(g, observatories, catalog, server_id)

  if server_id == 'INTERMAGNET':
    _quality_relations(g, observatories)

  _frame_relations(g, observatories, catalog, server_id)

  # Write the output files, in RDF/TTL and JSON-LD
  _write(g, server_id, observatory=observatory)


def _catalog(server_id):
  import os
  import utilrsw

  log.info("Reading and preparing catalog.")

  catalog_file = os.path.join(hapimeta.data_dir, 'catalog', f'{server_id}-all.json')
  catalog = utilrsw.read(catalog_file)
  catalog = utilrsw.array_to_dict(catalog, 'id')

  for dataset_id in list(catalog.keys()):
    dataset = catalog[dataset_id]
    if 'info' not in dataset:
      log.error(f"Dataset {dataset_id} is missing 'info'")
      del catalog[dataset_id]
      continue
    if 'parameters' not in dataset['info']:
      log.error(f"Dataset {dataset_id} is missing 'parameters'")
      del catalog[dataset_id]
      continue
    parameters = dataset['info']['parameters']
    dataset['parameters'] = utilrsw.array_to_dict(parameters, 'name')

  return catalog


def _observatories(dataset_ids, server_id):
  """
  Convert IDs in the form 'observatory/quality/cadence/frame' into a
  dictionary grouped by observatory:
    observatory1: {
      'quality': [qualities associated with observatory1],
      'cadence': [cadences associated with observatory1],
      'frame': [frames values associated with observatory1]
    },
    observatory2: {...}
  """
  def add_unique(items, value):
    if value not in items:
      items.append(value)

  grouped = {}
  for dataset_id in dataset_ids:
    parts = dataset_id.split('/')
    if server_id == 'INTERMAGNET':
      if len(parts) != 4:
        print(f"Skipping dataset ID with missing part: {dataset_id}")
        continue

      observatory, quality, cadence, frame = parts

    if server_id == 'WDC':
      if len(parts) != 3:
        print(f"Skipping dataset ID with missing part: {dataset_id}")
        continue

      observatory, cadence, frame = parts
      quality = None

    if observatory not in grouped:
      grouped[observatory] = {
        'qualities': [],
        'cadences': [],
        'frames': []
      }

    add_unique(grouped[observatory]['qualities'], quality)
    add_unique(grouped[observatory]['cadences'], cadence)
    add_unique(grouped[observatory]['frames'], frame)

  return grouped


def _head(g, url):
  # Define the header of the graph
  # - bind namespaces that are not included by default
  # - define the base url

  g.bind('hapi', HAPI)
  g.bind('dcat', DCAT)
  g.base = URIRef(url)


def _provides(g, dataset_ids):

  # Include the relations between the Server and the Datasets
  # we use here the dcat:servesDataset relation, rather than the HAPI one
  # (which should be removed)

  g.add((g.base, RDF.type, HAPI.Service))
  for dataset_id in dataset_ids:
    uri_ref = f"/info?dataset={dataset_id}"
    g.add((g.base, DCAT.servesDataset, URIRef(uri_ref)))

  g.add((g.base, DCAT.endpointURL, g.base))


def _definitions(g, dataset_ids, catalog):
  # Include the relation between Datasets and Parameters

  for dataset_id in dataset_ids:
    uri_dataset = URIRef(f"/info?dataset={dataset_id}")
    g.add((uri_dataset, RDF.type, HAPI.Dataset))
    for i, parameter in enumerate(catalog[dataset_id]['parameters']):
      # the parameter object must be a URI I propose to compose it as follows:
      # ex: https://imag-data.bgs.ac.uk/GIN_V1/hapi/info?dataset=aae/reported/PT1S/native#Field_Magnitude
      uri_parameter = URIRef(f"{str(uri_dataset)}#{parameter}")
      param_type = HAPI.Time if i == 0 else HAPI.Parameter
      g.add((uri_parameter, RDF.type, param_type))
      g.add((uri_dataset, HAPI.hasParameter, uri_parameter))


def _cadence_relations(g, dataset_ids_parts, catalog, server_id):
  # Include the cadence information for each Dataset
  # NB: use new property name of hapi:resamplingMethod (see base.ttl)
  def min_cadence(cadences):
    import datetime
    import utilrsw

    if not cadences:
      return None

    start = datetime.datetime(2020, 1, 1)
    def key(cadence):
      return utilrsw.time.isoduration_to_timedelta(cadence, start=start)

    return min(cadences, key=key)

  for observatory in dataset_ids_parts.keys():
    cadences = dataset_ids_parts[observatory]['cadences']
    base_cadence = min_cadence(cadences)

    if base_cadence is None:
      log.error(f"No cadences found for observatory '{observatory}'.")
      continue

    for quality in dataset_ids_parts[observatory]['qualities']:
      sub_cadences = set(cadences) - {base_cadence}
      for cadence in sub_cadences:
        for frame in dataset_ids_parts[observatory]['frames']:
          if server_id == 'INTERMAGNET':
            id_resample = f"{observatory}/{quality}/{cadence}/{frame}"
            id_source = f"{observatory}/{quality}/{base_cadence}/{frame}"
          if server_id == 'WDC':
            id_resample = f"{observatory}/{cadence}/{frame}"
            id_source = f"{observatory}/{base_cadence}/{frame}"

          if (id_resample not in catalog) or (id_source not in catalog):
            log.warning(f"Dataset ID '{id_resample}' or '{id_source}' not found in catalog.")
            continue

          uri_resample = URIRef(f"/info?dataset={id_resample}")
          uri_source = URIRef(f"/info?dataset={id_source}")
          g.add((uri_resample, HAPI.resamplingMethod, HAPI.average))
          g.add((uri_resample, HAPI.isResampledOf, uri_source))


def _quality_relations(g, dataset_ids_parts):

  for observatory in dataset_ids_parts.keys():
    qualities = dataset_ids_parts[observatory]['qualities']
    if 'reported' in qualities:
      base_quality = 'reported'
    elif 'adjusted' in qualities:
      base_quality = 'adjusted'
    elif 'quasi-def' in qualities:
      base_quality = 'quasi-def'
    else:
      base_quality = dataset_ids_parts[observatory]['qualities'][0]

    sub_qualities = set(qualities) - {base_quality}
    for quality in sub_qualities:
      for cadence in dataset_ids_parts[observatory]['cadences']:
        for frame in dataset_ids_parts[observatory]['frames']:
          uri1 = URIRef(f"/info?dataset={observatory}/{quality}/{cadence}/{frame}")
          uri2 = URIRef(f"/info?dataset={observatory}/{base_quality}/{cadence}/{frame}")
          g.add((uri1, DCTERMS.isVersionOf, uri2))
          # we could also say:
          # g.add((uri1, PROV.wasDerivedFrom, uri2))


def _frame_relations(g, dataset_ids_parts, catalog, server_id):

  if server_id == 'INTERMAGNET':
    base_frame = 'native'
  if server_id == 'WDC':
    base_frame = 'original'

  for observatory in dataset_ids_parts.keys():
    frames = dataset_ids_parts[observatory]['frames'].copy()
    if server_id == 'WDC':
      if 'k' in frames:
        # Datasets ending in /k do not contain the Field_Vector parameter
        frames.remove('k')

    if base_frame not in frames:
      log.error(f"Base frame '{base_frame}' not found for observatory '{observatory}'.")
      continue

    for quality in dataset_ids_parts[observatory]['qualities']:
      for cadence in dataset_ids_parts[observatory]['cadences']:
        sub_frames = set(frames) - {base_frame}
        for frame in sub_frames:
          if server_id == 'INTERMAGNET':
            dataset_id_1 = f"{observatory}/{quality}/{cadence}/{frame}"
            dataset_id_2 = f"{observatory}/{quality}/{cadence}/{base_frame}"
          if server_id == 'WDC':
            dataset_id_1 = f"{observatory}/{cadence}/{frame}"
            dataset_id_2 = f"{observatory}/{cadence}/{base_frame}"

          if (dataset_id_1 not in catalog) or (dataset_id_2 not in catalog):
            log.warning(f"Dataset ID '{dataset_id_1}' or '{dataset_id_2}' not found in catalog.")
            continue

          if 'Field_Vector' not in catalog[dataset_id_1]['parameters']:
            continue
          if 'Field_Vector' not in catalog[dataset_id_2]['parameters']:
            continue

          uri1 = URIRef(f"/info?dataset={dataset_id_1}#Field_Vector")
          uri2 = URIRef(f"/info?dataset={dataset_id_2}#Field_Vector")
          g.add((uri1, HAPI.isReferenceFrameTransformOf, uri2))


def _write(g, server_id, observatory=None):
  import os
  out_dir = os.path.join(hapimeta.data_dir, 'relations')
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  basename = os.path.join(out_dir, server_id)
  if observatory is not None:
    basename += f"-{observatory}"

  # Preserve graph base in serialized outputs for downstream consumers.
  base_iri = str(getattr(g, "base", "")) or None

  turtle_kwargs = {"format": "turtle"}
  if base_iri:
    turtle_kwargs["base"] = base_iri

  jsonld_kwargs = {"format": "json-ld"}
  if base_iri:
    jsonld_kwargs["base"] = base_iri

  g.serialize(destination=f"{basename}.ttl", **turtle_kwargs)
  g.serialize(destination=f"{basename}.jsonld", **jsonld_kwargs)

  print(f"Conversion complete. Output written to {basename}.{{ttl, jsonld}}")


if __name__ == "__main__":
  if all:
    relations("INTERMAGNET", "aae")
    relations("WDC", "aae")
    relations("INTERMAGNET")
    relations("WDC")
  else:
    relations(server_id, observatory)
