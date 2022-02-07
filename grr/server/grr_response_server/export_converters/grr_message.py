#!/usr/bin/env python
"""Classes for exporting GrrMessage."""

from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base


class GrrMessageConverter(base.ExportConverter):
  """Converts GrrMessage's payload into a set of RDFValues.

  GrrMessageConverter converts given GrrMessages to a set of exportable
  RDFValues. It looks at the payload of every message and applies necessary
  converters to produce the resulting RDFValues.

  Usually, when a value is converted via one of the ExportConverter classes,
  metadata (ExportedMetadata object describing the client, session id, etc)
  are provided by the caller. But when converting GrrMessages, the caller can't
  provide any reasonable metadata. In order to understand where the messages
  are coming from, one actually has to inspect the messages source and this
  is done by GrrMessageConverter and not by the caller.

  Although ExportedMetadata should still be provided for the conversion to
  happen, only "source_urn" and value will be used. All other metadata will be
  fetched from the client object pointed to by GrrMessage.source.
  """

  input_rdf_type = rdf_flows.GrrMessage

  def __init__(self, *args, **kw):
    super().__init__(*args, **kw)
    self.cached_metadata = {}

  def Convert(self, metadata, grr_message):
    """Converts GrrMessage into a set of RDFValues.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      grr_message: GrrMessage to be converted.

    Returns:
      List or generator with resulting RDFValues.
    """
    return self.BatchConvert([(metadata, grr_message)])

  def BatchConvert(self, metadata_value_pairs):
    """Converts a batch of GrrMessages into a set of RDFValues at once.

    Args:
      metadata_value_pairs: a list or a generator of tuples (metadata, value),
        where metadata is ExportedMetadata to be used for conversion and value
        is a GrrMessage to be converted.

    Returns:
      Resulting RDFValues. Empty list is a valid result and means that
      conversion wasn't possible.
    """

    # Group messages by source (i.e. by client urn).
    msg_dict = {}
    for metadata, msg in metadata_value_pairs:
      msg_dict.setdefault(msg.source, []).append((metadata, msg))

    metadata_objects = []
    metadata_to_fetch = []

    # Open the clients we don't have metadata for and fetch metadata.
    for client_urn in msg_dict:
      try:
        metadata_objects.append(self.cached_metadata[client_urn])
      except KeyError:
        metadata_to_fetch.append(client_urn)

    if metadata_to_fetch:
      client_ids = set(urn.Basename() for urn in metadata_to_fetch)
      infos = data_store.REL_DB.MultiReadClientFullInfo(client_ids)

      fetched_metadata = [
          export.GetMetadata(client_id, info)
          for client_id, info in infos.items()
      ]

      for metadata in fetched_metadata:
        self.cached_metadata[metadata.client_urn] = metadata
      metadata_objects.extend(fetched_metadata)

    data_by_type = {}
    for metadata in metadata_objects:
      try:
        for original_metadata, message in msg_dict[metadata.client_urn]:
          # Get source_urn and annotations from the original metadata
          # provided.
          new_metadata = base.ExportedMetadata(metadata)
          new_metadata.source_urn = original_metadata.source_urn
          new_metadata.annotations = original_metadata.annotations
          cls_name = message.payload.__class__.__name__

          # Create a dict of values for conversion keyed by type, so we can
          # apply the right converters to the right object types
          if cls_name not in data_by_type:
            converters_classes = export_converters_registry.GetConvertersByValue(
                message.payload)
            data_by_type[cls_name] = {
                "converters": [cls(self.options) for cls in converters_classes],
                "batch_data": [(new_metadata, message.payload)]
            }
          else:
            data_by_type[cls_name]["batch_data"].append(
                (new_metadata, message.payload))

      except KeyError:
        pass

    # Run all converters against all objects of the relevant type
    converted_batch = []
    for dataset in data_by_type.values():
      for converter in dataset["converters"]:
        converted_batch.extend(converter.BatchConvert(dataset["batch_data"]))

    return converted_batch
