#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This plugin renders AFF4 objects contained within a container."""

import json
import locale

from django import http
from django import template

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import utils

# this reads the environment and inits the right locale
locale.setlocale(locale.LC_ALL, "")


class ViewRenderer(renderers.RDFValueRenderer):
  """Render a container View."""
  ClassName = "View"
  name = "Array"

  layout_template = template.Template("""
<a href="/#container={{container|urlencode}}&main=ContainerViewer"
  target=new>View details.</a>
""")

  def Layout(self, request, response):
    container = aff4.RDFURN(request.REQ.get("client_id", "")).Add(
      request.REQ.get("file_view_path", ""))

    return self.RenderFromTemplate(self.layout_template, response,
                                   container=utils.SmartUnicode(container))


class ContainerAFF4Stats(fileview.AFF4Stats):
  """Display the stats of a container object."""

  def Layout(self, request, response):
    """Introspect the Schema for each object."""
    response = renderers.Renderer.Layout(self, request, response)
    urn = aff4.ROOT_URN.Add(request.REQ.get("file_view_path", "/"))

    try:
      fd = aff4.FACTORY.Open(urn)
      classes = self.RenderAFF4Attributes(fd, request)

      return self.RenderFromTemplate(
          self.layout_template,
          response, classes=classes, id=self.id, unique=self.unique,
          path=fd.urn)
    except IOError: pass


class ContainerViewTabs(fileview.FileViewTabs):
  names = ["Stats", "Download"]
  renderers = ["ContainerAFF4Stats", "DownloadView"]


class ContainerFileTable(fileview.FileTable):
  """A table that displays the content of an AFF4Collection."""

  # We receive change path events from this queue
  event_queue = "tree_select"
  # Set the first column to be zero width
  table_options = {
      "aoColumnDefs": [
          {"sWidth": "1px", "aTargets": [0]}
          ],
      "bAutoWidth": False,
      "table_hash": "tb",
      }

  # We publish selected paths to this queue
  selection_publish_queue = "file_select"
  format = template.Template("""
<"TableHeader"<"H"lrp>><"TableBody_{{unique}}"t><"TableFooter"<"F"p>>""")

  # Subscribe for the event queue and when events arrive refresh the
  # table.
  vfs_table_template = template.Template("""<script>
  // Update the table when the tree changes
  grr.subscribe("{{ event_queue|escapejs }}", function(path, selected_id,
    update_hash) {
          grr.state.path = path;
          grr.state.query = $("input#query").val() || "";

          //Redraw the table
          grr.redrawTable("table_{{unique}}");

          // If the user really clicked the tree, we reset the hash
          if (update_hash != 'no_hash') {
            grr.publish('hash_state', 'tb', undefined);
          }
      }, 'table_{{ unique }}');

  //Receive the selection event and emit a path
  grr.subscribe("table_selection_{{ id|escapejs }}", function(node) {
    var path = grr.state.path || "";
    if (node) {
      var element = node.find("span")[0];
      if (element) {
        var filename = element.innerHTML;
        grr.publish("{{ selection_publish_queue|escapejs }}",
                     filename);
      };
    };
  }, 'table_{{ unique }}');

  $(".TableBody_{{unique}}").addClass("TableBody");

   </script>""")

  def __init__(self):
    renderers.TableRenderer.__init__(self)
    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer))
    self.AddColumn(renderers.AttributeColumn("subject"))

  def Layout(self, request, response):
    """The table lists files in the directory and allow file selection."""
    self.AddDynamicColumns(request)

    response = super(ContainerFileTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.vfs_table_template, response,
        id=self.id, event_queue=self.event_queue, unique=self.unique,
        selection_publish_queue=self.selection_publish_queue,
        )

  def AddDynamicColumns(self, request):
    """Add the columns in the VIEW attribute."""
    container_urn = aff4.RDFURN(request.REQ["container"])
    fd = aff4.FACTORY.Open(container_urn)
    view = fd.Get(fd.Schema.VIEW)
    if view:
      for column_name in view:
        column_name = column_name.string
        self.AddColumn(renderers.AttributeColumn(column_name))

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    self.AddDynamicColumns(request)

    sort_direction = request.REQ.get("sSortDir_0", "asc") == "desc"
    container_urn = aff4.RDFURN(request.REQ["container"])

    # TODO(user): Implement query filtering here.
    query = request.REQ.get("query")
    if not query:
      query = "subject matches '.'"

    # For now we just list the directory
    container = aff4.FACTORY.Open(container_urn)
    query_expression = query
    children = dict(((utils.SmartUnicode(c.urn), c)
                     for c in container.Query(query_expression)))

    child_names = children.keys()
    child_names.sort(reverse=sort_direction)

    row_index = start_row

    # Make sure the table knows how large it is.
    self.size = len(child_names)

    for child_urn in child_names:
      fd = children[child_urn]
      row_attributes = dict()

      # Add the fd to all the columns
      for column in self.columns:
        try:
          column.AddRowFromFd(row_index, fd)
        except AttributeError: pass

      if "Container" in fd.behaviours:
        row_attributes["Icon"] = "directory"
      else:
        row_attributes["Icon"] = "file"

      self.AddRow(row_attributes, row_index=row_index)
      row_index += 1
      if row_index > end_row:
        return


