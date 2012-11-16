#!/usr/bin/env python
"""This module contains base classes for different kind of renderers."""


import copy
import csv
import functools
import json
import os
import re
import StringIO
import traceback


from django import http
from django import template

from M2Crypto import BN

import logging

# pylint: disable=W0611
from grr import artifacts
# pylint: enable=W0611
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import data_store
from grr.lib import registry
from grr.lib import utils

# Global counter for ids
COUNTER = 1

# Maximum size of tables that can be downloaded
MAX_ROW_LIMIT = 1000000


class VerifyRenderers(registry.InitHook):

  def RunOnce(self):
    renderers = {}

    for candidate in RDFValueRenderer.classes.values():
      if issubclass(candidate, RDFValueRenderer) and candidate.classname:
        renderers.setdefault(candidate.classname, []).append(candidate)

    for r in renderers:
      if len(renderers[r]) > 1:
        raise RuntimeError("More than one renderer found for %s!" % str(r))


class Template(template.Template):
  """A specialized template which supports concatenation."""

  def __init__(self, template_string):
    self.template_string = template_string
    super(Template, self).__init__(template_string)

  def Copy(self):
    return Template(self.template_string)

  def __str__(self):
    return self.template_string

  def __add__(self, other):
    """Support concatenation."""
    return Template(self.template_string + utils.SmartStr(other))

  def __radd__(self, other):
    """Support concatenation."""
    return Template(utils.SmartStr(other) + self.template_string)


class RDFValueColumn(object):
  """A column holds a bunch of cell values which are RDFValue instances."""

  width = None

  def __init__(self, name, header=None, renderer=None, sortable=False,
               width=None):
    """Constructor.

    Args:

     name: The name of this column.The name of this column normally
       shown in the column header.

     header: (Optional) If exists, we call its Layout() method to
       render the column headers.

     renderer: The RDFValueRenderer that should be used in this column. Default
       is None - meaning it will be automatically calculated.

     sortable: Should this column be sortable.
     width: The ratio (in percent) of this column relative to the table width.
    """
    self.name = name
    self.header = header
    self.width = width
    self.renderer = renderer
    self.sortable = sortable
    # This stores all Elements on this column. The column may be
    # sparse.
    self.rows = {}

  def LayoutHeader(self, request, response):
    if self.header is not None:
      try:
        self.header.Layout(request, response)
      except AttributeError:
        response.write(utils.SmartStr(self.header))
    else:
      response.write(utils.SmartStr(self.name))

  def GetElement(self, index):
    return self.rows[index]

  def AddElement(self, index, element):
    self.rows[index] = element

  def RenderRow(self, index, request, row_options=None):
    """Render the RDFValue stored at the specific index."""
    value = self.rows.get(index, "")
    if row_options is not None:
      row_options["row_id"] = index

    renderer = self.renderer
    if renderer is None:
      # What is the RDFValueRenderer for this attribute?
      renderer = RDFValueRenderer.RendererForRDFValue(
          value.__class__.__name__)

    # Intantiate the renderer and return the HTML
    if renderer:
      return renderer(value).RawHTML(request)
    else:
      return utils.SmartStr(value)


class AttributeColumn(RDFValueColumn):
  """A table column which can be filled from an AFF4Object."""

  def __init__(self, name, **kwargs):
    # Locate the attribute
    self.attribute = aff4.Attribute.GetAttributeByName(name)

    RDFValueColumn.__init__(self, name, **kwargs)

  def AddRowFromFd(self, index, fd):
    """Add a new value from the fd."""
    value = fd.Get(self.attribute)
    if value is not None:
      self.rows[index] = value


class Renderer(object):
  """Baseclass for renderer classes."""

  __metaclass__ = registry.MetaclassRegistry

  # The following should be set for renderers that should be visible from the
  # main menu. Note- this does not allow inheritance - must be set for each
  # class that should be visible.
  description = None

  # This property is used in GUIs to define behaviours. These can take arbitrary
  # values as needed. Behaviours are read only and set in the class definition.
  # For example "Host" behaviours represent a top level Host specific action
  # (appears in the host menu), while "General" represents a top level General
  # renderer (appears in the General menu).
  behaviours = frozenset()

  # Each widget maintains its own state.
  state = None

  # This is a maximum time in seconds the renderer is allowed to run. Renderers
  # exceeding this time are killed softly (i.e. the time is not a guaranteed
  # maximum, but will be used as a guide).
  max_execution_time = 60

  def __init__(self):
    self.state = {}

  def RenderAjax(self, request, response):
    """Responds to an AJAX request.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      JSON encoded parameters as expected by the javascript widget.
    """
    self.id = request.REQ.get("id", hash(self))
    self.unique = GetNextId()

    return response

  def Layout(self, request, response):
    """Outputs HTML to be inserted into the DOM in order to layout this widget.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      HTML to insert into the DOM.
    """
    if request:
      self.id = request.REQ.get("id", hash(self))
    else:
      self.id = 0

    self.unique = GetNextId()

    # Make the encoded state available for our template.
    encoder = json.JSONEncoder()
    self.state_json = encoder.encode(self.state)

    return response

  def RenderFromTemplate(self, template_obj, response, **kwargs):
    """A helper function to render output from a template.

    Args:
       template_obj: The template object to use.
       response: A HttpResponse object
       **kwargs: Arguments to be expanded into the template.

    Returns:
       the same response object we got.

    Raises:
       RuntimeError: if the template is not an instance of Template.
    """
    context = template.Context(kwargs)
    if not isinstance(template_obj, Template):
      raise RuntimeError("template must be an instance of Template")

    response.write(template_obj.render(context))
    return response

  def FormatFromTemplate(self, template_obj, **kwargs):
    """Return a safe formatted unicode object using a template."""
    return template_obj.render(template.Context(kwargs)).encode("utf8")

  def FormatFromString(self, string, mimetype="text/html", **kwargs):
    """Returns a http response from a dynamically compiled template."""
    result = http.HttpResponse(mimetype=mimetype)
    template_obj = Template(string)
    return self.RenderFromTemplate(template_obj, result, **kwargs)

  @classmethod
  def CheckAccess(cls, request):
    """Checks if the user is allowed to view this renderer.

    Args:
      request: A request object.

    Raises:
      data_store.UnauthorizedAccess if the user is not permitted.
    """


