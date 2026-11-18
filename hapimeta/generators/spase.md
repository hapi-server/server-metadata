**Draft Proposal**

Additional information for the SPASE record can be provided in the `/about` and `/info` response. Any additional SPASE information provided takes precedence over the default HAPI to SPASE mapping implemented in this script and described in [the mapping spreadsheet](https://docs.google.com/document/d/1hd2On4uYQAPNc0xEgZ4XHBOQ8V-x0Pkh5UNtXrkgl7Y/).

In the `/about` response, the `x_SPASE` field can be used to provide SPASE-specific metadata. For example,

```json
"x_SPASE": {
  "PersonID": "spase://SMWG/Person/Katherine.Cariglia",
  "RepositoryID": "spase://HamSCI/Repository/Madrigal"
}
```

is mapped to:

```xml
<NumericalData>
  <ResourceHeader>
    <Person>
      <PersonID>spase://SMWG/Person/Katherine.Cariglia</PersonID>
    </Person>
  </ResourceHeader>
  <AccessInformation>
    <Repository>
      <RepositoryID>spase://HamSCI/Repository/Madrigal</RepositoryID>
    </Repository>
  </AccessInformation>
</NumericalData>
```

In the `/info` response, one can provide a partial SPASE record in the `additionalMetadata` field.

For example, the `additionalMetadata` field in the `/info` response could contain (`additionalMetadata` will only be used for mapping if a SPASE schema URL is given for the `schemaURL` string):

```json
"additionalMetadata": {
  "name": "SPASE additions",
  "schemaURL": "http://www.spase-group.org/data/schema/spase-2.8.0.xsd",
  "content": {
    "NumericalData": {
      "ResourceHeader": {
        "Contact": {
          "PersonID": "spase://SMWG/Person/Katherine.Cariglia",
          "Role": "MetadataContact"
        }
      },
      "AccessInformation": {
        "Repository": {
          "RepositoryID": "spase://HamSCI/Repository/Madrigal"
        }
      },
      "Instrument": {
        "InstrumentID": "spase://HamSCI/Instrument/Example"
      }
    }
  }
}
```

For repeated elements, use arrays:

```json
"additionalMetadata": {
  "name": "SPASE additions",
  "content": {
    "NumericalData": {
      "ResourceHeader": {
        "Contact": [
          {
            "PersonID": "spase://SMWG/Person/Katherine.Cariglia",
            "Role": "MetadataContact"
          },
          {
            "PersonID": "spase://SMWG/Person/Another.Person",
            "Role": "MetadataContact"
          }
        ]
      },
      "AccessInformation": {
        "Repository": {
          "RepositoryID": "spase://HamSCI/Repository/Madrigal"
        }
      },
      "Instrument": [
        {
          "InstrumentID": "spase://HamSCI/Instrument/Example"
        },
        {
          "InstrumentID": "spase://HamSCI/Instrument/AnotherExample"
        }
      ]
    }
  }
}
```

Information about parameters can be added. For example, the conversion of the following HAPI `/info` response

```json
"parameters": [
  {
    "name": "Time",
    "units": "UTC",
    "type": "isotime",
    "fill": null,
    "description": "Time of the observation"
  },
  {
    "name": "parameterA",
    "units": "nT",
    "description": "Description of parameterA"
  }
],
"additionalMetadata": {
  "name": "SPASE additions",
  "schemaURL": "http://www.spase-group.org/data/schema/spase-2.8.0.xsd",
  "content": {
    "NumericalData": {
      "Parameter": [
        {
          "ParameterKey": "parameterA",
          "ValidMin": -65534.0,
          "ValidMax": 65534.0
        }
      ]
    }
  }
}
```

will result in

```xml
<NumericalData>
  ...
  <Parameter>
    <ParameterKey>Time</ParameterKey>
    <Description>Time of the observation</Description>
  </Parameter>
  <Parameter>
    <ParameterKey>parameterA</ParameterKey>
    <Description>Description of parameterA</Description>
    <Units>nT</Units>
    <ValidMin>-65534.0</ValidMin>
    <ValidMax>65534.0</ValidMax>
  </Parameter>
  ...
</NumericalData>
```
