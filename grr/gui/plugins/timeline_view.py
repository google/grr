#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""A viewer for the timeline objects."""

import urllib

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import utils


class TimelineViewRenderer(semantic.RDFValueArrayRenderer):
  """Render a container View.

  Post Parameters:
    - aff4_path: The path to the currently drawn object.
  """
  classname = "TimelineView"

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}'
   onclick='grr.loadFromHash("{{this.hash|escape}}");'
   class="grr-button grr-button-red">
  View details.
</a>
""")

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")

    container = request.REQ.get("aff4_path", "")
    if container:
      self.container = rdfvalue.RDFURN(container)
      self.hash_dict = dict(container=self.container,
                            main="TimelineMain",
                            c=client_id,
                            reason=request.token.reason)
      self.hash = urllib.urlencode(sorted(self.hash_dict.items()))

      return super(TimelineViewRenderer, self).Layout(request, response)


class TimelineMain(renderers.TemplateRenderer):
  """This is the main view to the timeline.

  Internal State (from hash value):
    - container: The container name for the timeline.
    - query: The query to filter.
  """

  layout_template = renderers.Template("""
<div id='toolbar_{{id|escape}}' class="navbar navbar-default"></div>
<div id='{{unique|escape}}' class="fill-parent no-margins toolbar-margin"></div>
""")

  def Layout(self, request, response):
    response = super(TimelineMain, self).Layout(request, response)
    return self.CallJavascript(response, "TimelineMain.Layout")


class TimelineViewerSplitter(renderers.Splitter2Way):
  """This is the main view to browse files.

  Internal State:
    - container: The container name for the timeline.
  """

  top_renderer = "EventTable"
  bottom_renderer = "EventViewTabs"

  def Layout(self, request, response):
    self.state["container"] = request.REQ.get("container")
    return super(TimelineViewerSplitter, self).Layout(request, response)


class TimelineToolbar(renderers.TemplateRenderer):
  """A navigation enhancing toolbar.

  Generated Javascript Events:
    - query_changed(query): When the user submits a new query.
    - hash_state(query): When the user submits a new query.

  Post Parameters:
    - container: The container name for the timeline.
    - query: The query to filter.
  """

  layout_template = renderers.Template("""
<div class="navbar-inner">

<ul class="nav navbar-nav pull-left">
<li>
  <div class="navbar-form">
    <button id='export_{{unique|escape}}' title="Export to CSV"
      class="btn btn-default">
      <img src="/static/images/stock-save.png" class="toolbar_icon" />
    </button>
  </div>
</li>
<li>
  <a>{{this.container|escape}}</a>
</li>
</ul>

<ul class="nav navbar-nav pull-right">
<li class="toolbar-search-box">
<form id="form_{{unique|escape}}" name="query_form"
    class="navbar-form form-search">

<div class="input-group">
<input class="form-control search-query" type="text" id="container_query"
  name="query" value="{{this.query|escape}}" size=180></input>
<span class="input-group-btn">
  <button type="submit" class="btn btn-default">Filter</button>
</span>
</div>

</form>
</li>
</ul>

</div>
""") + renderers.TemplateRenderer.help_template

  context_help_url = "user_manual.html#_timeline"

  def Layout(self, request, response):
    """Render the toolbar."""
    self.container = request.REQ.get("container")
    self.query = request.REQ.get("query", "")
    self.token = request.token

    response = super(TimelineToolbar, self).Layout(request, response)
    return self.CallJavascript(response,
                               "TimelineToolbar.Layout",
                               container=self.container,
                               reason=self.token.reason)


class EventMessageRenderer(semantic.RDFValueRenderer):
  """Render a special message to describe the event based on its type."""

  # If the type is unknown we just say what it is.
  default_template = renderers.Template("""