class UserLabelCheckMixin(object):
  """Checks the user has a label or deny access to this renderer."""

  # This should be overridden in the mixed class.
  AUTHORIZED_LABELS = []

  @classmethod
  def CheckAccess(cls, request):
    """If the user is not in the AUTHORIZED_LABELS, reject this renderer."""
    try:
      user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users")
                                  .Add(request.token.username)
                                  .Add("labels"), token=request.token)

      for label in user_fd.Get(user_fd.Schema.LABEL).data.label:
        if label in cls.AUTHORIZED_LABELS:
          return
    except IOError:
      pass

    raise data_store.UnauthorizedAccess("User %s not allowed." %
                                        request.token.username)


class ErrorHandler(Renderer):
  """An error handler decorator which can be applied on individual methods."""

  message_template = Template("""
<script>
  grr.publish("grr_messages", "Error: {{error|escapejs}}");
  grr.publish("grr_traceback", "Error: {{backtrace|escapejs}}");
</script>
""")

  def __init__(self, message_template=None, status_code=503):
    super(ErrorHandler, self).__init__()
    self.status_code = status_code
    if message_template is not None:
      self.message_template = message_template

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except Exception as e:  # pylint: disable=W0703
        logging.error(e)
        if not isinstance(self.message_template, Template):
          self.message_template = Template(self.message_template)

        response = self.FormatFromString(self.message_template, error=e,
                                         backtrace=traceback.format_exc())
        response.status_code = 200

        return response

    return Decorated


class TemplateRenderer(Renderer):
  """A simple renderer for fixed templates.

  The parameter 'this' is passed to the template as our reference.
  """

  # These post parameters will be automatically imported into the state.
  post_parameters = []

  # Derived classes should set this template
  layout_template = Template("")

  def Layout(self, request, response, apply_template=None):
    """Render the layout from the template."""
    for parameter in self.post_parameters:
      value = request.REQ.get(parameter)
      if value is not None:
        self.state[parameter] = value

    response = super(TemplateRenderer, self).Layout(request, response)
    if apply_template is None:
      apply_template = self.layout_template

    return self.RenderFromTemplate(apply_template, response,
                                   this=self, id=self.id, unique=self.unique,
                                   renderer=self.__class__.__name__)

  def RawHTML(self, request=None):
    """This returns raw HTML, after sanitization by Layout()."""
    result = http.HttpResponse(mimetype="text/html")
    try:
      self.Layout(request, result)
    except AttributeError:
      # This can happen when a empty protobuf field is rendered
      return ""

    return result.content


class EscapingRenderer(TemplateRenderer):
  """A simple renderer to escape a string."""
  layout_template = Template("{{this.to_escape|escape}}")

  def __init__(self, to_escape):
    self.to_escape = to_escape
    super(EscapingRenderer, self).__init__()


