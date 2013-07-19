#!/usr/bin/env python
"""This module contains base classes for different kind of renderers."""


import copy
import csv
import functools
import itertools
import json
import os
import re
import StringIO
import traceback
import urllib


from django import http
from django import template
from django.core import context_processors

from M2Crypto import BN

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr

# Global counter for ids
COUNTER = 1

# Maximum size of tables that can be downloaded
MAX_ROW_LIMIT = 1000000


def GetNextId():
  """Generate a unique id."""
  global COUNTER  # pylint: disable=global-statement
  COUNTER += 1  # pylint: disable=g-bad-name
  return COUNTER


class VerifyRenderers(registry.InitHook):

  def RunOnce(self):
    renderers = {}

    for candidate in RDFValueRenderer.classes.values():
      if aff4.issubclass(candidate, RDFValueRenderer) and candidate.classname:
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
    value = self.rows.get(index)
    if value is None:
      return ""

    if row_options is not None:
      row_options["row_id"] = index

    if self.renderer:
      renderer = self.renderer(value)
    else:
      renderer = FindRendererForObject(value)

    # Intantiate the renderer and return the HTML
    if renderer:
      result = renderer.RawHTML(request)
    else:
      result = utils.SmartStr(value)

    return result


class AttributeColumn(RDFValueColumn):
  """A table column which can be filled from an AFF4Object."""

  def __init__(self, name, **kwargs):
    # Locate the attribute
    self.attribute = aff4.Attribute.GetAttributeByName(name)

    RDFValueColumn.__init__(self, name, **kwargs)

  def AddRowFromFd(self, index, fd):
    """Add a new value from the fd."""
    value = fd.Get(self.attribute)
    try:
      # Unpack flows that are stored inside tasks.
      value = value.Payload()
    except AttributeError:
      pass
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

  js_call_template = Template("""
<script>
  grr.ExecuteRenderer("{{method|escapejs}}", {{js_state_json|safe}});
</script>
""")

  def __init__(self, id=None, state=None):  # pylint: disable=redefined-builtin
    self.state = state or {}
    self.id = id
    self.unique = GetNextId()

  def CallJavascript(self, response, method, **kwargs):
    """Inserts javascript call into the response.

    Args:
      response: Response object where the <script>...</script> code will be
                written.
      method: Javascript method to be executed. For example,
              "SomeRenderer.Layout". For details on how to register these
              methods, please see gui/static/javascript/renderers.js.
      **kwargs: Dictionary arguments that will be passed to the javascript
                functions in JSON-encoded 'state' argument. self.unique
                and self.id are included into 'state' by default.

    Returns:
      Response object.
    """
    js_state = {"unique": self.unique,
                "id": self.id}
    js_state.update(kwargs)

    self.RenderFromTemplate(self.js_call_template, response,
                            method=method,
                            js_state_json=json.dumps(js_state))
    return response

  def RenderAjax(self, request, response):
    """Responds to an AJAX request.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      JSON encoded parameters as expected by the javascript widget.
    """
    if request and self.id is None:
      self.id = request.REQ.get("id", hash(self))

    return response

  def Layout(self, request, response):
    """Outputs HTML to be inserted into the DOM in order to layout this widget.

    Args:
      request: The request object.
      response: A HttpResponse object which can be filled in.

    Returns:
      HTML to insert into the DOM.
    """
    if request and self.id is None:
      self.id = request.REQ.get("id", hash(self))

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
    kwargs["this"] = self
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
      access_control.UnauthorizedAccess if the user is not permitted.
    """


class UserLabelCheckMixin(object):
  """Checks the user has a label or deny access to this renderer."""

  # This should be overridden in the mixed class.
  AUTHORIZED_LABELS = []

  @classmethod
  def CheckAccess(cls, request):
    """If the user is not in the AUTHORIZED_LABELS, reject this renderer."""
    if data_store.DB.security_manager.CheckUserLabels(
        request.token.username, cls.AUTHORIZED_LABELS):
      return
    raise access_control.UnauthorizedAccess("User %s not allowed." %
                                            request.token.username)


class ErrorHandler(Renderer):
  """An error handler decorator which can be applied on individual methods."""

  message_template = Template("""
<script>
  grr.publish("grr_messages", "Error: {{error|escapejs}}");
  grr.publish("grr_traceback", "Error: {{backtrace|escapejs}}");
