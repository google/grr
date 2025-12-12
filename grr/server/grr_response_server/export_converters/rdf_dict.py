#!/usr/bin/env python
"""Classes for exporting rdf dict data."""

from collections.abc import Iterator
from typing import Any

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


class ExportedDictItem(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedDictItem
  rdf_deps = [base.ExportedMetadata]


class DictToExportedDictItemsConverter(base.ExportConverter):
  """Export converter that converts Dict to ExportedDictItems."""

  input_rdf_type = rdf_protodict.Dict

  def _IterateDict(
      self, d: dict[str, Any], key: str = ""
  ) -> Iterator[tuple[str, Any]]:
    """Performs a deeply-nested iteration of a given dictionary."""
    if isinstance(d, (list, tuple)):
      for i, v in enumerate(d):
        next_key = "%s[%d]" % (key, i)
        for v in self._IterateDict(v, key=next_key):
          yield v
    elif isinstance(d, set):
      for i, v in enumerate(sorted(d)):
        next_key = "%s[%d]" % (key, i)
        for v in self._IterateDict(v, key=next_key):
          yield v
    elif isinstance(d, (dict, rdf_protodict.Dict)):
      for k in sorted(d):
        k = str(k)

        v = d[k]
        if not key:
          next_key = k
        else:
          next_key = key + "." + k

        for v in self._IterateDict(v, key=next_key):
          yield v
    else:
      yield key, d

  def Convert(
      self, metadata: base.ExportedMetadata, data: rdf_protodict.Dict
  ) -> list[ExportedDictItem]:
    result = []
    d = data.ToDict()
    for k, v in self._IterateDict(d):
      result.append(ExportedDictItem(metadata=metadata, key=k, value=str(v)))

    return result
