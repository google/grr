#!/usr/bin/env python
"""Classes for exporting rdf dict data."""

from collections.abc import Iterator
from typing import Any

from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base


class DictToExportedDictItemsConverterProto(
    base.ExportConverterProto[jobs_pb2.Dict]
):
  """Export converter that converts Dict to ExportedDictItems."""

  input_proto_type = jobs_pb2.Dict
  output_proto_types = (export_pb2.ExportedDictItem,)

  def _IterateDict(self, d: Any, key: str = "") -> Iterator[tuple[str, Any]]:
    """Performs a deeply-nested iteration of a given dictionary."""
    if isinstance(d, (list, tuple)):
      for i, v in enumerate(d):
        next_key = "%s[%d]" % (key, i)
        yield from self._IterateDict(v, key=next_key)
    elif isinstance(d, set):
      for i, v in enumerate(sorted(d)):
        next_key = "%s[%d]" % (key, i)
        yield from self._IterateDict(v, key=next_key)
    elif isinstance(d, dict):
      for k in sorted(d):
        k = str(k)
        v = d[k]
        if not key:
          next_key = k
        else:
          next_key = key + "." + k
        yield from self._IterateDict(v, key=next_key)
    else:
      yield key, d

  def _DataBlobToValue(self, blob: jobs_pb2.DataBlob) -> Any:
    """Converts a DataBlob proto to a python value."""
    if blob.HasField("string"):
      return blob.string
    if blob.HasField("integer"):
      return blob.integer
    if blob.HasField("boolean"):
      return blob.boolean
    if blob.HasField("float"):
      return blob.float
    if blob.HasField("data"):
      return blob.data
    if blob.HasField("none"):
      return None
    if blob.HasField("dict"):
      return self._KeyValueProtoToDict(blob.dict)
    if blob.HasField("list"):
      return [self._DataBlobToValue(d) for d in blob.list.content]
    if blob.HasField("set"):
      return {self._DataBlobToValue(d) for d in blob.set.content}

    # Fallback to string representation for other types.
    # For example, we ignore EmbeddedRDFValue type.
    return str(blob)

  def _KeyValueProtoToDict(self, proto: jobs_pb2.Dict) -> dict[str, Any]:
    """Converts a KeyValue proto to a python dict.

    It stringifies the keys in the process. Values are not yet converted
    because we rely on their type when iterating over the dict.

    Args:
      proto: The jobs_pb2.Dict proto to convert.

    Returns:
      A dictionary representation of the proto.
    """
    res = {}
    for item in proto.dat:
      key = str(self._DataBlobToValue(item.k))
      res[key] = self._DataBlobToValue(item.v)
    return res

  def Convert(
      self, metadata: export_pb2.ExportedMetadata, data: jobs_pb2.Dict
  ) -> list[export_pb2.ExportedDictItem]:
    result = []
    d = self._KeyValueProtoToDict(data)
    for k, v in self._IterateDict(d):
      result.append(
          export_pb2.ExportedDictItem(metadata=metadata, key=k, value=str(v))
      )

    return result
