#!/usr/bin/env python
"""API renderers for accessing AFF4 objects."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_object_renderers
from grr.gui import api_renderers
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue


class ApiAff4Renderer(api_renderers.ApiRenderer):
  """Renders AFF4 objects in JSON format."""

  method = "GET"
  route = "/api/aff4/<path:aff4_path>"

  def Render(self, request):
    aff4_object = aff4.FACTORY.Open(request["aff4_path"],
                                    token=request["token"])
    rendered_data = api_object_renderers.RenderObject(aff4_object, request)

    return rendered_data


class ApiAff4IndexRenderer(api_renderers.ApiRenderer):
  """Renders AFF4 objects in JSON format."""

  method = "GET"
  route = "/api/aff4-index/<path:aff4_path>"

  def Render(self, request):
    encoded_urns = []

    aff4_path = rdfvalue.RDFURN(request.aff4_path)
    index_prefix = "index:dir/"
    for predicate, _, timestamp in data_store.DB.ResolveRegex(
        aff4_path, index_prefix + ".+", token=request.token,
        timestamp=data_store.DB.NEWEST_TIMESTAMP, limit=1000000):

      urn = aff4_path.Add(predicate[len(index_prefix):])
      encoded_urns.append([api_object_renderers.RenderObject(urn),
                           timestamp])

    return encoded_urns