Event of type {{this.type|escape}}
""")

  event_template_dispatcher = {
      "file.mtime": renderers.Template(
          "<div><pre class='inline'>M--</pre> File modified.</div>"),
      "file.atime": renderers.Template(
          "<div><pre class='inline'>-A-</pre> File access.</div>"),
      "file.ctime": renderers.Template(
          "<div><pre class='inline'>--C</pre> File metadata changed.</div>"),
  }

  def Layout(self, request, response):
    self.type = self.proxy.type
    self.layout_template = self.event_template_dispatcher.get(
        self.type, self.default_template)

    return super(EventMessageRenderer, self).Layout(request, response)


class EventTable(renderers.TableRenderer):
  """Render all the events in a table.

  Listening Javascript Events:
    - query_changed(query): Re-renders the table with the new query.

  Generated Javascript Events:
    - event_select(event_id): When the user selects an event from the
      table. event_id is the sequential number of the event from the start of
      the time series.

  Internal State/Post Parameters:
    - container: The container name for the timeline.
    - query: The query to filter.
  """

  content_cache = None

  def __init__(self, **kwargs):
    if EventTable.content_cache is None:
      EventTable.content_cache = utils.TimeBasedCache()
    super(EventTable, self).__init__(**kwargs)
    self.AddColumn(semantic.AttributeColumn("event.id"))
    self.AddColumn(semantic.AttributeColumn("timestamp"))
    self.AddColumn(semantic.AttributeColumn("subject"))
    self.AddColumn(semantic.RDFValueColumn("Message",
                                           renderer=EventMessageRenderer,
                                           width="100%"))

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    self.state["container"] = request.REQ.get("container")
    self.state["query"] = request.REQ.get("query", "")

    response = super(EventTable, self).Layout(request, response)
    return self.CallJavascript(response,
                               "EventTable.Layout",
                               container=self.state["container"],
                               renderer=self.__class__.__name__)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table."""
    query = request.REQ.get("query", "")
    container = request.REQ.get("container")

    key = utils.SmartUnicode(container)
    key += ":" + query + ":%d"
    try:
      events = self.content_cache.Get(key % start_row)
      self.content_cache.ExpireObject(key % start_row)
      act_row = start_row
    except KeyError:
      fd = aff4.FACTORY.Open(container, token=request.token)
      events = fd.Query(query)
      act_row = 0

    for child in events:
      if act_row < start_row:
        act_row += 1
        continue

      # Add the event to the special message renderer.
      self.AddCell(act_row, "Message", child.event)

      # Add the fd to all the columns
      for column in self.columns:
        # This sets AttributeColumns directly from their fd.
        if isinstance(column, semantic.AttributeColumn):
          column.AddRowFromFd(act_row, child)

      act_row += 1
      if act_row >= end_row:
        self.content_cache.Put(key % act_row, events)
        # Tell the table there are more rows.
        return True


class EventViewTabs(renderers.TabLayout):
  """Show tabs to allow inspection of the event.

  Listening Javascript Events:
    - event_select(event_id): Indicates the user has selected this event in the
      table, we re-render ourselves with the new event_id.

  Post Parameters:
    - container: The container name for the timeline.
    - event: The event id within the timeseries container to render.
  """

  event_queue = "event_select"
  names = ["Event", "Subject"]
  delegated_renderers = ["EventView", "EventSubjectView"]

  def Layout(self, request, response):
    """Check if the file is a readable and disable the tabs."""
    self.state["container"] = request.REQ.get("container")
    self.state["event"] = request.REQ.get("event")

    response = super(EventViewTabs, self).Layout(request, response)
    return self.CallJavascript(response,
                               "EventViewTabs.Layout",
                               event_queue=self.event_queue,
                               container=self.state["container"],
                               renderer=self.__class__.__name__)


class EventSubjectView(fileview.AFF4Stats):
  """View the subject of the event.

  Post Parameters:
    - container: The container name for the timeline.
    - event: The event id.
  """

  def GetEvent(self, request):
    event_id = request.REQ.get("event")
    if event_id:
      event_id = int(event_id)
      container = request.REQ.get("container")
      fd = aff4.FACTORY.Open(container, token=request.token)

      child = None
      for child in fd:
        # Found the right event.
        if child.id == event_id:
          return child

  def Layout(self, request, response):
    """Find the event and show stats about it."""
    event = self.GetEvent(request)
    if event:
      subject = aff4.FACTORY.Open(event.subject,
                                  token=request.token,
                                  age=aff4.ALL_TIMES)
      self.classes = self.RenderAFF4Attributes(subject, request)
      self.path = subject.urn

      return super(EventSubjectView, self).Layout(request, response)


class EventView(EventSubjectView):
  """View the event details."""

  error_message = renderers.Template(
      "Please select an event in the table above.")

  def Layout(self, request, response):
    """Retrieve the event aff4 object."""
    event = self.GetEvent(request)
    if event:
      event_class = aff4.AFF4Object.classes["AFF4Event"]
      self.classes = self.RenderAFF4Attributes(event_class(event), request)
      self.path = "Event %s at %s" % (event.id,
                                      rdfvalue.RDFDatetime(event.timestamp))

      return renderers.TemplateRenderer.Layout(self, request, response)

    # Just return a generic error message.
    return renderers.TemplateRenderer.Layout(self, request, response,
                                             self.error_message)


class RDFEventRenderer(semantic.RDFProtoRenderer):
  """A renderer for Event Protobufs."""
  classname = "RDFEvent"
  name = "Event"