class TableRenderer(TemplateRenderer):
  """A renderer for tables.

  In order to have a table rendered, it is only needed to subclass
  this class in a plugin. Requests to the URL table/classname are then
  handled by this class.
  """

  # We receive change path events from this queue
  event_queue = "tree_select"
  table_options = {}
  message = ""

  def __init__(self):
    # A list of columns
    self.columns = []
    self.column_dict = {}
    # Number of rows
    self.size = 0
    self.message = ""
    # Make a copy of the table options so they can be mutated.
    self.table_options = copy.deepcopy(self.table_options)
    self.table_options["iDisplayLength"] = 50
    self.table_options["aLengthMenu"] = [10, 50, 100, 200, 1000]

    super(TableRenderer, self).__init__()

  def AddColumn(self, column):
    self.columns.append(column)
    self.column_dict[utils.SmartUnicode(column.name)] = column

  def AddRow(self, row_dict, row_index=None):
    """Adds a new row to the table.

    Args:
      row_dict: a dict of values for this row. Keys are column names,
           and values are strings.

      row_index:  If specified we add to this index.
    """
    if row_index is None:
      row_index = self.size

    for k, v in row_dict.iteritems():
      try:
        self.column_dict[k].AddElement(row_index, v)
      except KeyError:
        pass

    row_index += 1
    self.size = max(self.size, row_index)

  def AddRowFromFd(self, index, fd):
    """Adds the row from an AFF4 object."""
    for column in self.columns:
      # This sets AttributeColumns directly from their fd.
      try:
        column.AddRowFromFd(index, fd)
      except AttributeError:
        pass

  def GetCell(self, row_index, column_name):
    """Gets the value of a Cell."""
    if row_index is None:
      row_index = self.size

    try:
      return self.column_dict[column_name].GetElement(row_index)
    except KeyError:
      pass

  def AddCell(self, row_index, column_name, value):
    if row_index is None:
      row_index = self.size

    try:
      self.column_dict[column_name].AddElement(row_index, value)
    except KeyError:
      pass

    self.size = max(self.size, row_index + 1)

  # The following should be safe: {{this.headers}} comes from the column's
  # LayoutHeader().
  layout_template = Template("""
<div class="tableContainer" id="{{unique|escape}}">
<table id="table_{{ id|escape }}" class="scrollTable">
    <thead class="fixedHeader">
<tr> {{ this.headers|safe }} </tr>
    </thead>
    <tbody id="body_{{id|escape}}" class="scrollContent">
      <tr class="even">
        <td id="{{unique|escape}}" colspan="200" class="table_loading">
          Loading...
        </td>
      </tr>
    </tbody>
</table>
</div>
<script>
  grr.table.newTable("{{renderer|escapejs}}", "table_{{id|escapejs}}",
    "{{unique|escapejs}}", {{this.state_json|safe}});

  grr.subscribe("GeometryChange", function (id) {
    if (id == "{{id|escapejs}}") {
      grr.fixHeight($("#table_wrapper_{{unique|escapejs}}"));
      $("#{{id|escapejs}}").find(".TableBody").each(function () {
         grr.fixHeight($(this));
      });
    };
  }, "{{unique|escapejs}}");

  grr.publish("grr_messages", "{{this.message|escapejs}}");
  $("#table_{{id|escapejs}}").attr({{this.state_json|safe}});
</script>
""")

  # Renders the inside of the tbody.
  ajax_template = Template("""
{% for row, row_options in this.rows %}
<tr
 {% for option, value in row_options %}
   {{option|safe}}='{{value|escape}}'
 {% endfor %} >
 {% for cell in row %}
   <td>{{cell|safe}}</td>
 {% endfor %}
</tr>
{% endfor %}
{% if this.additional_rows %}
<tr>
  <td id="{{unique|escape}}" colspan="200" class="table_loading">
    Loading...
  </td>
</tr>
{% endif %}
<script>
  grr.publish("GeometryChange", "main");
  grr.publish("grr_messages", "{{this.message|escapejs}}");
  grr.table.setHeaderWidths($('#{{id}}'));
</script>
""")

  def Layout(self, request, response):
    """Outputs HTML to be compatible with the DataTable interface.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      HTML to insert into the DOM.
    """
    self.table_options = copy.deepcopy(self.table_options)
    self.table_options.setdefault("aoColumnDefs", []).append(
        {"bSortable": False,
         "aTargets": [i for i, c in enumerate(self.columns) if not c.sortable]})

    self.table_options["sTableId"] = GetNextId()

    # Make up the headers by interpolating the column headers
    headers = StringIO.StringIO()
    for i in self.columns:
      opts = ""
      if i.width is not None:
        opts += "header_width='%s' " % i.width

      if i.sortable:
        opts += "sortable=1 "

      # Ask each column to draw itself
      headers.write("<th %s >" % opts)
      i.LayoutHeader(request, headers)
      headers.write("</th>")

    self.headers = headers.getvalue()
    return super(TableRenderer, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table between the start and end rows.

    This should normally be overridden by derived classes.

    Args:
      start_row: The initial row to populate.
      end_row: The final row to populate.
      request: The request object.
    """

  # Do not trigger an error on the browser.
  @ErrorHandler(status_code=200)
  def RenderAjax(self, request, response):
    """Responds to an AJAX request.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      JSON encoded parameters as expected by the javascript widget.
    """
    start_row = int(request.REQ.get("start_row", 0))
    limit_row = int(request.REQ.get("length", 50))

    # The limit_row is merely a suggestion for the BuildTable method, but if
    # the BuildTable method wants to render more we can render more here.
    end_row = self.BuildTable(start_row, limit_row + start_row, request)
    if not end_row: end_row = min(start_row + limit_row, self.size)

    self.rows = []
    for index in xrange(start_row, end_row):
      row_options = {}
      row = []
      for c in self.columns:
        row.append(utils.SmartStr(c.RenderRow(index, request, row_options)))

      self.rows.append((row, row_options.items()))

    self.additional_rows = self.size > end_row

    # If we did not write any additional rows in this round trip we ensure the
    # table does not try to fetch more rows. This is a safety check in case
    # BuildTable does not set the correct size and end row. Without this check
    # the browser will spin trying to fill the table.
    if not self.rows:
      self.additional_rows = False

    return super(TableRenderer, self).Layout(request, response,
                                             apply_template=self.ajax_template)

  def Download(self, request, _):
    """Export the table in CSV.

    This streams the entire table (after suitable filtering).

    Args:
      request: The request object.

    Returns:
       A streaming response object.
    """
    self.BuildTable(0, MAX_ROW_LIMIT, request)

    def RemoveTags(string):
      """Very simple for now - remove any html from output."""
      return re.sub("(?ims)<[^>]+>", "", utils.SmartStr(string)).strip()

    def Generator():
      """Generates the CSV for streaming."""
      fd = StringIO.StringIO()
      writer = csv.writer(fd)

      # Write the headers
      writer.writerow([c.name for c in self.columns])

      # Send 1000 rows at a time
      for i in range(0, self.size):
        if i % 1000 == 0:
          # Flush the buffer
          yield fd.getvalue()
          fd.truncate(0)

        writer.writerow(
            [RemoveTags(c.RenderRow(i, request)) for c in self.columns])

      # The last chunk
      yield fd.getvalue()

    response = http.HttpResponse(content=Generator(),
                                 mimetype="binary/x-csv")

    # This must be a string.
    response["Content-Disposition"] = ("attachment; filename=table.csv")

    return response


class TreeRenderer(TemplateRenderer):
  """An abstract Renderer to support a navigation tree."""

  publish_select_queue = "tree_select"

  layout_template = Template("""
<script>
grr.grrTree("{{ renderer|escapejs }}", "{{ id|escapejs }}",
            "{{ this.publish_select_queue|escapejs }}",
            {{ this.state_json|safe }});
</script>""")

  def Layout(self, request, response):
    return super(TreeRenderer, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Render the tree leafs for the tree path."""
    response = super(TreeRenderer, self).RenderAjax(request, response)
    self.message = ""
    result = []
    self._elements = []
    self._element_index = set()

    path = request.REQ.get("path", "")

    # All derived classes to populate the branch
    self.RenderBranch(path, request)
    for name, icon, behaviour in self._elements:
      if name:
        fullpath = os.path.join(path, name)
        data = dict(data=dict(title=name, icon=icon),
                    attr=dict(id=DeriveIDFromPath(fullpath),
                              path=fullpath))
        if behaviour == "branch":
          data["state"] = "closed"

        result.append(data)

    # If this is a completely empty tree we have to return at least something
    # or the tree will load forever.
    if not result and path == "/":
      result.append(dict(data=dict(title=path, icon="branch"),
                         attr=dict(id=DeriveIDFromPath(path),
                                   path=path)))

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(dict(
        data=result, message=self.message, id=self.id)),
                             mimetype="text/json")

  def AddElement(self, name, behaviour="branch", icon=None):
    """This should be called by the RenderBranch method to prepare the tree."""
    if icon is None:
      icon = behaviour

    self._elements.append((name, icon, behaviour))
    self._element_index.add(name)

  def __contains__(self, other):
    return other in self._element_index

  def RenderBranch(self, path, request):
    """A generator of branch elements.

    Should be overridden by derived classes. This method is called once to
    render the branch. It is expected to call AddElement() repeatadly to build
    the tree.

    Args:
      path: The path to list in the tree.
      request: The request object.
    """


