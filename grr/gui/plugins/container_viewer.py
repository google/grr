#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2011 Google Inc. All Rights Reserved.
"""This plugin renders AFF4 objects contained within a container."""

import locale
import urllib

import logging

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import utils

# This reads the environment and inits the right locale.
try:
  locale.setlocale(locale.LC_ALL, "")
except locale.Error as e:
  logging.warn("%s, falling back to 'en_US.UTF-8'", e)
  locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


class RDFValueCollectionViewRenderer(semantic.RDFValueArrayRenderer):
  """Render an RDFView."""
  classname = "RDFValueCollectionView"
  name = "Array"

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}' onclick='grr.loadFromHash(
    "{{this.hash|escape}}");' class="grr-button grr-button-red">
  View details.
</a>
""")

  def GenerateHash(self, aff4_path, client_id, token):
    h = dict(aff4_path=aff4_path,
             main="RDFValueCollectionRenderer",
             c=client_id,
             reason=token.reason)

    self.hash = urllib.urlencode(sorted(h.items()))

  def Layout(self, request, response):
    """Layout method for the View attribtue."""
    client_id = request.REQ.get("client_id")
    aff4_path = request.REQ.get("aff4_path", client_id)

    self.GenerateHash(aff4_path, client_id, request.token)

    return super(RDFValueCollectionViewRenderer, self).Layout(request, response)


class AFF4ValueCollectionViewRenderer(RDFValueCollectionViewRenderer):
  """Render a container View."""
  classname = "AFF4CollectionView"

  def GenerateHash(self, aff4_path, client_id, token):

    self.container = aff4_path
    h = dict(container=self.container,
             main="ContainerViewer",
             c=client_id,
             reason=token.reason)

    self.hash = urllib.urlencode(sorted(h.items()))


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

  content_cache = None
  max_items = 10000
  custom_class = "containerFileTable"

  def __init__(self, **kwargs):
    if ContainerFileTable.content_cache is None:
      ContainerFileTable.content_cache = utils.TimeBasedCache()

    super(ContainerFileTable, self).__init__(**kwargs)

    self.AddColumn(semantic.RDFValueColumn("Icon",
                                           renderer=semantic.IconRenderer,
                                           width="40px"))
    self.AddColumn(semantic.AttributeColumn("subject", width="100%"))

  def Layout(self, request, response):
    """The table lists files in the directory and allow file selection."""
    self.state["container"] = request.REQ.get("container")
    self.state["query"] = request.REQ.get("query", "")

    container = aff4.FACTORY.Open(self.state["container"], token=request.token)
    self.AddDynamicColumns(container)

    response = super(ContainerFileTable, self).Layout(request, response)
    return self.CallJavascript(response,
                               "ContainerFileTable.Layout",
                               renderer=self.__class__.__name__,
                               container=self.state["container"])

  def AddDynamicColumns(self, container):
    """Add the columns in the VIEW attribute."""
    view = container.Get(container.Schema.VIEW, [])
    for column_name in view:
      try:
        self.AddColumn(semantic.AttributeColumn(column_name))
      except (KeyError, AttributeError):
        logging.error("Container %s specifies an invalid attribute %s",
                      container.urn, column_name)

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    container_urn = rdfvalue.RDFURN(request.REQ["container"])
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
      children = {}
      for c in sorted(container.Query(query_expression, limit=limit)):
        children[utils.SmartUnicode(c.urn)] = c

      self.content_cache.Put(key, children)

    child_names = children.keys()
    child_names.sort(reverse=sort_direction)

    if len(children) == self.max_items:
      self.columns[0].AddElement(0, rdfvalue.RDFString("nuke"))
      msg = ("This table contains more than %d entries, please use a filter "
             "string or download it as a CSV file.") % self.max_items
      self.columns[1].AddElement(0, rdfvalue.RDFString(msg))
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
    aff4_root = rdfvalue.RDFURN(request.REQ.get("aff4_root", aff4.ROOT_URN))
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
    query_expression = ("subject matches '%s.+'" % utils.EscapeRegex(urn))

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
<div class="navbar-inner">

<ul class="nav navbar-nav pull-left">
<li>
<form id="csv_{{unique|escape}}" action="/render/Download/ContainerFileTable"
   METHOD=post target='_blank' class="navbar-form">
<input type="hidden" name='container' value='{{this.container|escape}}' />
<input type="hidden" id="csv_query" name="query" />
<input type="hidden" id="csv_reason" name="reason" />
<input type="hidden" id="csrfmiddlewaretoken" name="csrfmiddlewaretoken" />
<button id='export' title="Export to CSV" class="btn btn-default">
<img src="/static/images/stock-save.png" class="toolbar_icon" />
</button>
</form>
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
<input class="form-control search-query" type="text" id="query" name="query"
  value="{{this.query|escape}}" size=180></input>
<span class="input-group-btn">
  <button type="submit" class="btn btn-default">Query</button>
</span>
</div>

</form>
</li>
</ul>

</div>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    self.container = request.REQ.get("container")
    self.query = request.REQ.get("query", "")

    response = super(ContainerToolbar, self).Layout(request, response)
    return self.CallJavascript(response, "ContainerToolbar.Layout")


class ContainerViewer(renderers.TemplateRenderer):
  """This is the main view to browse files."""

  layout_template = renderers.Template("""
<div id='toolbar_{{id|escape}}' class="navbar navbar-default"></div>
<div id='{{unique|escape}}' class="fill-parent no-margins toolbar-margin"></div>
""")

  def Layout(self, request, response):
    response = super(ContainerViewer, self).Layout(request, response)
    return self.CallJavascript(response, "ContainerViewer.Layout")


class ContainerViewerSplitter(renderers.Splitter):
  """This is the main view to browse files."""

  left_renderer = "ContainerNavigator"
  top_right_renderer = "ContainerFileTable"
  bottom_right_renderer = "AFF4ObjectRenderer"