</script>
""")

  def __init__(self, message_template=None, status_code=503, **kwargs):
    super(ErrorHandler, self).__init__(**kwargs)
    self.status_code = status_code
    if message_template is not None:
      self.message_template = message_template

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(utils.SmartUnicode(e))
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

    csrf_token = context_processors.csrf(request)

    return self.RenderFromTemplate(apply_template, response,
                                   this=self, id=self.id, unique=self.unique,
                                   renderer=self.__class__.__name__,
                                   **csrf_token)

  def RawHTML(self, request=None, **kwargs):
    """This returns raw HTML, after sanitization by Layout()."""
    result = http.HttpResponse(mimetype="text/html")
    self.Layout(request, result, **kwargs)
    return result.content


class EscapingRenderer(TemplateRenderer):
  """A simple renderer to escape a string."""
  layout_template = Template("{{this.to_escape|escape}}")

  def __init__(self, to_escape, **kwargs):
    self.to_escape = to_escape
    super(EscapingRenderer, self).__init__(**kwargs)


class TableRenderer(TemplateRenderer):
  """A renderer for tables.

  In order to have a table rendered, it is only needed to subclass
  this class in a plugin. Requests to the URL table/classname are then
  handled by this class.
  """

  fixed_columns = False
  custom_class = ""

  # We receive change path events from this queue
  event_queue = "tree_select"
  table_options = {}
  message = ""

  def __init__(self, **kwargs):
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

    super(TableRenderer, self).__init__(**kwargs)

  def AddColumn(self, column):
    self.columns.append(column)
    self.column_dict[utils.SmartUnicode(column.name)] = column

  def AddRow(self, row_dict=None, row_index=None, **kwargs):
    """Adds a new row to the table.

    Args:
      row_dict: a dict of values for this row. Keys are column names,
           and values are strings.

      row_index:  If specified we add to this index.
    """
    if row_index is None:
      row_index = self.size

    if row_dict is not None:
      kwargs.update(row_dict)

    for k, v in kwargs.iteritems():
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
<div id="{{unique|escape}}">
<table id="table_{{ id|escape }}" class="table table-striped table-condensed
  table-hover table-bordered full-width
  {% if this.fixed_columns %} fixed-columns{% endif %} {{ this.custom_class }}">
  <colgroup>
  {% for column in this.columns %}
    {% if column.width %}
    <col style="width: {{column.width|escape}}" />
    {% else %}
    <col></col>
    {% endif %}
  {% endfor %}
  </colgroup>
    <thead>
<tr> {{ this.headers|safe }} </tr>
    </thead>
    <tbody id="body_{{id|escape}}" class="scrollContent">
          {{this.table_contents|safe}}
    </tbody>
</table>
</div>
<script>
  grr.table.newTable("{{renderer|escapejs}}", "table_{{id|escapejs}}",
    "{{unique|escapejs}}", {{this.state_json|safe}});

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
  var table = $('#{{id}}');

  grr.publish("grr_messages", "{{this.message|escapejs}}");
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

      if i.sortable:
        opts += "sortable=1 "

      # Ask each column to draw itself
      headers.write("<th %s >" % opts)
      i.LayoutHeader(request, headers)
      headers.write("</th>")

    self.headers = headers.getvalue()

    # Populate the table with the initial view.
    tmp = http.HttpResponse(mimetype="text/html")
    delegate_renderer = self.__class__(id=self.id, state=self.state.copy())
    self.table_contents = delegate_renderer.RenderAjax(request, tmp).content

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
          fd.truncate(size=0)

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
<div class="fill-parent">
  <ul id="{{unique|escape}}" class="nav nav-tabs">
    {% for child, name in this.indexes %}
    <li renderer="{{ child|escape }}">
      <a id="{{name|escape}}" renderer="{{ child|escape }}">{{name|escape}}</a>
    </li>
    {% endfor %}
  </ul>
  <div id="tab_contents_{{unique|escape}}" class="tab-content"></div>
</div>

<!-- TODO: rewrite. it's bad to generate JS code in a loop -->
<script>
// Disable the tabs which need to be disabled.
$("li").removeClass("disabled");
$("li a").removeClass("disabled");

{% for disabled in this.disabled %}
$("li[renderer={{disabled|escapejs}}]").addClass("disabled");
$("li a[renderer={{disabled|escapejs}}]").addClass("disabled");
{% endfor %}
</script>
<script>
  // Store the state of this widget.
  $("#{{unique|escapejs}}").data().state = {{this.state_json|safe}};

  // Add click handlers to switch tabs.
  $("#{{unique|escapejs}} li a").click(function (e) {
    e.preventDefault();
    if ($(this).hasClass("disabled")) return false;

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

    // We append the state of this widget which is stored on the unique element.
    grr.layout(renderer, renderer + "_{{unique|escapejs}}",
       $("#{{unique|escapejs}}").data().state);

    // Clear previously selected tab.
    $("#{{unique|escapejs}}").find("li").removeClass("active");

    // Select the new one.
    $(this).parent().addClass("active");
  });

  // Find first enabled tab (the default selection).
  var enabledTabs = $.map(
    $("#{{unique|escapejs}} > li:not(.disabled)"),
    function(val) {
      return $(val).attr("renderer");
    }
  );

  // Select the first tab at first.
  {% if this.tab_hash %}
    var selected = grr.hash.{{this.tab_hash|safe}} ||
      "{{this.selected|escapejs}}";
  {% else %}
    var selected = "{{this.selected|escapejs}}";
  {% endif %}

  if (enabledTabs.indexOf(selected) == -1) {
    selected = enabledTabs.length > 0 ? enabledTabs[0] : null;
  }
  if (selected) {
    $($("#{{unique|escapejs}} li a[renderer='" + selected + "']")).click();
  }
</script>

""")

  def __init__(self, *args, **kwargs):
    super(TabLayout, self).__init__(*args, **kwargs)
    # This can be overriden by child classes.
    self.disabled = []

  def Layout(self, request, response, apply_template=None):
    """Render the content of the tab or the container tabset."""
    if not self.selected:
      self.selected = self.delegated_renderers[0]

    self.indexes = [(self.delegated_renderers[i], self.names[i])
                    for i in range(len(self.names))]

    return super(TabLayout, self).Layout(request, response, apply_template)


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
  max_left_pane_width = 3000

  # This ensures that many Splitters can be placed in the same page by
  # making ids unique.
  layout_template = Template("""
<div id="{{id|escape}}_leftPane" class="leftPane">
  {{this.left_pane|safe}}
</div>
<div id="{{id|escape}}_rightPane" class="rightPane no-overflow">
  <div id="{{ id|escape }}_rightSplitterContainer"
   class="rightSplitterContainer">
    <div id="{{id|escape}}_rightTopPane"
      class="rightTopPane ">
      {{this.top_right_pane|safe}}
    </div>
    <div id="{{id|escape}}_rightBottomPane"
      class="rightBottomPane">
      {{this.bottom_right_pane|safe}}
    </div>
  </div>
</div>
<script>
      $("#{{ id|escapejs }}")
          .splitter({
              minAsize: {{ this.min_left_pane_width }},
              maxAsize: {{ this.max_left_pane_width }},
              splitVertical: true,
              A: $('#{{id|escapejs}}_leftPane'),
              B: $('#{{id|escapejs}}_rightPane'),
              animSpeed: 50,
              closeableto: 0});

      $("#{{id|escapejs}}_rightSplitterContainer")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_rightTopPane'),
              B: $('#{{id|escapejs}}_rightBottomPane'),
              animSpeed: 50,
              closeableto: 100});

      // Triggering resize event here to ensure that splitters will position
      // themselves correctly.
      $("#{{ id|escapejs }}").resize();

// Pass our state to our children.
var state = $.extend({}, grr.state, {{this.state_json|safe}});
</script>
""")

  def Layout(self, request, response):
    """Layout."""
    self.id = request.REQ.get("id", hash(self))

    # Pre-render the top and bottom layout contents to avoid extra round trips.
    self.left_pane = self.classes[self.left_renderer](
        id="%s_leftPane" % self.id).RawHTML(request)

    self.top_right_pane = self.classes[self.top_right_renderer](
        id="%s_rightTopPane" % self.id).RawHTML(request)

    self.bottom_right_pane = self.classes[self.bottom_right_renderer](
        id="%s_rightBottomPane" % self.id).RawHTML(request)

    return super(Splitter, self).Layout(request, response)