class TabLayout(TemplateRenderer):
  """This renderer creates a set of tabs containing other renderers."""
  # The hash component that will be used to remember which tab we have open.
  # If set to None, currently selected tab name won't be preserved.
  tab_hash = "tab"

  # The name of the delegated renderer that will be used by default (None is the
  # first one).
  selected = None

  names = []
  delegated_renderers = []

  # Note that we do not use jquery-ui tabs here because there is no way to hook
  # a post rendering function so we can resize the canvas. We implement our own
  # tabs here from scratch.
  layout_template = Template("""
<div class="ui-tabs ui-widget ui-widget-content ui-corner-all">
<ul id="{{unique|escape}}" class="ui-tabs-nav ui-helper-reset ui-helper-clearfix
  ui-widget-header ui-corner-all">
 {% for child, name in this.indexes %}
  <li class="ui-state-default ui-corner-top">
   <a id="{{name|escape}}" renderer="{{ child|escape }}">
   <span>{{ name|escape }}</span></a>
  </li>
 {% endfor %}
</ul>
<div id="tab_contents_{{unique|escape}}" class="ui-tabs-panel
   ui-widget-content ui-corner-bottom">
</div>
</div>
<script>
  // Store the state of this widget.
  $("#{{unique|escapejs}}").data().state = {{this.state_json|safe}};

  // Add click handlers to switch tabs.
  $("#{{unique|escapejs}} li a").click(function () {
    if($(this).hasClass("ui-state-disabled")) return false;

    var renderer = this.attributes["renderer"].value;

    {% if this.tab_hash %}
      grr.publish("hash_state", "{{this.tab_hash|escapejs}}", renderer);
    {% endif %}

    // Make a new div to accept the content of the tab rather than drawing
    // directly on the content area. This prevents spurious drawings due to
    // latent ajax calls.
    content_area = $("#tab_contents_{{unique|escapejs}}");
    content_area.html('<div id="' + renderer + '_{{unique|escapejs}}">')
    update_area = $("#" + renderer + "_{{unique|escapejs}}");

    // Ensure that new div's dimensions are explicitly set to match content's
    // dimensions. Otherwise we can get weird bugs if dimensions of the content
    // areas of different tabs are different.
    update_area.width(content_area.width());
    update_area.height(content_area.height());

    // We append the state of this widget which is stored on the unique element.
    grr.layout(renderer, renderer + "_{{unique|escapejs}}",
       $("#{{unique|escapejs}}").data().state, function () {
        grr.publish("GeometryChange", "{{id|escapejs}}");
       });

    // Clear previously selected tab.
    $("#{{unique|escapejs}}").find("li").removeClass(
       "ui-tabs-selected ui-state-active");

    // Select the new one.
    $(this).parent().addClass("ui-tabs-selected ui-state-active");
  });

  //Fix up the height of the tab container when our height changes.
  grr.subscribe("GeometryChange", function (id) {
    if(id == "{{id|escapejs}}") {
      grr.fixHeight($("#tab_contents_{{unique|escapejs}}"));
      grr.fixHeight($("#tab_contents_{{unique|escapejs}} > div"));

      // Propagate the signal along.
      $("#tab_contents_{{unique|escapejs}} > div").each(function () {
         var id = this.attributes["id"].value;
         grr.publish("GeometryChange", id);
      });
    };
   }, "tab_contents_{{unique|escapejs}}");

  // Select the first tab at first.
  {% if this.tab_hash %}
    var selected = grr.hash.{{this.tab_hash|safe}} ||
      "{{this.selected|escapejs}}";
  {% else %}
    var selected = "{{this.selected|escapejs}}";
  {% endif %}
  // Check that tab exists and fall back to default if not.
  if (! $("#{{unique|escapejs}} li a[renderer='" + selected + "']")) {
    selected = "{{this.selected|escapejs}}";
  }
  $($("#{{unique|escapejs}} li a[renderer='" + selected + "']")).click();
</script>

""")

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    if not self.selected:
      self.selected = self.delegated_renderers[0]

    self.indexes = [(self.delegated_renderers[i], self.names[i])
                    for i in range(len(self.names))]

    return super(TabLayout, self).Layout(request, response)


