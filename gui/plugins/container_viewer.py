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

import locale
import urllib

import logging

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import utils

# This reads the environment and inits the right locale.
locale.setlocale(locale.LC_ALL, "")


class ViewRenderer(renderers.RDFValueRenderer):
  """Render a container View."""
  ClassName = "View"
  name = "Array"

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}' onclick='grr.loadFromHash(
    "{{this.hash|escape}}");' class="grr-button grr-button-red">
  View details.
</a>
""")

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")
    self.container = aff4.RDFURN(request.REQ.get("aff4_path", client_id))

    h = dict(container=self.container, main="ContainerViewer", c=client_id,
             reason=request.token.reason)

    self.hash = urllib.urlencode(h)

    return super(ViewRenderer, self).Layout(request, response)


class ContainerAFF4Stats(fileview.AFF4Stats):
  """Display the stats of a container object."""


class ContainerViewTabs(fileview.FileViewTabs):
  names = ["Stats", "Download"]
  delegated_renderers = ["ContainerAFF4Stats", "DownloadView"]


class ContainerFileTable(renderers.TableRenderer):
  """A table that displays the content of an AFF4Collection.

  Listening Javascript Events:
    - query_changed(query) - When the query changes, we re-render the entire
      table.

  Internal State:
    - container: The container to query.
    - query: The query string to use.
  """
  layout_template = (renderers.TableRenderer.layout_template + """
<script>
  //Receive the selection event and emit a path
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var element = node.find("span")[0];
      if (element) {
        var filename = element.innerHTML;
        grr.publish("file_select", filename);
      };
    };
  }, '{{ unique|escapejs }}');

  // Redraw the table if the query changes
  grr.subscribe("query_changed", function(query) {
    grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
      container: "{{this.state.container|escapejs}}",
      query: query,
    });
  }, "{{unique|escapejs}}");
</script>""")

  content_cache = None
  max_items = 10000

  def __init__(self):
    if ContainerFileTable.content_cache is None:
      ContainerFileTable.content_cache = utils.TimeBasedCache()

    renderers.TableRenderer.__init__(self)
    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer, width=0))
    self.AddColumn(renderers.AttributeColumn("subject"))

  def Layout(self, request, response):
    """The table lists files in the directory and allow file selection."""
    self.state["container"] = request.REQ.get("container")
    self.state["query"] = request.REQ.get("query", "")

    container = aff4.FACTORY.Open(self.state["container"], token=request.token)
    self.AddDynamicColumns(container)

    return super(ContainerFileTable, self).Layout(request, response)

  def AddDynamicColumns(self, container):
    """Add the columns in the VIEW attribute."""
    view = container.Get(container.Schema.VIEW)
    if view:
      for column_name in view:
        column_name = column_name.string
        try:
          self.AddColumn(renderers.AttributeColumn(column_name))
        except (KeyError, AttributeError):
          logging.error("Container %s specifies an invalid attribute %s",
                        container.urn, column_name)

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    container_urn = aff4.RDFURN(request.REQ["container"])
    container = aff4.FACTORY.Open(container_urn, token=request.token)
    self.AddDynamicColumns(container)

    sort_direction = request.REQ.get("sSortDir_0", "asc") == "desc"

    # Get the query from the user.
    query_expression = request.REQ.get("query")
    if not query_expression:
      query_expression = "subject matches '.'"

    limit = max(self.max_items, end_row)

    key = utils.SmartUnicode(container_urn)
    key += ":" + query_expression + ":" + str(limit)
    try:
      children = self.content_cache.Get(key)
    except KeyError:
      children = dict(((utils.SmartUnicode(c.urn), c)
                       for c in container.Query(query_expression,
                                                limit=limit)))
      self.content_cache.Put(key, children)

    child_names = children.keys()
    child_names.sort(reverse=sort_direction)

    if len(children) == self.max_items:
      self.columns[0].AddElement(0, aff4.RDFString("nuke"))
      msg = ("This table contains more than %d entries, please use a filter "
             "string or download it as a CSV file.") % self.max_items
      self.columns[1].AddElement(0, aff4.RDFString(msg))
      self.AddRow({}, row_index=0)
      return

    row_index = start_row

    # Make sure the table knows how large it is.
    self.size = len(child_names)

    for child_urn in child_names[row_index:]:
      fd = children[child_urn]
      row_attributes = dict()

      # Add the fd to all the columns
      for column in self.columns:
        try:
          column.AddRowFromFd(row_index, fd)
        except AttributeError:
          pass

      if "Container" in fd.behaviours:
        row_attributes["Icon"] = dict(icon="directory")
      else:
        row_attributes["Icon"] = dict(icon="file")

      self.AddRow(row_attributes, row_index=row_index)
      row_index += 1
      if row_index > end_row:
        return


class ContainerNavigator(renderers.TreeRenderer):
  """A Container navigation Tree.

  Note that this renderer is only suitable for virtualized containers which are
  not too large. This is due to the way the tree construction is done. To view
  the VFS itself as a container use the VFSContainer renderer.

  Generated Javascript Events:
    - tree_select(aff4_path) - The full aff4 path for the branch which the user
      selected.

  Internal State:
    - aff4_root: The aff4 node which forms the root of this tree.
    - container: The container we are querying.
  """

  def Layout(self, request, response):
    self.state["container"] = request.REQ.get("container")
    self.state["aff4_root"] = request.REQ.get("aff4_root", str(aff4.ROOT_URN))

    return super(ContainerNavigator, self).Layout(request, response)

  def RenderBranch(self, path, request):
    """Renders tree leafs for filesystem path."""
    aff4_root = aff4.RDFURN(request.REQ.get("aff4_root", aff4.ROOT_URN))
    container = request.REQ.get("container")
    if not container:
      raise RuntimeError("Container not provided.")

    # Path is relative to the aff4 root specified.
    urn = aff4_root.Add(path)

    # Open the container
    container = aff4.FACTORY.Open(container, token=request.token)
    # Find only direct children of this tree branch.

    # NOTE: Although all AFF4Volumes are also containers, this gui element is
    # really only suitable for showing AFF4Collection objects which are not very
    # large, since we essentially list all members.
    query_expression = ("subject matches '%s.+'" % data_store.EscapeRegex(urn))

    branches = set()

    for child in container.Query(query_expression):
      try:
        branch, _ = child.urn.RelativeName(urn).split("/", 1)
        branches.add(branch)
      except ValueError:
        pass

    # This actually sorts by the URN (which is UTF8) - I am not sure about the
    # correct sorting order for unicode string?
    directory_like = list(branches)
    directory_like.sort(cmp=locale.strcoll)

    for d in directory_like:
      self.AddElement(d)


class ContainerToolbar(renderers.TemplateRenderer):
  """A navigation enhancing toolbar.

  Listening Javascript Events:
    - tree_select(aff4_path): Updates the query.

  Generated Javascript Events:
    - query_changed(query): The query has been updated by the user. The query is
      set to be the full aff4 path of the tree node which was selected.
  """

  layout_template = renderers.Template("""
