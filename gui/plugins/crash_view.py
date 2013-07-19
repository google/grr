#!/usr/bin/env python
"""Interface for crash information."""


import itertools
import urllib

from grr.gui import renderers
from grr.lib import aff4


class ClientCrashDetailsRenderer(renderers.RDFValueRenderer):
  """Renders details about a single client crash."""

  layout_template = renderers.Template("""
<dl class="dl-horizontal">
  <dt>Timestamp</dt><dd>{{this.proxy.timestamp}}</dd>
  <dt>Crash Type</dt><dd>{{this.proxy.crash_type}}</dd>

  {% if this.proxy.crash_message %}
  <dt>Crash Message</dt><dd>{{this.proxy.crash_message}}</dd>
  {% endif %}

  {% if this.proxy.backtrace %}
  <dt>Backtrace</dt><dd>{{this.proxy.backtrace}}</dd>
  {% endif %}

  {% if this.proxy.session_id %}
  <dt>Session Id</dt>
  <dd>
     <a href="/#{{this.hash|escape}}"
        onclick='grr.loadFromHash("{{this.hash|escapejs}}")'>
        {{this.proxy.session_id|escape}}
     </a>
  </dd>
  {% endif %}

  <dt>Client Information</dt>
  <dd>{{this.client_info|safe}}</dd>
</dl>
""")

  def Layout(self, request, response):
    if self.proxy.session_id:
      self.hash = urllib.urlencode(dict(c=self.proxy.client_id,
                                        flow=self.proxy.session_id,
                                        main="ManageFlows"))
    client_info_renderer = renderers.FindRendererForObject(
        self.proxy.client_info)
    self.client_info = client_info_renderer.RawHTML()
    super(ClientCrashDetailsRenderer, self).Layout(request, response)


class ClientCrashCollectionRenderer(renderers.TableRenderer):
  """Renderer for RDFValueCollection of ClientCrash."""

  size = 0
  crashes_urn = None

  def __init__(self, **kwargs):
    super(ClientCrashCollectionRenderer, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn("Client Id", width="10%"))
    self.AddColumn(renderers.RDFValueColumn(
        "Crash Details", width="90%", renderer=ClientCrashDetailsRenderer))

  def BuildTable(self, start_row, end_row, request):
    """Builds table of ClientCrash'es."""
    crashes_urn = str(self.state.get("crashes_urn") or
                      request.REQ.get("crashes_urn"))

    try:
      collection = aff4.FACTORY.Open(crashes_urn,
                                     aff4_type="RDFValueCollection",
                                     token=request.token)
    except IOError:
      return

    self.size = len(collection)

    row_index = start_row
    for value in itertools.islice(collection, start_row, end_row):
      self.AddCell(row_index, "Client Id", value.client_id)
      self.AddCell(row_index, "Crash Details", value)
      row_index += 1

  def Layout(self, request, response):
    self.state["crashes_urn"] = str(self.crashes_urn or
                                    request.REQ.get("crashes_urn"))
    super(ClientCrashCollectionRenderer, self).Layout(request, response)


class GlobalCrashesRenderer(ClientCrashCollectionRenderer):
  """View launched flows in a tree."""
  description = "All Clients Crashes"
  behaviours = frozenset(["GeneralAdvanced"])
  order = 50
  crashes_urn = aff4.ROOT_URN.Add("crashes")