class Splitter(TemplateRenderer):
  """A renderer to achieve a three paned view with a splitter.

  There is a left pane dividing the screen into half horizontally, and
  top and bottom panes dividing the right pane into two.

  This should be subclassed and the below renderers should be
  provided:

  left_renderer will show on the left.
  top_right_renderer will show on the top right.
  bottom_right_renderer will show on the bottom right.

  """

  # Override with the names of the renderers to use in the
  # constructor.
  left_renderer = ""
  top_right_renderer = ""
  bottom_right_renderer = ""

  # Override to change minimum allowed width of the left pane.
  min_left_pane_width = 0

  # This ensures that many Splitters can be placed in the same page by
  # making ids unique.
  layout_template = Template("""
      <div id="{{id|escape}}_leftPane" class="leftPane"></div>
      <div id="{{id|escape}}_rightPane" class="rightPane">
        <div id="{{ id|escape }}_rightSplitterContainer"
         class="rightSplitterContainer">
          <div id="{{id|escape}}_rightTopPane"
           class="rightTopPane"></div>
          <div id="{{id|escape}}_rightBottomPane"
           class="rightBottomPane"></div>
        </div>
      </div>
<script>
      $("#{{ id|escapejs }}")
          .splitter({
              minAsize: {{ this.min_left_pane_width }},
              maxAsize: 3000,
              splitVertical: true,
              A: $('#{{id|escapejs}}_leftPane'),
              B: $('#{{id|escapejs}}_rightPane'),
              animSpeed: 50,
              closeableto: 0})
          .bind("resize", function (event) {
            grr.publish("GeometryChange", "{{id|escapejs}}_leftPane");
            event.stopPropagation();
           });

      $("#{{id|escapejs}}_rightSplitterContainer")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_rightTopPane'),
              B: $('#{{id|escapejs}}_rightBottomPane'),
              animSpeed: 50,
              closeableto: 100})
          .bind("resize", function (event) {
            grr.publish("GeometryChange", "{{id|escapejs}}_rightTopPane");
            grr.publish("GeometryChange", "{{id|escapejs}}_rightBottomPane");
            event.stopPropagation();
           });

// Pass our state to our children.
var state = $.extend({}, grr.state, {{this.state_json|safe}});

grr.layout("{{this.left_renderer|escapejs}}", "{{id|escapejs}}_leftPane",
           state);
grr.layout("{{ this.top_right_renderer|escapejs }}",
           "{{id|escapejs}}_rightTopPane", state);
grr.layout("{{ this.bottom_right_renderer|escapejs }}",
           "{{id|escapejs}}_rightBottomPane", state);

// Propagate geometry change events to all our subpanes.
grr.subscribe("GeometryChange", function(id) {
  if (id == "{{id|escapejs}}") {
    grr.publish("GeometryChange", '{{id|escapejs}}_rightBottomPane');
    grr.publish("GeometryChange", '{{id|escapejs}}_rightTopPane');
    grr.publish("GeometryChange", '{{id|escapejs}}_leftPane');
  };
}, "{{id|escapejs}}_leftPane");

</script>
""")


class Splitter2Way(TemplateRenderer):
  """A two way top/bottom Splitter."""
  top_renderer = ""
  bottom_renderer = ""

  layout_template = Template("""
      <div id="{{id|escape}}_topPane" class="rightTopPane"></div>
      <div id="{{id|escape}}_bottomPane" class="rightBottomPane"></div>
<script>
      $("#{{id|escapejs}}")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_topPane'),
              B: $('#{{id|escapejs}}_bottomPane'),
              animSpeed: 50,
              closeableto: 100})
          .bind("resize", function (event) {
            grr.log("splitter resize event");
            grr.publish("GeometryChange", "{{id|escapejs}}_topPane");
            grr.publish("GeometryChange", "{{id|escapejs}}_bottomPane");
            event.stopPropagation();
          });

var state = $.extend({}, grr.state, {{this.state_json|safe}});

grr.layout("{{this.top_renderer|escapejs }}", "{{id|escapejs}}_topPane",
           state);
grr.layout("{{this.bottom_renderer|escapejs }}", "{{id|escapejs}}_bottomPane",
           state);

</script>
""")


class Splitter2WayVertical(TemplateRenderer):
  """A two way left/right Splitter."""
  left_renderer = ""
  right_renderer = ""

  layout_template = Template("""
      <div id="{{unique|escape}}_leftPane" class="leftPane"></div>
      <div id="{{unique|escape}}_rightPane" class="rightPane"></div>
<script>
      $("#{{id|escapejs}}")
          .splitter({
              minAsize: 0,
              maxAsize: 3000,
              splitVertical: true,
              A: $('#{{unique|escapejs}}_leftPane'),
              B: $('#{{unique|escapejs}}_rightPane'),
              animSpeed: 50,
              closeableto: 0})
          .bind("resize", function (event) {
            grr.publish("GeometryChange", "{{unique|escapejs}}_leftPane");
            grr.publish("GeometryChange", "{{unique|escapejs}}_rightPane");
            event.stopPropagation();
           });

grr.layout("{{ this.left_renderer|escapejs }}",
           "{{unique|escapejs}}_leftPane");
grr.layout("{{ this.right_renderer|escapejs }}",
           "{{unique|escapejs}}_rightPane");

grr.subscribe("GeometryChange", function (id) {
  if (id == "{{id|escapejs}}") {
    grr.fixWidth($("#{{unique|escapejs}}_leftPane"));
    grr.fixWidth($("#{{unique|escapejs}}_rightPane"));
  };
}, "{{unique|escapejs}}_leftPane");


</script>
""")


class TextInput(Renderer):
  """A Renderer to produce a text input field.

  The renderer will publish keystrokes to the publish_queue.
  """
  # The descriptive text
  text = ""
  name = ""
  publish_queue = ""

  template = Template("""
<div class="GrrSearch">
{{ text|escape }}<br>
<input type="text" name="{{this.name|escape}}"
  id="{{unique|escape}}"></input></div>
<script>
   grr.installEventsForText("{{unique|escapejs}}",
                            "{{this.publish_queue|escapejs}}");
</script>
""")


