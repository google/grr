#!/usr/bin/env python
"""Renderers that render AFF4 objects into JSON-compatible data-structures."""



import itertools
import re
import sys


from grr.gui import api_value_renderers
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.proto import api_pb2


class ApiAFF4ObjectRendererBase(object):
  """Baseclass for restful API objects rendering classes."""

  __metaclass__ = registry.MetaclassRegistry

  aff4_type = None
  args_type = None


class ApiAFF4ObjectRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiAFF4ObjectRendererArgs


class ApiAFF4ObjectRenderer(ApiAFF4ObjectRendererBase):
  aff4_type = "AFF4Object"

  args_type = ApiAFF4ObjectRendererArgs

  def __init__(self):
    if self.aff4_type is None:
      raise ValueError("Have to set aff4_type.")

  def RenderObject(self, aff4_object, args):
    """Renders given object as plain JSON-friendly data structure."""
    render_value_args = dict(limit_lists=args.limit_lists)
    if args.type_info == args.TypeInformation.WITH_TYPES:
      render_value_args["with_types"] = True
    elif args.type_info == args.TypeInformation.WITH_TYPES_AND_METADATA:
      render_value_args["with_types"] = True
      render_value_args["with_metadata"] = True

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
              api_value_renderers.RenderValue(value, **render_value_args))
        else:
          attributes[attribute.predicate] = api_value_renderers.RenderValue(
              value, **render_value_args)

    result = dict(aff4_class=aff4_object.__class__.__name__,
                  urn=utils.SmartUnicode(aff4_object.urn),
                  attributes=attributes,
                  age_policy=aff4_object.age_policy)

    if args.type_info == args.TypeInformation.WITH_TYPES_AND_METADATA:
      descriptors = {}
      for attribute, _ in aff4_object.synced_attributes.items():
        descriptors[attribute.predicate] = {
            "description": attribute.description
        }

      result["metadata"] = descriptors

    return result


class ApiRDFValueCollectionRendererArgs(rdfvalue.RDFProtoStruct):
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
          aff4_object.GenerateItems(), args.offset,
          args.count and (args.offset + args.count) or sys.maxint))

    render_value_args = dict(limit_lists=args.items_limit_lists)
    if args.items_type_info == "WITH_TYPES":
      render_value_args["with_types"] = True
    elif args.items_type_info == "WITH_TYPES_AND_METADATA":
      render_value_args["with_types"] = True
      render_value_args["with_metadata"] = True

    result = {}
    result["offset"] = args.offset
    result["count"] = len(items)
    result["items"] = api_value_renderers.RenderValue(
        items, **render_value_args)

    if args.with_total_count:
      if hasattr(aff4_object, "CalculateLength"):
        total_count = aff4_object.CalculateLength()
      else:
        total_count = len(aff4_object)
      result["total_count"] = total_count

    return result


class VFSGRRClientApiObjectRenderer(ApiAFF4ObjectRendererBase):
  """Renderer for VFSGRRClient objects."""

  aff4_type = "VFSGRRClient"

  def RenderObject(self, aff4_object, unused_args):
    """Renders VFSGRRClient as plain JSON-friendly data structure."""
    return dict(summary=api_value_renderers.RenderValue(
        aff4_object.GetSummary(), with_types=True, with_metadata=True))


RENDERERS_CACHE = {}


def RenderAFF4Object(obj, args):
  """Renders given AFF4 object into JSON-friendly data structure."""
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