class Splitter2Way(TemplateRenderer):
  """A two way top/bottom Splitter."""
  top_renderer = ""
  bottom_renderer = ""

  layout_template = Template("""
<div id="{{id|escape}}_topPane" class="rightTopPane">
  {{this.top_pane|safe}}
</div>
<div id="{{id|escape}}_bottomPane" class="rightBottomPane">
  {{this.bottom_pane|safe}}
</div>
<script>
      $("#{{id|escapejs}}")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_topPane'),
              B: $('#{{id|escapejs}}_bottomPane'),
              animSpeed: 50,
              closeableto: 100});

var state = $.extend({}, grr.state, {{this.state_json|safe}});
</script>
""")

  def Layout(self, request, response):
    """Layout."""
    self.id = self.id or request.REQ.get("id", hash(self))

    # Pre-render the top and bottom layout contents to avoid extra round trips.
    self.top_pane = self.classes[self.top_renderer](
        id="%s_topPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    self.bottom_pane = self.classes[self.bottom_renderer](
        id="%s_bottomPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    return super(Splitter2Way, self).Layout(request, response)


class Splitter2WayVertical(TemplateRenderer):
  """A two way left/right Splitter."""
  left_renderer = ""
  right_renderer = ""

  # Override to change minimum allowed width of the left pane.
  min_left_pane_width = 0
  max_left_pane_width = 3000

  layout_template = Template("""
<div id="{{id|escape}}_leftPane" class="leftPane">
  {{this.left_pane|safe}}
</div>
<div id="{{id|escape}}_rightPane" class="rightPane">
  {{this.right_pane|safe}}
</div>

<script>
      $("#{{id|escapejs}}")
          .splitter({
              minAsize: {{ this.min_left_pane_width }},
              maxAsize: {{ this.max_left_pane_width }},
              splitVertical: true,
              A: $('#{{id|escapejs}}_leftPane'),
              B: $('#{{id|escapejs}}_rightPane'),
              animSpeed: 50,
              closeableto: 0});

</script>
""")

  def Layout(self, request, response):
    """Layout."""
    self.id = request.REQ.get("id", hash(self))

    # Pre-render the top and bottom layout contents to avoid extra round trips.
    self.left_pane = self.classes[self.left_renderer](
        id="%s_leftPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    self.right_pane = self.classes[self.right_renderer](
        id="%s_rightPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    return super(Splitter2WayVertical, self).Layout(request, response)


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


class RDFValueRenderer(TemplateRenderer):
  """These are abstract classes for rendering RDFValues."""

  # This specifies the name of the RDFValue object we will render.
  classname = ""

  layout_template = Template("""
{{this.proxy|escape}}
""")

  def __init__(self, proxy, **kwargs):
    """Constructor.

    This class renders a specific AFF4 object which we delegate.

    Args:
      proxy: The RDFValue class we delegate.
    """
    self.proxy = proxy
    super(RDFValueRenderer, self).__init__(**kwargs)

  @classmethod
  def RendererForRDFValue(cls, rdfvalue_cls_name):
    """Returns the class of the RDFValueRenderer which renders rdfvalue_cls."""
    for candidate in cls.classes.values():
      if (aff4.issubclass(candidate, RDFValueRenderer) and
          candidate.classname == rdfvalue_cls_name):
        return candidate


class ValueRenderer(RDFValueRenderer):
  """A renderer which renders an RDFValue in machine readable format."""

  layout_template = Template("""
<span type='{{this.rdfvalue_type|escape}}' rdfvalue='{{this.value|escape}}'>
  {{this.rendered_value|safe}}
</span>
""")

  def Layout(self, request, response):
    self.rdfvalue_type = self.proxy.__class__.__name__
    try:
      self.value = self.proxy.SerializeToString()
    except AttributeError:
      self.value = utils.SmartStr(self.proxy)

    renderer = FindRendererForObject(self.proxy)
    self.rendered_value = renderer.RawHTML(request)
    return super(ValueRenderer, self).Layout(request, response)


class SubjectRenderer(RDFValueRenderer):
  """A special renderer for Subject columns."""
  classname = "Subject"

  layout_template = Template("""
<span type=subject aff4_path='{{this.aff4_path|escape}}'>
  {{this.basename|escape}}
</span>
""")

  def Layout(self, request, response):
    aff4_path = rdfvalue.RDFURN(request.REQ.get("aff4_path", ""))
    self.basename = self.proxy.RelativeName(aff4_path) or self.proxy
    self.aff4_path = self.proxy

    return super(SubjectRenderer, self).Layout(request, response)


class RDFURNRenderer(RDFValueRenderer):
  """A special renderer for RDFURNs."""

  classname = "RDFURN"

  layout_template = Template("""
{% if this.href %}
<a href='#{{this.href|escape}}'
  onclick='grr.loadFromHash("{{this.href|escape}}");'>
  {{this.proxy|escape}}
</a>
{% else %}
{{this.proxy|escape}}
{% endif %}
""")

  def Layout(self, request, response):
    client, rest = self.proxy.Split(2)
    if aff4_grr.VFSGRRClient.CLIENT_ID_RE.match(client):
      h = dict(main="VirtualFileSystemView",
               c=client,
               tab="AFF4Stats",
               t=DeriveIDFromPath(rest))
      self.href = urllib.urlencode(sorted(h.items()))

    super(RDFURNRenderer, self).Layout(request, response)


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
                                   value=rdfvalue.RDFDatetime(value))

  def Time32Bit(self, _, value):
    return self.FormatFromTemplate(self.time_template,
                                   value=rdfvalue.RDFDatetime(value*1000000))

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
    protodict = rdfvalue.Dict(initializer=protodict)
    return self.FormatFromTemplate(self.proto_template,
                                   data=protodict.ToDict().items())

  def RDFProtoRenderer(self, _, value, proto_renderer_name=None):
    """Render a field using another RDFProtoRenderer."""
    renderer_cls = self.classes[proto_renderer_name]
    rdf_value = aff4.FACTORY.RDFValue(renderer_cls.classname)(value)
    return renderer_cls(rdf_value).RawHTML()

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.result = []
    for descriptor, value in self.proxy.ListFields():
      name = descriptor.name
      # Try to translate the value if there is a special translator for it.
      if name in self.translator:
        try:
          value = self.translator[name](self, None, value)
          if value is not None:
            self.result.append((name, value))

          # If the translation fails for whatever reason, just output the string
          # value literally (after escaping)
        except KeyError:
          value = self.FormatFromTemplate(self.translator_error_template,
                                          value=value)
        except Exception as e:
          logging.warn("Failed to render {0}. Err: {1}".format(name, e))
          value = ""

      else:
        renderer = FindRendererForObject(value)

        self.result.append((name, renderer.RawHTML(request)))

    return super(RDFProtoRenderer, self).Layout(request, response)


class RDFValueArrayRenderer(RDFValueRenderer):
  """Renders arrays of RDFValues."""

  # {{entry}} comes from the individual rdfvalue renderers so it is assumed to
  # be safe.
  layout_template = Template("""
<table class='proto_table'>
<tbody>
{% for entry in this.data %}
<tr class="proto_separator"></tr>
<td>{{entry|safe}}</td>
</tr>
{% endfor %}
</tbody>
</table>
""")

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.data = []

    for element in self.proxy:
      renderer = FindRendererForObject(element)
      if renderer:
        try:
          self.data.append(renderer.RawHTML(request))
        except Exception as e:
          raise RuntimeError(
              "Unable to render %s with %s: %s" % (type(element), renderer, e))

    return super(RDFValueArrayRenderer, self).Layout(request, response)


class DictRenderer(RDFValueRenderer):
  """Renders dicts."""

  classname = "Dict"

  # {{value}} comes from the translator so its assumed to be safe.
  layout_template = Template("""
{% if this.data %}
<table class='proto_table'>
<tbody>
  {% for key, value in this.data %}
    <tr>
      <td class="proto_key">{{key|escape}}</td><td class="proto_value">
        {{value|safe}}
      </td>
    </tr>
  {% endfor %}
</tbody>
</table>
{% endif %}
""")

  translator_error_template = Template("<pre>{{value|escape}}</pre>")

  def Layout(self, request, response):
    """Render the protodict as a table."""
    self.data = []

    for key, value in sorted(self.proxy.items()):
      try:
        renderer = FindRendererForObject(value)
        if renderer:
          value = renderer.RawHTML(request)
        else:
          raise TypeError("Unknown renderer")

      # If the translation fails for whatever reason, just output the string
      # value literally (after escaping)
      except TypeError:
        value = self.FormatFromTemplate(self.translator_error_template,
                                        value=value)
      except Exception as e:
        logging.warn("Failed to render {0}. Err: {1}".format(type(value), e))

      self.data.append((key, value))

    return super(DictRenderer, self).Layout(request, response)


class ListRenderer(RDFValueArrayRenderer):
  classname = "list"


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
<div class="centered">
<img class='grr-icon' src='/static/images/{{this.proxy.icon}}.png'
 alt='{{this.proxy.description}}' title='{{this.proxy.description}}'
 /></div>""")


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


class EmptyRenderer(TemplateRenderer):
  """A do nothing renderer."""

  layout_template = Template("")


class UnauthorizedRenderer(TemplateRenderer):
  """Send UnauthorizedAccess Exceptions to the queue."""

  layout_template = Template("""
<script>
  grr.publish("unauthorized", "{{this.subject|escapejs}}",
              "{{this.message|escapejs}}");
</script>
""")

  def Layout(self, request, response, exception=None):
    exception = exception or request.REQ.get("e", "")
    if exception:
      self.subject = exception.subject
      self.message = str(exception)

    return super(UnauthorizedRenderer, self).Layout(request, response)


class TypeInfoFormRenderer(TemplateRenderer):
  """A Renderer for the form of a type info."""

  # Derived classes should use this to specify which type_info class this
  # renderer should be used.
  type_info_cls = None

  # This lookup map is for mapping the renderer to the the TypeInfo class.
  type_map = None

  form_template = Template("")

  # This is the default view of the description.
  default_description_view = Template("""
  <label class="control-label">
    <abbr title='{{this.type.description|escape}}'>
      {{this.type.friendly_name}}
    </abbr>
  </label>
""")

  @classmethod
  def GetRendererForType(cls, type_info_cls):
    # Build a lookup map for speed.
    if cls.type_map is None:
      cls.type_map = dict(
          [(x.type_info_cls, x) for x in cls.classes.values()
           if aff4.issubclass(x, TypeInfoFormRenderer)])
    try:
      return cls.type_map[type_info_cls]
    except KeyError:
      logging.error("TypeInfo %s has no renderer.", type_info_cls)
      raise KeyError("TypeInfo %s has no renderer." % type_info_cls)

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    """Produce a string to render a form element from the type_descriptor."""
    self.type = type_descriptor
    self.value = (request.REQ.get(prefix + type_descriptor.name) or
                  type_descriptor.default)

    return self.FormatFromTemplate(self.form_template, prefix=prefix, **kwargs)

  def ParseArgs(self, type_descriptor, request, **kwargs):
    raise NotImplementedError("Type renderer %s does not know how to parse "
                              "args." % self.__class__.__name__)


class EmptyRequest(object):
  """Class used to create fake request objects."""
  pass


class TypeDescriptorSetRenderer(TemplateRenderer):
  """A Renderer for a type descriptor set."""

  form_template = Template("""
  {% for form_element in this.form_elements %}
    {{form_element|escape}}
  {% endfor %}
""")

  def Form(self, type_descriptor_set, request, **kwargs):
    """Render the form for this type descriptor set."""
    self.form_elements = []

    # This allows us to pass dictionary instead of a proper request object.
    if not hasattr(request, "REQ"):
      req = EmptyRequest()
      req.REQ = request  # pylint: disable=g-bad-name
    else:
      req = request

    for type_descriptor in type_descriptor_set:
      if not type_descriptor.hidden:
        try:
          type_renderer = TypeInfoFormRenderer.GetRendererForType(
              type_descriptor.__class__)()
        except KeyError:
          # If no special renderer is specified, use DelegatedTypeInfoRenderer.
          type_renderer = DelegatedTypeInfoRenderer()
          type_renderer.type_info_cls = type_descriptor.__class__

        # Allow the type renderer to draw the form.
        self.form_elements.append(type_renderer.Form(
            type_descriptor, req, **kwargs))

    return self.FormatFromTemplate(self.form_template)

  def ParseArgs(self, type_descriptor_set, request, **kwargs):
    """Given the type descriptor, construct the args from the request."""

    # This allows us to pass dictionary instead of a proper request object.
    if not hasattr(request, "REQ"):
      req = EmptyRequest()
      req.REQ = request
    else:
      req = request

    for type_descriptor in type_descriptor_set:
      if not type_descriptor.hidden:
        try:
          type_renderer = TypeInfoFormRenderer.GetRendererForType(
              type_descriptor.__class__)()
        except KeyError:
          # If no special renderer is specified, use DelegatedTypeInfoRenderer.
          type_renderer = DelegatedTypeInfoRenderer()
          type_renderer.type_info_cls = type_descriptor.__class__

        # Allow the type renderer to construct its own object.
        yield type_descriptor.name, type_renderer.ParseArgs(
            type_descriptor, req, **kwargs)


class DelegatedTypeInfoRenderer(TypeInfoFormRenderer):
  """A renderer which delegates the rendering to a child descriptor."""

  child_prefix = "pathspec_"

  def Form(self, type_descriptor, request, prefix="v_"):
    """Render a form for this type_descriptor."""

    # Just delegate the form building to the child descriptors.
    if type_descriptor.child_descriptor:
      type_descriptor_renderer = TypeDescriptorSetRenderer()
      return type_descriptor_renderer.Form(type_descriptor.child_descriptor,
                                           request,
                                           prefix=prefix + self.child_prefix)

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    """Parse an RDFValue for the type_descriptor from the request."""
    # Build a new RDFValue from the default, and then simply change the
    # attributes as specified in the child type_descriptor_set.
    result = type_descriptor.GetDefault()

    if type_descriptor.child_descriptor:
      type_descriptor_renderer = TypeDescriptorSetRenderer()
      for name, value in type_descriptor_renderer.ParseArgs(
          type_descriptor.child_descriptor, request,
          prefix=prefix + self.child_prefix, **kwargs):
        if value is not None:
          if not result:
            # If the default is None but there are parameters set for this
            # argument we create an object of the rdf type it should be.
            result_cls = aff4.FACTORY.RDFValue(type_descriptor.rdf_type)
            if not result_cls:
              raise ValueError("Could not get default for type %s" %
                               type_descriptor)
            result = result_cls()

          setattr(result, name, value)

    return result


class GenericProtoDictTypeRenderer(TypeInfoFormRenderer):
  """Renderer for generic ProtoDict type."""
  type_info_cls = type_info.GenericProtoDictType

  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
<div class="controls">
  <span class="uneditable-input">
    Specifying {{ this.type.name|escape }} not yet supported in the GUI.</span>
</div>
</div> <!-- control-group -->
"""

  def ParseArgs(self, type_descriptor, request, **kwargs):
    return None


class StringFormRenderer(TypeInfoFormRenderer):
  """String form element renderer."""
  type_info_cls = type_info.String

  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
<div class="controls"><input name='{{prefix}}{{ this.type.name|escape }}'
    type=text value='{{ this.value|escape }}'/></div>
</div>
"""

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    return request.REQ.get(prefix + type_descriptor.name)


class NotEmptyStringFormRenderer(StringFormRenderer):
  type_info_cls = type_info.NotEmptyString


class ByteStringRenderer(StringFormRenderer):
  type_info_cls = type_info.Bytes

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    return utils.SmartStr(super(ByteStringRenderer, self).ParseArgs(
        type_descriptor, request, prefix=prefix, **kwargs))


class FilterStringFormRenderer(StringFormRenderer):
  """Renderer for the type FilterString."""
  type_info_cls = type_info.FilterString




# TODO(user): we only support list of strings at the moment. We should
# come out with a proper way to rendering complex types like List(String) and
# so on.
class ListFormRenderer(TypeInfoFormRenderer):
  """Renderer for generic lists of objects."""
  type_info_cls = type_info.List

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    """Produce a string to render a form element from the type_descriptor."""
    if isinstance(type_descriptor.validator, type_info.String):
      self.form_template = StringFormRenderer.form_template
    else:
      return ""

    self.type = type_descriptor
    if request.REQ.get(prefix + type_descriptor.name) is not None:
      items = self.ParseArgs(type_descriptor, request, **kwargs)
    else:
      items = type_descriptor.default
    self.value = ",".join(items or [])

    return self.FormatFromTemplate(self.form_template, prefix=prefix, **kwargs)

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    if isinstance(type_descriptor.validator, type_info.String):
      str_val = request.REQ.get(prefix + type_descriptor.name)
      if str_val:
        return [x.strip() for x in str_val.split(",")]
      else:
        return []
    else:
      return ""


class InterpolatedPathRenderer(ListFormRenderer):
  """Renderer for paths that contain variable expansions."""
  type_info_cls = type_info.InterpolatedList
  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
  <script>
(function() {
  var select2_id="";

  function SetFormText(text) {
    $("#{{unique|escape}}_inputpath").focus();
    $("#{{unique|escape}}_inputpath").replaceSelectedText(text,
        "collapseToEnd");
    // Need to call change here, to notify new hunt's wizard when this
    // renderer is used there.
    $("#{{unique|escape}}_inputpath").change();
  }

  function HideDropdown() {
    $(select2_id).hide();
  }

  function ShowDropdown() {
    $(select2_id).show();
    $("#{{unique|escape}}_select").select2("open");
  }

  function SetEventHandlers() {
    $("#{{unique|escape}}_select").on("change", function(e) {
      // Note: Hunt's wizards triggers "change" event in all the controls of the
      // form every time the form is displayed. We can detect that by checking
      // if the e.val object is empty or not.
      if (e.val) {
        SetFormText(e.val);
      }
    });
    $("#{{unique|escape}}_select").on("close", function () { HideDropdown() });
    $("#{{unique|escape}}_caret").click(function () { ShowDropdown() });
  }

  $("#{{unique|escape}}_select").select2();

  // select2 injects HTML so we need to find the element ID again to hide it
  // until the dropdown is clicked.
  select2_id = "#"+$("#{{unique|escape}}_select").select2("container")[0].id;

  SetEventHandlers();
  HideDropdown();
})();
  </script>

  <div class="controls">
    <input name='{{prefix}}{{this.type.name|escape}}'
    id='{{unique|escape}}_inputpath' type=text value='{{ this.value|escape }}'/>

    <a class="btn dropdown-toggle" id='{{unique|escape}}_caret' href="#">
      <span class="caret"></span>
    </a>

    <select id='{{unique|escape}}_select'>
      {% for key, value in this.interpolated_paths.items %}
        <option value='{{value|escape}}'>{{key|escape}}</option>
      {% endfor %}
    </select>

  </div>
</div>
"""

  def GetInterpolatedPaths(self):
    """Get the list of path expansions from the User object.

    Returns:
      dictionary of path expansions: dict[label] = expansion
    """
    interpolated_paths = {}
    for attribute in rdfvalue.User().special_folders.Fields():
      expansion = "%%%%Users.special_folders.%s%%%%" % attribute
      interpolated_paths["%%%s%%" % attribute] = expansion

    interpolated_paths["%homedir%"] = "%%Users.homedir%%"
    interpolated_paths["%username%"] = "%%Users.username%%"

    return interpolated_paths

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    """Produce a string to render a form element from the type_descriptor."""
    if not isinstance(type_descriptor.validator, type_info.String):
      return ""

    self.type = type_descriptor
    self.interpolated_paths = self.GetInterpolatedPaths()

    if request.REQ.get(prefix + type_descriptor.name) is not None:
      items = self.ParseArgs(type_descriptor, request, **kwargs)
    else:
      items = type_descriptor.default
    self.value = ",".join(items or [])

    return self.FormatFromTemplate(
        self.form_template, unique=self.unique, this=self,
        prefix=prefix, **kwargs)


class RegularExpressionFormRenderer(StringFormRenderer):
  type_info_cls = type_info.RegularExpression


class NumberFormRenderer(StringFormRenderer):
  type_info_cls = type_info.Integer

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    return long(request.REQ.get(prefix + type_descriptor.name))


class DurationFormRenderer(StringFormRenderer):
  """Form elements renderer for DurationSeconds."""
  type_info_cls = type_info.Duration

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    """Produce a string to render a form element from the type_descriptor."""
    self.type = type_descriptor
    value = (request.REQ.get(prefix + type_descriptor.name) or
             type_descriptor.default)
    self.value = str(rdfvalue.Duration(value))

    return self.FormatFromTemplate(self.form_template, prefix=prefix, **kwargs)

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    return rdfvalue.Duration(utils.SmartStr(
        request.REQ.get(prefix + type_descriptor.name)))


class EncryptionKeyFormRenderer(StringFormRenderer):
  """Renders an encryption key."""

  type_info_cls = type_info.EncryptionKey

  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
<div class="controls">
<input name='{{prefix}}{{ this.type.name|escape }}'
 type=text value='{{ value|escape }}'
 size='{{field_size|escape}}'
 max_size='{{field_size|escape}}'/></div>

</div>
"""

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    self.type = type_descriptor
    bits = type_descriptor.length * 8
    key = BN.rand(bits)
    kwargs["value"] = utils.FormatAsHexString(key, width=bits/4, prefix="")
    kwargs["field_size"] = (bits/4) + 2
    return self.FormatFromTemplate(self.form_template, prefix=prefix, **kwargs)


class BoolFormRenderer(TypeInfoFormRenderer):
  """Render Boolean types."""
  type_info_cls = type_info.Bool

  form_template = Template("""
<div class="control-group">
<div class="controls">

<label class="checkbox">
  <input name='{{prefix}}{{ this.type.name|escape }}' type=checkbox
      {% if this.value %}checked {% endif %} value='{{ this.value|escape }}'/>

  <abbr title='{{this.type.description|escape}}'>
    {{this.type.friendly_name}}
  </abbr>
</label>

</div>
</div>
""")

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    value = request.REQ.get(prefix + type_descriptor.name)
    if value.lower() == "true":
      return True

    elif value.lower() == "false":
      return False


class RDFEnumFormRenderer(NumberFormRenderer):
  """Renders RDF enums."""

  type_info_cls = type_info.SemanticEnum

  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
<div class="controls">

<select name="{{prefix}}{{this.type.name|escape}}">
{% for enum_name, enum_value in enum_values %}
 <option {% ifequal enum_value value %}selected{% endifequal %}
   value="{{enum_value|escape}}">
   {{enum_name|escape}}
   {% ifequal enum_value default %} (default){% endifequal %}
</option>
{% endfor %}
</select>

</div>
</div>
"""

  def Form(self, type_descriptor, request, prefix=""):
    # We want enums to be sorted by their numerical value.
    self.type = type_descriptor
    value = type_descriptor.GetDefault()

    enum_values = sorted(
        type_descriptor.enum_container.enum_dict.items(),
        key=lambda (k, v): v)

    return self.FormatFromTemplate(
        self.form_template, enum_values=enum_values, prefix=prefix,
        default=type_descriptor.GetDefault(), value=value)


class PathTypeEnumRenderer(RDFEnumFormRenderer):
  type_info_cls = type_info.PathTypeEnum


class ArtifactListRenderer(TypeInfoFormRenderer):
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


class UserListRenderer(TypeInfoFormRenderer):
  """Renders a User selector."""

  type_info_cls = type_info.UserList

  form_template = """<div class="control-group">
""" + TypeInfoFormRenderer.default_description_view + """
<div class="controls">
<select id="user_select_{{unique|escape}}"
name="{{prefix}}{{ this.type.name|escape }}" multiple="multiple">
{% for user in valid_users %}
  <option value="{{user.username|escape}}">{{user.username|escape}}
  {% if user.domain %} ({{user.domain|escape}}){% endif %}
  </option>
{% endfor %}
</select>
</div>
</div>
"""

  def Form(self, type_descriptor, request, prefix="v_", **kwargs):
    client_id = request.REQ.get("client_id", None)
    if client_id:
      client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id), mode="r",
                                 token=request.token)
      valid_users = sorted(list(client.Get(client.Schema.USER, [])))
    else:
      valid_users = []

    return super(UserListRenderer, self).Form(
        type_descriptor, request,
        prefix=prefix, valid_users=valid_users, **kwargs)

  def ParseArgs(self, type_descriptor, request, prefix="v_", **kwargs):
    return request.REQ.getlist(prefix + type_descriptor.name + "[]") or []