class Button(TemplateRenderer):
  """A Renderer for a button."""
  text = "A button"

  template = Template("""
<button id="{{ unique|escape }}_button">{{ this.text|escape }}</button>
<script>
 $('#{{ unique|escape }}_button').button()
</script>
""")


def GetNextId():
  """Generate a unique id."""
  global COUNTER  # pylint: disable=W0603
  COUNTER += 1  # pylint: disable=C6409
  return COUNTER


class RDFValueRenderer(TemplateRenderer):
  """These are abstract classes for rendering RDFValues."""

  # This specifies the name of the RDFValue object we will render.
  classname = ""

  layout_template = Template("""
{{this.proxy|escape}}
""")

  def __init__(self, proxy):
    """Constructor.

    This class renders a specific AFF4 object which we delegate.

    Args:
      proxy: The RDFValue class we delegate.
    """
    self.proxy = proxy
    super(RDFValueRenderer, self).__init__()

  @classmethod
  def RendererForRDFValue(cls, rdfvalue_cls_name):
    """Returns the class of the RDFValueRenderer which renders rdfvalue_cls."""
    for candidate in cls.classes.values():
      if (issubclass(candidate, RDFValueRenderer) and
          candidate.classname == rdfvalue_cls_name):
        return candidate


class SubjectRenderer(RDFValueRenderer):
  """A special renderer for Subject columns."""
  classname = "Subject"

  layout_template = Template("""
<span type=subject aff4_path='{{this.aff4_path|escape}}'>
  {{this.basename|escape}}
</span>
""")

  def Layout(self, request, response):
    aff4_path = aff4.RDFURN(request.REQ.get("aff4_path", ""))
    self.basename = self.proxy.RelativeName(aff4_path)
    self.aff4_path = self.proxy

    return super(SubjectRenderer, self).Layout(request, response)


class RDFProtoRenderer(RDFValueRenderer):
  """Nicely render protobuf based RDFValues.

  Its possible to override specific fields in the protobuf by providing a method
  like:

  translate_method_name(self, value)

  which is expected to return a safe html unicode object reflecting the value in
  the value field.
  """
  name = ""

  # The field which holds the protobuf
  proxy_field = "data"

  # {{value}} comes from the translator so its assumed to be safe.
  layout_template = Template("""
<table class='proto_table'>
<tbody>
{% for key, value in this.result %}
<tr>
<td class="proto_key">{{key|escape}}</td><td class="proto_value">
{{value|safe}}
</td>
</tr>
{% endfor %}
</tbody>
</table>
""")

  # This is a translation dispatcher for rendering special fields.
  translator = {}

  translator_error_template = Template("<pre>{{value|escape}}</pre>")

  def Ignore(self, unused_descriptor, unused_value):
    """A handler for ignoring a value."""
    return None

  time_template = Template("{{value|escape}}")

  def Time(self, _, value):
    return self.FormatFromTemplate(self.time_template,
                                   value=aff4.RDFDatetime(value))

  def Time32Bit(self, _, value):
    return self.FormatFromTemplate(self.time_template,
                                   value=aff4.RDFDatetime(value*1000000))

  hrb_template = Template("{{value|filesizeformat}}")

  def HumanReadableBytes(self, _, value):
    """Format byte values using human readable units."""
    return self.FormatFromTemplate(self.hrb_template, value=value)

  pre_template = Template("<pre>{{value|escape}}</pre>")

  def Pre(self, _, value):
    return self.FormatFromTemplate(self.pre_template, value=value)

  def Enum(self, descriptor, value):
    try:
      return descriptor.enum_type.values_by_number[value].name
    except (AttributeError, KeyError):
      return value

  def ProtoDict(self, _, protodict):
    """Render a ProtoDict as a string of values."""
    protodict = utils.ProtoDict(protodict)
    return self.FormatFromTemplate(self.proto_template,
                                   data=protodict.ToDict().items())

  def RDFProtoRenderer(self, _, value, proto_renderer_name=None):
    """Render a field using another RDFProtoRenderer."""
    renderer_cls = self.classes[proto_renderer_name]
    rdf_value = aff4.RDFProto.classes[renderer_cls.classname](value)
    return renderer_cls(rdf_value).RawHTML()

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.result = []

    for descriptor, value in getattr(self.proxy, self.proxy_field).ListFields():
      # Try to translate the value
      name = descriptor.name
      try:
        value = self.translator[name](self, descriptor, value)

        # If the translation fails for whatever reason, just output the string
        # value literally (after escaping)
      except KeyError:
        value = self.FormatFromTemplate(self.translator_error_template,
                                        value=value)
      except Exception as e:
        logging.warn("Failed to render {0}. Err: {1}".format(name, e))
        value = ""

      if value:
        self.result.append((name, value))

    return super(RDFProtoRenderer, self).Layout(request, response)


class RDFProtoArrayRenderer(RDFProtoRenderer):
  """Renders arrays of protobufs."""

  # {{value}} comes from the translator so its assumed to be safe.
  proto_template = Template("""
<table class='proto_table'>
<tbody>
{% for proto_table in data %}
<tr class="proto_separator"></tr>
  {% for key, value in proto_table %}
    <tr>
      <td class="proto_key">{{key|escape}}</td><td class="proto_value">
        {{value|safe}}
      </td>
    </tr>
  {% endfor %}
{% endfor %}
</tbody>
</table>
""")

  def Layout(self, _, response):
    """Render the protobuf as a table."""
    result = []

    for proto in getattr(self.proxy, self.proxy_field):
      proto_table = []
      for descriptor, value in proto.ListFields():
        # Try to translate the value
        name = descriptor.name
        try:
          value = self.translator[name](self, descriptor, value)

          # If the translation fails for whatever reason, just output the string
          # value literally (after escaping)
        except KeyError:
          value = self.FormatFromTemplate(self.translator_error_template,
                                          value=value)
        except Exception as e:
          logging.warn("Failed to render {0}. Err: {1}".format(name, e))

        if value:
          proto_table.append((name, value))

      result.append(proto_table)

    return self.RenderFromTemplate(self.proto_template, response, data=result)


