#!/usr/bin/env python
"""API handlers for accessing AFF4 objects."""



from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import api_pb2


CATEGORY = "AFF4"


class ApiGetAff4ObjectArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetAff4ObjectArgs


class ApiGetAff4ObjectHandler(api_call_handler_base.ApiCallHandler):
  """Renders AFF4 objects in JSON format.

  Query parameters interpretation depends on the type of the AFF4 object
  that's being fetched. See documentation on AFF4 object handlers for
  details.
  """

  category = CATEGORY
  args_type = ApiGetAff4ObjectArgs

  @classmethod
  def GetAdditionalArgsTypes(cls):
    results = {}
    for aff4_renderer_cls in (api_aff4_object_renderers.
                              ApiAFF4ObjectRendererBase.classes.values()):
      results[aff4_renderer_cls.aff4_type] = aff4_renderer_cls.args_type
    return results

  additional_args_types = GetAdditionalArgsTypes

  def Render(self, args, token=None):
    aff4_object = aff4.FACTORY.Open(args.aff4_path, token=token)
    rendered_data = api_aff4_object_renderers.RenderAFF4Object(
        aff4_object, [x.args for x in args.additional_args])

    return rendered_data


class ApiGetAff4IndexArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetAff4IndexArgs


class ApiGetAff4IndexHandler(api_call_handler_base.ApiCallHandler):
  """Returns list of children objects for the object with a given path."""

  category = CATEGORY
  args_type = ApiGetAff4IndexArgs

  def Render(self, args, token=None):
    encoded_urns = []

    aff4_path = rdfvalue.RDFURN(args.aff4_path)
    index_prefix = "index:dir/"
    for predicate, _, timestamp in data_store.DB.ResolvePrefix(
        aff4_path, index_prefix, token=token,
        timestamp=data_store.DB.NEWEST_TIMESTAMP, limit=1000000):

      urn = aff4_path.Add(predicate[len(index_prefix):])
      encoded_urns.append([utils.SmartUnicode(urn), timestamp])

    return encoded_urns
