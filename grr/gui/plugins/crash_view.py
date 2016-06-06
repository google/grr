#!/usr/bin/env python
"""Interface for crash information."""


import urllib

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib.aff4_objects import collects


class ClientCrashDetailsRenderer(semantic.RDFValueRenderer):
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
""") + renderers.TemplateRenderer.help_template

  context_help_url = "admin.html#_crashes"

  def Layout(self, request, response):
    if self.proxy.session_id:
      self.hash = urllib.urlencode(dict(c=self.proxy.client_id,
                                        flow=self.proxy.session_id,
                                        main="ManageFlows"))
    client_info_renderer = semantic.FindRendererForObject(
        self.proxy.client_info)
    self.client_info = client_info_renderer.RawHTML(request)
    super(ClientCrashDetailsRenderer, self).Layout(request, response)


class ClientCrashCollectionRenderer(renderers.TableRenderer):
  """Renderer for RDFValueCollection of ClientCrash."""

  size = 0
  crashes_urn = None

  def __init__(self, **kwargs):
    super(ClientCrashCollectionRenderer, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Client Id", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Crash Details",
                                           width="90%",
                                           renderer=ClientCrashDetailsRenderer))

  def BuildTable(self, start_row, end_row, request):
    """Builds table of ClientCrash'es."""
    crashes_urn = str(self.state.get("crashes_urn") or
                      request.REQ.get("crashes_urn"))

    try:
      collection = aff4.FACTORY.Open(
          crashes_urn,
          aff4_type=collects.PackedVersionedCollection,
          token=request.token)
    except IOError:
      return

    for row_index, value in enumerate(collection):
      if row_index < start_row:
        continue
      row_index += 1
      if row_index > end_row:
        # Indicate that there are more rows.
        return True
      self.AddCell(row_index, "Client Id", value.client_id)
      self.AddCell(row_index, "Crash Details", value)

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