class AbstractLogRenderer(TemplateRenderer):
  """Render a page for view a Log file.

  Implements a very simple view. That will be extended with filtering
  capabilities.

  Implementations should implement the GetLog function.
  """

  layout_template = Template("""
<table class="proto_table">
{% for line in this.log %}
  <tr>
  {% for val in line %}
    <td class="proto_key">{{ val|escape }}</td>
  {% endfor %}
  </tr>
{% empty %}
<tr><td>No entries</tr></td>
{% endfor %}
<table>
""")

  def GetLog(self, request):
    """Take a request and return a list of tuples for a log."""

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    self.log = self.GetLog(request)
    return super(AbstractLogRenderer, self).Layout(request, response)


class IconRenderer(RDFValueRenderer):
  width = 0
  layout_template = Template("""
<img class='grr-icon' src='/static/images/{{this.proxy.icon}}.png'
 alt='{{this.proxy.description}}' title='{{this.proxy.description}}'
 />""")


def DeriveIDFromPath(path):
  """Transforms path into something that can be used as a HTML DOM ID.

  This transformation never needs to be reversed so it needs the following
  properties:
  - A filename must always have a unique DOM id.
  - The dom id should be similar to the filename for simple ASCII filenames.
  - Invalid characters in DOM Ids should be transformed to valid ones.

  Args:
    path: A fully qualified path.

  Returns:
    A string suitable for including in a DOM id.
  """
  # This regex selects invalid characters
  invalid_chars = re.compile("[^a-zA-Z0-9]")

  components = path.split("/")
  return "_" + "-".join(
      [invalid_chars.sub(lambda x: "_%02X" % ord(x.group(0)), x)
       for x in components if x])


class ErrorRenderer(TemplateRenderer):
  """Render Exceptions."""
  layout_template = Template("""
<script>
  grr.publish("messages", "{{this.value|escapejs}}");
</script>
""")

  def Layout(self, request, response):
    self.value = request.REQ.get("value", "")
    return super(ErrorRenderer, self).Layout(request, response)


class EmptyRenderer(Renderer):
  """A do nothing renderer."""

  def Format(self, **_):
    return ""


class UnauthorizedRenderer(TemplateRenderer):
  """Send UnauthorizedAccess Exceptions to the queue."""

  layout_template = Template("""
<script>
  grr.publish("unauthorized", "{{this.client_id|escapejs}}",
              "{{this.message|escapejs}}");
</script>
""")

  def Layout(self, request, response):
    exception = request.REQ.get("e", "")
    if exception:
      self.client_id = exception.subject
      self.message = str(exception)

    return super(UnauthorizedRenderer, self).Layout(request, response)


class FormElementRenderer(TemplateRenderer):
  """Base class for renderers for basic form elements."""

  form_template = Template("")

  def Format(self, **kwargs):
    return self.FormatFromTemplate(self.form_template, **kwargs)


class StringFormRenderer(FormElementRenderer):
  form_template = Template("""
<td>{{desc|escape}}</td>
<td><input {% if arg_type.AllowNone %}class="form_field_or_none"{% endif %}
name='{{ field|escape }}' type=text value='{{ value|escape }}'/></td>
""")


class EncryptionKeyFormRenderer(FormElementRenderer):
  """Renders an encryption key."""

  # Length of this key in bits.
  bits = 128

  form_template = Template("""
<td>{{desc|escape}}</td>
<td><input {% if arg_type.AllowNone %}class="form_field_or_none"{% endif %}
name='{{ field|escape }}' type=text value='{{ value|escape }}'
size='{{field_size|escape}}' max_size='{{field_size|escape}}'/></td>
""")

  def Format(self, **kwargs):
    key = BN.rand(self.bits)
    kwargs["value"] = utils.FormatAsHexString(key, width=self.bits/4, prefix="")
    kwargs["field_size"] = (self.bits/4) + 2
    return self.FormatFromTemplate(self.form_template, **kwargs)


class BoolFormRenderer(FormElementRenderer):
  form_template = Template("""
<td>{{desc|escape}}</td>
<td><input name='{{ field|escape }}' type=checkbox
    {% if value %}checked {% endif %} value='{{ value|escape }}'/></td>
""")


class ProtoEnumFormRenderer(FormElementRenderer):
  """Renders protobuf enums."""

  form_template = Template("""
<td>{{desc|escape}}</td><td><select name="{{field|escape}}">
{% for enum_name, enum_desc in enum_values %}
 <option {% ifequal enum_desc.number value %}selected{% endifequal %}
   value="{{enum_desc.number|escape}}">
   {{enum_name|escape}}
   {% ifequal enum_desc.number default %} (default){% endifequal %}
</option>
{% endfor %}
</select></td>
""")

  def Format(self, arg_type, **kwargs):
    # We want enums to be sorted by their numerical value.
    enum_values = sorted(
        arg_type.enum_descriptor.values_by_name.items(),
        key=lambda (k, v): v)
    return self.FormatFromTemplate(self.form_template, enum_values=enum_values,
                                   **kwargs)


class ArtifactListRenderer(FormElementRenderer):
  """Renders an Artifact selector."""

  form_template = Template("""
<tr><td><hr/></td></tr>
{% for name, cls in artifact_list %}
  {% if name in default %}
    <tr>
      <td>Collect {{name|escape}}</td>
      <td><input name='{{ desc|escape }}' type='checkbox'
          checked value='{{ name|escape }}'/></td>
      <td>{{ cls.GetDescription|escape }}</td>
    </tr>
  {% endif %}
{% endfor %}

<tr><td><hr/></td></tr>
""")

  def Format(self, arg_type, **kwargs):
    _ = arg_type
    artifacts_list = []
    for key, val in artifact.Artifact.classes.items():
      if key != "Artifact":
        artifacts_list.append((key, val))
    return self.FormatFromTemplate(
        self.form_template, artifact_list=artifacts_list, **kwargs)


