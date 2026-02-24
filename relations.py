# Usage: python intermagnet.py

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, DCAT, DCTERMS

# define the HAPI namespace
HAPI = Namespace("http://hapi.org/rdf/")

import hapimeta
log = hapimeta.logger('relations')

debug_observatory = None
#debug_observatory = 'aae'


def relations():
  url = "https://imag-data.bgs.ac.uk/GIN_V1/hapi"

  catalog = _catalog()

  dataset_ids = catalog.keys()
  if debug_observatory is not None:
    # For debugging, keep only IDs that start with aae
    dataset_ids = [id for id in catalog.keys() if id.startswith(debug_observatory)]

  observatories = _observatories(dataset_ids)

  if debug_observatory is not None:
    import utilrsw
    utilrsw.print_dict(observatories)

  g = Graph()

  _head(g, url)
  _provides(g, dataset_ids)
  _definitions(g, dataset_ids, catalog)
  _cadence_relations(g, observatories)
  _quality_relations(g, observatories)
  _frame_relations(g, observatories)

  # Write the output files, in RDF/TTL and JSON-LD
  _write(g)


def _catalog():
  import os
  import utilrsw
  catalog_file = os.path.join(hapimeta.data_dir, 'catalogs', 'INTERMAGNET-all.json')
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


def _observatories(dataset_ids):
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
    if len(parts) != 4:
      print(f"Skipping dataset ID with missing part: {dataset_id}")
      continue

    observatory, quality, cadence, frame = parts
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


def _write(g):
  import os
  out_dir = os.path.join(hapimeta.data_dir, 'relations')
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)
  basename = os.path.join(out_dir, "INTERMAGNET")
  g.serialize(destination=f"{basename}.ttl", format='turtle')
  g.serialize(destination=f"{basename}.jsonld", format='json-ld')

  print(f"Conversion complete. Output written to {basename}.{{ttl, jsonld}}")


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
    uri_ref = f"{g.base}/info?dataset={dataset_id}"
    g.add((g.base, DCAT.servesDataset, URIRef(uri_ref)))

  g.add((g.base, DCAT.endpointURL, g.base))


def _definitions(g, dataset_ids, catalog):
  # Include the relation between Datasets and Parameters

  for dataset_id in dataset_ids:
    uri_dataset = URIRef(f"{g.base}/info?dataset={dataset_id}")
    g.add((uri_dataset, RDF.type, HAPI.Dataset))
    for parameter in catalog[dataset_id]['parameters']:
      # the parameter object must be a URI I propose to compose it as follows:
      # ex: https://imag-data.bgs.ac.uk/GIN_V1/hapi/info?dataset=aae/reported/PT1S/native#Field_Magnitude
      uri_parameter = URIRef(f"{str(uri_dataset)}#{parameter}")
      g.add((uri_dataset, HAPI.hasParameter, uri_parameter))


def _cadence_relations(g, dataset_ids_parts):
  # Include the cadence information for each Dataset
  # NB: use new property name of hapi:resamplingMethod (see base.ttl)

  base_cadence = 'PT1S'
  for observatory in dataset_ids_parts.keys():
    cadences = dataset_ids_parts[observatory]['cadences']
    if base_cadence not in cadences:
      log.error(f"Base cadence '{base_cadence}' not found for observatory '{observatory}'.")
      continue
    for quality in dataset_ids_parts[observatory]['qualities']:
      sub_cadences = set(cadences) - {base_cadence}
      for cadence in sub_cadences:
        for frame in dataset_ids_parts[observatory]['frames']:
          uri_resample = URIRef(f"{g.base}/info?dataset={observatory}/{quality}/{cadence}/{frame}")
          uri_source = URIRef(f"{g.base}/info?dataset={observatory}/{quality}/{base_cadence}/{frame}")
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
          uri1 = URIRef(f"{g.base}/info?dataset={observatory}/{quality}/{cadence}/{frame}")
          uri2 = URIRef(f"{g.base}/info?dataset={observatory}/{base_quality}/{cadence}/{frame}")
          g.add((uri1, DCTERMS.isVersionOf, uri2))
          # we could also say:
          # g.add((uri1, PROV.wasDerivedFrom, uri2))


def _frame_relations(g, dataset_ids_parts):

  base_frame = 'native'
  for observatory in dataset_ids_parts.keys():
    frames = dataset_ids_parts[observatory]['frames']
    if base_frame not in frames:
      log.error(f"Base frame '{base_frame}' not found for observatory '{observatory}'.")
      continue
    for quality in dataset_ids_parts[observatory]['qualities']:
      for cadence in dataset_ids_parts[observatory]['cadences']:
        sub_frames = set(frames) - {base_frame}
        for frame in sub_frames:
          uri1 = URIRef(f"{g.base}/info?dataset={observatory}/{quality}/{cadence}/{frame}")
          uri2 = URIRef(f"{g.base}/info?dataset={observatory}/{quality}/{cadence}/{base_frame}")
          g.add((uri1, HAPI.isReferenceFrameTransformOf, uri2))


if __name__ == "__main__":
  relations()