class ForemanAttributeRegexTypeRenderer(DelegatedTypeInfoRenderer):
  child_prefix = ""
  type_info_cls = type_info.ForemanAttributeRegexType


class ForemanAttributeIntegerTypeRenderer(DelegatedTypeInfoRenderer):
  child_prefix = ""
  type_info_cls = type_info.ForemanAttributeIntegerType


def FindRendererForObject(rdf_obj):
  """Find the appropriate renderer for an RDFValue object."""
  for cls in RDFValueRenderer.classes.values():
    try:
      if cls.classname == rdf_obj.__class__.__name__:
        return cls(rdf_obj)
    except AttributeError:
      pass

  if isinstance(rdf_obj, (rdfvalue.RDFValueArray)):
    return RDFValueArrayRenderer(rdf_obj)

  elif isinstance(rdf_obj, rdfvalue.RDFProtoStruct):
    return RDFProtoRenderer(rdf_obj)

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
  title = ""
  pages = []

  # This will be used for identifying the wizard when publishing the events.
  wizard_name = "wizard"

  layout_template = Template("""
<div id="Wizard_{{unique|escape}}" class="Wizard">
  <div class="WizardBar modal-header">
    <button type="button" class="close" data-dismiss="modal"
      aria-hidden="true">x</button>
    <h3>{{this.title|escape}} - <span class="Description"></span></h3>
  </div>
  <div class="modal-body" id="WizardContent_{{unique|escape}}">
  </div>
  <div class="modal-footer">
    <input type="button" value="Back" class="btn Back"
      style="visibility: hidden"/>
    <input type="button" value="Next" class="btn btn-primary Next" />
  </div>
</div>

<script>
(function() {

var stateJson = {{this.state_json|safe}};
var wizardPages = stateJson.pages;
var selectedWizardTab = 0;

$("#Wizard_{{unique|escapejs}} .Back").click(function() {
  selectTab(selectedWizardTab - 1);
});

$("#Wizard_{{unique|escapejs}} .Next").click(function() {
  if (selectedWizardTab + 1 < wizardPages.length) {
    selectTab(selectedWizardTab + 1);
  } else {
    grr.publish("WizardComplete", "{{this.wizard_name|escapejs}}");
  }
});

function selectTab(index) {
  selectedWizardTab = index;
  $("#Wizard_{{unique|escapejs}} .Description").text(
    wizardPages[index].description);

  var wizardStateJson = JSON.stringify(
    $("#Wizard_{{unique|escapejs}}").data());
  grr.layout(wizardPages[index].renderer, "WizardContent_{{unique|escapejs}}",
    { "{{this.wizard_name|escapejs}}": wizardStateJson });

  $("#Wizard_{{unique|escapejs}} .Back").css("visibility",
    index > 0 && wizardPages[index].show_back_button ? "visible" : "hidden");

  var nextButton = $("#Wizard_{{unique|escapejs}} .Next");
  nextButton.attr("value", wizardPages[index].next_button_label);

  var eventToWait = wizardPages[index].wait_for_event;
  if (eventToWait) {
    nextButton.attr("disabled", "yes");
    grr.subscribe("WizardProceed", function(id) {
      if (id == eventToWait) {
        nextButton.removeAttr("disabled");
      }
    }, "Wizard_{{unique|escapejs}}");
  } else {
    nextButton.removeAttr("disabled");
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


class RDFValueCollectionRenderer(TableRenderer):
  """Renderer for RDFValueCollection objects."""

  post_parameters = ["aff4_path"]
  size = 0

  def __init__(self, **kwargs):
    super(RDFValueCollectionRenderer, self).__init__(**kwargs)
    self.AddColumn(RDFValueColumn("Value", width="100%"))

  def BuildTable(self, start_row, end_row, request):
    """Builds a table of rdfvalues."""
    try:
      aff4_path = self.state.get("aff4_path") or request.REQ.get("aff4_path")
      collection = aff4.FACTORY.Open(aff4_path,
                                     aff4_type="RDFValueCollection",
                                     token=request.token)
    except IOError:
      return

    self.size = len(collection)

    row_index = start_row
    for value in itertools.islice(collection, start_row, end_row):
      self.AddCell(row_index, "Value", value)
      row_index += 1

  def Layout(self, request, response, aff4_path=None):
    if aff4_path:
      self.state["aff4_path"] = str(aff4_path)

    return super(RDFValueCollectionRenderer, self).Layout(
        request, response)


class ConfirmationDialogRenderer(TemplateRenderer):
  """Renderer used to render confirmation dialogs."""

  header = None
  cancel_button_title = "Close"
  proceed_button_title = "Proceed"

  # If check_access_subject is None, ConfirmationDialogRenderer will first
  # do an Ajax call to a CheckAccess renderer to obtain proper token and only
  # then will do an update.
  check_access_subject = None

  # This is supplied by subclasses. Contents of this template are rendered
  # between <form></form> tags and when 'Proceed' button is pressed,
  # contents of the form get sent with the AJAX request and therefore
  # can be accessed through request.REQ from RenderAjax method.
  content_template = Template("")

  layout_template = Template("""
  {% if this.header %}
  <div class="modal-header">
    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">
      x</button>
    <h3>{{this.header|escape}}</h3>
  </div>
  {% endif %}

  <div class="modal-body">
    <form id="{{this.form_id|escape}}" class="form-horizontal">
      {{this.rendered_content|safe}}
    </form>
    <div id="results_{{unique|escape}}"></div>
    <div id="check_access_results_{{unique|escape}}" class="hide"></div>
  </div>
  <div class="modal-footer">
    <button class="btn" data-dismiss="modal" name="Cancel"
      aria-hidden="true">
      {{this.cancel_button_title|escape}}</button>
    <button id="proceed_{{unique|escape}}" name="Proceed"
      class="btn btn-primary">
      {{this.proceed_button_title|escape}}</button>
  </div>

  <script>
    $("#proceed_{{unique|escape}}").click(function() {
      $(this).attr("disabled", true);
      {% if this.check_access_subject %}
        // We execute CheckAccess renderer with silent=true. Therefore it
        // searches for an approval and sets correct reason if approval is
        // found. When CheckAccess completes, we execute specified renderer,
        // which. If the approval wasn't found on CheckAccess stage, it will
        // fail due to unauthorized access and proper ACLDialog will be
        // displayed.
        grr.layout("CheckAccess", "check_access_results_{{unique|escapejs}}",
          {silent: true, subject: "{{this.check_access_subject|escapejs}}"},
          function() {
            grr.submit("{{renderer}}", "{{this.form_id|escapejs}}",
                       "results_{{unique|escapejs}}", {{this.state_json|safe}},
                       grr.update);
            }
        );
      {% else %}
        grr.submit("{{renderer}}", "{{this.form_id|escapejs}}",
                   "results_{{unique|escapejs}}", {{this.state_json|safe}},
                   grr.update);
      {% endif %}
    });
  </script>
""")

  @property
  def rendered_content(self):
    return self.FormatFromTemplate(self.content_template,
                                   unique=self.unique)

  def Layout(self, request, response):
    self.form_id = "form_%d" % GetNextId()
    return super(ConfirmationDialogRenderer, self).Layout(request, response)