class UserListRenderer(FormElementRenderer):
  """Renders a User selector."""

  form_template = Template("""
<tr><td>{{desc|escape}}</td><td>
<select id="user_select_{{unique|escape}}" name="{{field|escape}}"
  multiple="multiple">
{% for user in valid_users %}
  <option value="{{user.username|escape}}">{{user.username|escape}}
  {% if user.domain %} ({{user.domain|escape}}){% endif %}
  </option>
{% endfor %}
</select>
</td></tr>
<script>
  $("#user_select_{{unique|escapejs}}").multiselect({
    header: "Select users",
    noneSelectedText: "Select users"});
</script>
""")

  def Format(self, arg_type, **kwargs):
    _ = arg_type
    client = kwargs.get("client")
    if client:
      valid_users = list(client.Get(client.Schema.USER, []))
    else:
      valid_users = []

    return self.FormatFromTemplate(
        self.form_template, valid_users=valid_users, **kwargs)


def FindRendererForObject(rdf_obj):
  """Find the appropriate renderer for an RDFValue object."""
  for cls in RDFValueRenderer.classes.values():
    try:
      if cls.classname == rdf_obj.__class__.__name__:
        return cls(rdf_obj)
    except AttributeError:
      pass

  # Default renderer.
  return RDFValueRenderer(rdf_obj)


class WizardPage(object):
  """Configuration object used to configure WizardRenderer."""

  def __init__(self, name=None, description=None, renderer=None,
               next_button_label="Next", show_back_button=True,
               wait_for_event=None):
    """Constructor.

    Args:
      name: unique name for a given page.
      description: description that will be shown in the wizard's
                   "current step" bar. Default is None.
      renderer: renderer used to render given page.
      next_button_label: label for the "next" button for the current
                         page. Default is "Next".
      show_back_button: whether to show back button on current page. Default
                        is True.
      wait_for_event: wait for given event in the "WizardProceed" queue before
                      enabling "Next" button. Default is False.

    Raises:
      RuntimeError: if name or renderer is None
    """

    if name is None:
      raise RuntimeError("Name is not specified for WizardPage")
    self.name = name

    self.description = description

    if renderer is None:
      raise RuntimeError("Renderer is not specified for WizardPage")
    self.renderer = renderer

    self.next_button_label = next_button_label
    self.show_back_button = show_back_button
    self.wait_for_event = wait_for_event


class WizardRenderer(TemplateRenderer):
  """This renderer creates a wizard."""
  # The name of the delegated renderer that will be used by default (None is the
  # first one).
  selected = None

  # WizardPage objects that defined this wizard's behaviour.
  pages = []

  # This will be used for identifying the wizard when publishing the events.
  wizard_name = "wizard"

  layout_template = Template("""
<div id="Wizard_{{unique|escape}}"
     class="Wizard"
     style="width: 100%; height: 100%; padding-top: 40px">
  <div class="WizardBar"
       style="width: 100%; position: relative; top: -40px; height: 40px">

    <input type="button" value="Back" class="Back" style="visibility: hidden"/>
    <span class="Description"></span>
    <input type="button" value="Next" class="Next" />

  </div>
  <div id="WizardContent_{{unique|escape}}"
       style="width: 100%; height: 100%; position: relative; top: -40px">
  </div>
</div>

<script>
(function() {

var stateJson = {{this.state_json|safe}};
var wizardPages = stateJson.pages;
var selectedWizardTab = 0;

$("#Wizard_{{unique|escapejs}} .WizardBar .Back").button().click(function() {
  selectTab(selectedWizardTab - 1);
});

$("#Wizard_{{unique|escapejs}} .WizardBar .Next").button().click(function() {
  if (selectedWizardTab + 1 < wizardPages.length) {
    selectTab(selectedWizardTab + 1);
  } else {
    grr.publish("WizardComplete", "{{this.wizard_name|escapejs}}");
  }
});

function selectTab(index) {
  selectedWizardTab = index;
  $("#Wizard_{{unique|escapejs}} .WizardBar .Description").text(
    wizardPages[index].description);

  var wizardStateJson = JSON.stringify(
    $("#Wizard_{{unique|escapejs}}").data());
  grr.layout(wizardPages[index].renderer, "WizardContent_{{unique|escapejs}}",
    { "{{this.wizard_name|escapejs}}": wizardStateJson });

  $("#Wizard_{{unique|escapejs}} .WizardBar .Back").css("visibility",
    index > 0 && wizardPages[index].show_back_button ? "visible" : "hidden");

  var nextButton = $("#Wizard_{{unique|escapejs}} .WizardBar .Next");
  nextButton.button("option", "label", wizardPages[index].next_button_label);

  var eventToWait = wizardPages[index].wait_for_event;
  if (eventToWait) {
    nextButton.button({ disabled: true });
    grr.subscribe("WizardProceed", function(id) {
      if (id == eventToWait) {
        nextButton.button({ disabled: false });
      }
    }, "Wizard_{{unique|escapejs}}");
  } else {
    nextButton.button({ disabled: false });
  }
}

$("#Wizard_{{unique|escapejs}}").data({});
selectTab(0);

})();
</script>
""")

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    # Passing JSON-serializable wizard configuration (array of pages)
    # to the renderer's client side.
    self.state["pages"] = [page.__dict__ for page in self.pages]
    return super(WizardRenderer, self).Layout(request, response)