<form id="csv_{{unique|escape}}" action="/render/Download/ContainerFileTable"
   METHOD=post target='_blank'>
<input type="hidden" name='container' value='{{this.container|escape}}' />
<input type="hidden" id="csv_query" name="query" />
<button id='export' title="Export to CSV">
<img src="/static/images/stock-save.png">
</button>
{{this.container|escape}}
</form>
<form id="form_{{unique|escape}}" name="query_form">
Query
<input type="text" id="query" name="query"
  value="{{this.query|escape}}" size=180></input>
</form>
<script>
$('#export').button().click(function () {
  $("input#csv_query").val($("input#query").val());
  $("#csv_{{unique|escape}}").submit();
});

grr.subscribe("tree_select", function(path) {
   $("input#query").val("subject startswith '" +
      path.replace("'", "\\'") + "/'");
   $("#form_{{unique|escapejs}}").submit();
}, "form_{{unique|escapejs}}");

$("#form_{{unique|escapejs}}").submit(function () {
  query = $("input#query").val();
  grr.publish('query_changed', query);

  return false;
});
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    self.container = request.REQ.get("container")
    self.query = request.REQ.get("query", "")

    return super(ContainerToolbar, self).Layout(request, response)


class ContainerViewer(renderers.TemplateRenderer):
  """This is the main view to browse files."""

  layout_template = renderers.Template("""
<div id='toolbar_{{id|escape}}' class=toolbar></div>
<div id='{{unique|escape}}'></div>
<script>
  grr.state.container = grr.hash.container;
  grr.state.query = grr.hash.query || "";

  grr.layout("ContainerToolbar", "toolbar_{{id|escapejs}}");
  grr.layout("ContainerViewerSplitter", "{{unique|escapejs}}");
  grr.subscribe("GeometryChange", function (id) {
    if(id != "{{id|escapejs}}") return;
    grr.fixHeight($("#{{unique|escapejs}}"));
  }, "{{unique|escapejs}}");
</script>
""")


class ContainerViewerSplitter(renderers.Splitter):
  """This is the main view to browse files."""

  left_renderer = "ContainerNavigator"
  top_right_renderer = "ContainerFileTable"
  bottom_right_renderer = "ContainerViewTabs"