class ContainerNavigator(renderers.TreeRenderer):
  """A FileSystem navigation Tree."""

  renderer_template = template.Template("""
<script>
grr.grrTree("{{ renderer }}", "{{ id }}",
            "{{ publish_select_queue }}", {{ state|escapejs }},
            function (data, textStatus, jqXHR) {
              if (!data.id) return;

              if (data.message) {
                // Publish the message if it exist
                grr.publish('grr_messages', data.message);
              };
             });
</script>""")

  def RenderAjax(self, request, response):
    """Renders tree leafs for filesystem path."""
    response = super(ContainerNavigator, self).RenderAjax(request, response)

    result = []

    container_urn = aff4.RDFURN(request.REQ["container"])
    path = aff4.ROOT_URN.Add(request.REQ.get("path", "/"))

    # TODO(user): Implement query filtering
    message = ""

    # Open the container
    try:
      container = aff4.FACTORY.Open(container_urn)
      # Find only direct children of this tree branch.
      query_expression = (
          "subject matches '%s.+'" % data_store.EscapeRegex(path))

      branches = set()
      for child in container.Query(query_expression):
        try:
          branch, _ = child.urn.RelativeName(path).split("/", 1)
          branches.add(branch)
        except ValueError: pass

      # This actually sorts by the URN (which is UTF8) - I am not sure about the
      # correct sorting order for unicode string?
      directory_like = list(branches)
      directory_like.sort(cmp=locale.strcoll)

      for d in directory_like:
        result.append(
            dict(data=d,
                 attr=dict(id=renderers.DeriveIDFromPath(
                     utils.JoinPath(path, d))),
                 children=[],
                 state="closed"))
    except IOError, e:
      message = "Error fetching %s: %s" % (path, e)

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(dict(data=result, message=message,
                                                 id=self.id)),
                             mimetype="application/json")


class ContainerToolbar(renderers.Renderer):
  """A navigation enhancing toolbar."""

  template = template.Template("""
<a href="/render/Download/ContainerFileTable?container={{container}}"
  target=_new >
<button id='export' title="Export to CSV">
<img src="/static/images/stock-save.png">
</button></a>
{{container}}
<form id="{{unique}}" action="POST">
Query
<input type="text" id="query" name="query"
  value="{{query|escapejs}}" size=180></input>
</form>
<script>
$('#export').button();
grr.subscribe("tree_select", function(path) {
   $("input#query").val("subject startswith aff4:"+path);
}, "{{unique}}");
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    response = super(ContainerToolbar, self).Layout(request, response)

    container = request.REQ.get("container")
    query = request.REQ.get("query", "")

    return self.RenderFromTemplate(
        self.template, response, container=container, query=query,
        unique=self.unique, id=self.id)


class QueryDialog(renderers.Renderer):
  """Render a query builder."""

  layout_template = template.Template("""
<form id="form">
<select id="attribute">
{% for attribute in attributes %}
<option>{{attribute}}</option>
{% endfor %}
</select>
<select id="operators">
</select>
</form>
<script>
$("#attribute").change(function () {
  grr.update("QueryDialog", "operators", {attribute: $(this).val()});
});
</script>
""")

  ajax_template = template.Template("""
{% for opt in operators %}
<option>{{opt}}</option>
{% endfor %}
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    response = super(QueryDialog, self).Layout(request, response)

    attributes = []
    for name, attribute in aff4.Attribute.NAMES.items():
      attributes.extend(attribute.Fields(name))

    return self.RenderFromTemplate(
        self.layout_template, response, attributes=attributes,
        unique=self.unique, id=self.id)

  def RenderAjax(self, request, response):
    response = super(QueryDialog, self).RenderAjax(request, response)

    attribute = request.REQ.get("attribute")
    operators = aff4.Attribute.NAMES[attribute].attribute_type.operators.keys()

    return self.RenderFromTemplate(
        self.ajax_template, response, operators=operators, id=self.id)


class ContainerViewer(renderers.Renderer):
  """This is the main view to browse files."""
  category = "Inspect Client"
  description = "Browse Analysis result."

  template = template.Template("""
<div id='toolbar_{{id}}' class=toolbar></div>
<div id='{{id}}'></div>
<script>
  grr.state.container = grr.hash.container;
  grr.state.query = grr.hash.query || "";

  grr.layout("ContainerToolbar", "toolbar_{{id}}");
  grr.layout("ContainerViewerSplitter", "{{id}}");
  grr.subscribe("GeometryChange", function () {
    grr.fixHeight($("#{{id}}"));
  }, "{{id}}");
</script>
""")

  def Layout(self, request, response):
    """Show the main view only if we have a client_id."""
    response = renderers.Renderer.Layout(self, request, response)

    container = request.REQ.get("container")

    return self.RenderFromTemplate(
        self.template, response, container=container, id=self.unique)


class ContainerViewerSplitter(renderers.Splitter):
  """This is the main view to browse files."""

  search_client_template = template.Template("""
<h1 id="{{unique}}">Select a container</h1>
Please search for a client above.

<script>
   grr.subscribe("client_selection", function (cn) {
      grr.layout("{{renderer}}", "{{id}}", {client_id: cn});
   }, "{{unique}}");
</script>
""")

  def __init__(self):
    self.left_renderer = "ContainerNavigator"
    self.top_right_renderer = "ContainerFileTable"
    self.bottom_right_renderer = "ContainerViewTabs"

    super(ContainerViewerSplitter, self).__init__()

  def Layout(self, request, response):
    """Show the main view only if we have a client_id."""
    renderers.Renderer.Layout(self, request, response)

    container = request.REQ.get("container")
    if not container:
      return self.RenderFromTemplate(
          self.search_client_template, response,
          renderer=self.__class__.__name__, unique=self.unique, id=self.id)

    return super(ContainerViewerSplitter, self).Layout(request, response)
