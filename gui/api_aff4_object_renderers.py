#!/usr/bin/env python
"""Renderers that render AFF4 objects into JSON-compatible data-structures."""



import itertools
import re
import sys


from grr.gui import api_value_renderers
from grr.lib import aff4
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import api_pb2


class ApiAFF4ObjectRendererBase(object):
  """Baseclass for restful API objects rendering classes."""

  __metaclass__ = registry.MetaclassRegistry

  aff4_type = None
  args_type = None


class ApiAFF4ObjectRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAFF4ObjectRendererArgs


class ApiAFF4ObjectRenderer(ApiAFF4ObjectRendererBase):
  aff4_type = "AFF4Object"

  args_type = ApiAFF4ObjectRendererArgs

  def __init__(self):
    if self.aff4_type is None:
      raise ValueError("Have to set aff4_type.")

  def RenderObject(self, aff4_object, args):
    """Renders given object as plain JSON-friendly data structure."""
    object_attributes = aff4_object.synced_attributes.copy()
    for key, value in aff4_object.new_attributes.items():
      object_attributes[key] = value

    attributes = {}
    for attribute, values in object_attributes.items():
      attributes[attribute.predicate] = []
      for value in values:
        # This value is really a LazyDecoder() instance. We need to get at the
        # real data here.
        if hasattr(value, "ToRDFValue"):
          value = value.ToRDFValue()

        if aff4_object.age_policy != aff4.NEWEST_TIME:
          attributes[attribute.predicate].append(
              api_value_renderers.RenderValue(value,
                                              limit_lists=args.limit_lists))
        else:
          attributes[attribute.predicate] = api_value_renderers.RenderValue(
              value, limit_lists=args.limit_lists)

    return dict(aff4_class=aff4_object.__class__.__name__,
                urn=utils.SmartUnicode(aff4_object.urn),
                attributes=attributes,
                age_policy=aff4_object.age_policy)


class ApiRDFValueCollectionRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiRDFValueCollectionRendererArgs


class ApiRDFValueCollectionRenderer(ApiAFF4ObjectRendererBase):
  """Renderer for RDFValueCollections."""

  aff4_type = "RDFValueCollection"
  args_type = ApiRDFValueCollectionRendererArgs

  def RenderObject(self, aff4_object, args):
    """Renders RDFValueCollection as plain JSON-friendly data structure."""
    if args.filter:
      index = 0
      items = []
      for item in aff4_object.GenerateItems():
        serialized_item = item.SerializeToString()
        if re.search(re.escape(args.filter), serialized_item, re.I):
          if index >= args.offset:
            items.append(item)
          index += 1

          if args.count and len(items) >= args.count:
            break
    else:
      items = list(itertools.islice(
          aff4_object.GenerateItems(offset=args.offset),
          args.count or sys.maxint))

    result = {}
    result["offset"] = args.offset
    result["count"] = len(items)
    result["items"] = [api_value_renderers.RenderValue(
        i, limit_lists=args.items_limit_lists) for i in items]

    if args.with_total_count:
      if hasattr(aff4_object, "CalculateLength"):
        total_count = aff4_object.CalculateLength()
      else:
        total_count = len(aff4_object)
      result["total_count"] = total_count

    return result


class ApiIndexedSequentialCollectionRenderer(ApiRDFValueCollectionRenderer):
  aff4_type = "IndexedSequentialCollection"


class VFSGRRClientApiObjectRenderer(ApiAFF4ObjectRendererBase):
  """Renderer for VFSGRRClient objects."""

  aff4_type = "VFSGRRClient"

  def _GetDiskWarnings(self, client):
    """Returns list of disk warning for a given client object."""

    warnings = []
    volumes = client.Get(client.Schema.VOLUMES)

    # Avoid showing warnings for the CDROM.  This is isn't a problem for linux
    # and OS X since we only check usage on the disk mounted at "/".
    exclude_windows_types = [
        rdf_client.WindowsVolume.WindowsDriveTypeEnum.DRIVE_CDROM]

    if volumes:
      for volume in volumes:
        if volume.windowsvolume.drive_type not in exclude_windows_types:
          freespace = volume.FreeSpacePercent()
          if freespace < 5.0:
            warnings.append([volume.Name(), freespace])

    return warnings

  def RenderObject(self, client, unused_args):
    """Renders VFSGRRClient as plain JSON-friendly data structure."""
    return dict(disk_warnings=self._GetDiskWarnings(client),
                summary=api_value_renderers.RenderValue(client.GetSummary()))


RENDERERS_CACHE = {}


def RenderAFF4Object(obj, args=None):
  """Renders given AFF4 object into JSON-friendly data structure."""
  args = args or []

  cache_key = obj.__class__.__name__

  try:
    candidates = RENDERERS_CACHE[cache_key]
  except KeyError:
    candidates = []
    for candidate in ApiAFF4ObjectRendererBase.classes.values():
      if candidate.aff4_type:
        candidate_class = aff4.AFF4Object.classes[candidate.aff4_type]
      else:
        continue

      if aff4.issubclass(obj.__class__, candidate_class):
        candidates.append(candidate)

    if not candidates:
      raise RuntimeError("No renderer found for object %s." %
                         obj.__class__.__name__)

    # Ensure that the renderers order is stable.
    candidates = sorted(candidates, key=lambda cls: cls.__name__)

    RENDERERS_CACHE[cache_key] = candidates

  result = {}
  for candidate in candidates:
    api_renderer_args = None
    for arg in args:
      if candidate.args_type and isinstance(arg, candidate.args_type):
        api_renderer_args = arg

    if api_renderer_args is None and candidate.args_type is not None:
      api_renderer_args = candidate.args_type()

    api_renderer = candidate()
    renderer_output = api_renderer.RenderObject(obj, api_renderer_args)
    for k, v in renderer_output.items():
      result[k] = v

  return result
