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

import logging

from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import user_managers

# Global counter for ids
COUNTER = 1

# Maximum size of tables that can be downloaded
MAX_ROW_LIMIT = 1000000


def GetNextId():
  """Generate a unique id."""
  global COUNTER  # pylint: disable=global-statement
  COUNTER += 1  # pylint: disable=g-bad-name
  return COUNTER


def StringifyJSON(item):
  """Recursively convert item to a string.

  Since JSON can only encode strings we need to convert complex types to string.

  Args:
    item: A python data object.

  Returns:
    A data object suitable for JSON encoding.
  """
  if isinstance(item, (tuple, list)):
    return [StringifyJSON(x) for x in item]

  elif isinstance(item, dict):
    result = {}
    for k, v in item.items():
      result[k] = StringifyJSON(v)

    return result

  # pyformat: disable
  elif type(item) in (int, long, float, bool):  # pylint: disable=unidiomatic-typecheck
    return item
  # pyformat: enable

  elif item is None:
    return None

  else:
    return utils.SmartUnicode(item)


class Template(template.Template):
  """A specialized template which supports concatenation."""

  def __init__(self, template_string, allow_script=False):
    """Template constructor.

    Args:
      template_string: Template contents.
      allow_script: If False, ValueError will be raised when <script>
                    tag is found inside template_string. NOTE: this is
                    not a security check, but rather a convenience check
                    for developers so that they put javascript code into
                    the right place: not into templates, but into separate
                    javascript files.
    Raises:
      ValueError: if allow_script is False and <script> tag is found
                  inside the template.
    """
    self.template_string = template_string
    if not allow_script and "<script" in template_string:
      raise ValueError("<script> tags inside templates are not allowed. Please "
                       " use separate javascript files and "
                       "Renderer.CallJavascript() calls.")

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

  def RawHTML(self, **kwargs):
    kwargs["unique"] = GetNextId()
    return self.render(template.Context(kwargs))


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

  context_help_url = ""  # Class variable to store context sensitive help.

  js_call_template = Template("""
<script>
  grr.ExecuteRenderer("{{method|escapejs}}", {{js_state_json|safe}});
</script>
""",
                              allow_script=True)

  help_template = Template("""
{% if this.context_help_url %}
<div style="width: 15px; height: 0px; position: absolute; right: 10px; top:0">
  <a href="/help/{{this.context_help_url|escape}}" target="_blank">
  <i class="glyphicon glyphicon-question-sign"></i></a>
</div>
{% endif %}
""")

  # pylint: disable=redefined-builtin
  def __init__(self, id=None, state=None, renderer_name=None, **kwargs):
    self.state = state or kwargs
    self.id = id
    self.unique = GetNextId()
    self.renderer_name = renderer_name or self.__class__.__name__

  # pylint: enable=redefined-builtin

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
    js_state = self.state.copy()
    js_state.update(dict(unique=self.unique,
                         id=self.id,
                         renderer=self.__class__.__name__))

    # Since JSON can only represent strings, we must force inputs to a string
    # here.
    js_state.update(StringifyJSON(kwargs))

    if "." not in method:
      method = "%s.%s" % (self.__class__.__name__, method)

    js_state_json = JsonDumpForScriptContext(js_state)
    self.RenderFromTemplate(self.js_call_template,
                            response,
                            method=method,
                            js_state_json=js_state_json)
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
    self.state_json = JsonDumpForScriptContext(self.state)

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
    kwargs["this"] = self
    context = template.Context(kwargs)
    if not isinstance(template_obj, Template):
      raise RuntimeError("template must be an instance of Template")

    response.write(template_obj.render(context))
    return response

  def FormatFromTemplate(self, template_obj, **kwargs):
    """Return a safe formatted unicode object using a template."""
    kwargs["this"] = self
    return template_obj.render(template.Context(kwargs)).encode("utf8")

  def FormatFromString(self, string, content_type="text/html", **kwargs):
    """Returns a http response from a dynamically compiled template."""
    result = http.HttpResponse(content_type=content_type)
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

  @property
  def javascript_path(self):
    return "static/javascript/%s.js" % (
        self.classes[self.renderer].__module__.split(".")[-1])

# This will register all classes into this modules's namespace regardless of
# where they are defined. This allows us to decouple the place of definition of
# a class (which might be in a plugin) from its use which will reference this
# module.
Renderer.classes = globals()


class UserLabelCheckMixin(object):
  """Checks the user has a label or deny access to this renderer."""

  # This should be overridden in the mixed class.
  AUTHORIZED_LABELS = []

  @classmethod
  def CheckAccess(cls, request):
    """If the user is not in the AUTHORIZED_LABELS, reject this renderer."""
    user_managers.CheckUserForLabels(request.token.username,
                                     cls.AUTHORIZED_LABELS,
                                     token=request.token)


class ErrorHandler(Renderer):
  """An error handler decorator which can be applied on individual methods."""

  def __init__(self, status_code=503, **kwargs):
    super(ErrorHandler, self).__init__(**kwargs)
    self.status_code = status_code

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(utils.SmartUnicode(e))
        response = http.HttpResponse()
        response = self.CallJavascript(response,
                                       "ErrorHandler.Layout",
                                       error=utils.SmartUnicode(e),
                                       backtrace=traceback.format_exc())
        response.status_code = 500

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
  ajax_template = Template("")

  def Layout(self, request, response, apply_template=None):
    """Render the layout from the template."""
    for parameter in self.post_parameters:
      value = request.REQ.get(parameter)
      if value is not None:
        self.state[parameter] = value

    response = super(TemplateRenderer, self).Layout(request, response)
    if apply_template is None:
      apply_template = self.layout_template

    canary_mode = getattr(request, "canary_mode", False)

    return self.RenderFromTemplate(apply_template,
                                   response,
                                   this=self,
                                   id=self.id,
                                   unique=self.unique,
                                   renderer=self.__class__.__name__,
                                   canary_mode=canary_mode)

  def RenderAjax(self, request, response):
    return TemplateRenderer.Layout(self,
                                   request,
                                   response,
                                   apply_template=self.ajax_template)

  def RawHTML(self, request=None, method=None, **kwargs):
    """This returns raw HTML, after sanitization by Layout()."""
    if method is None:
      method = self.Layout
    result = http.HttpResponse(content_type="text/html")
    method(request, result, **kwargs)
    return result.content

  def __str__(self):
    return self.RawHTML()


class AngularDirectiveRendererBase(TemplateRenderer):
  """Renderers specified Angular directive with given parameters."""

  __abstract = True  # pylint: disable=g-bad-name

  directive = None
  directive_args = None

  def Layout(self, request, response, **kwargs):
    if self.directive is None:
      raise ValueError("'directive' attribute has to be specified.")

    self.directive_args = self.directive_args or {}

    response = super(AngularDirectiveRendererBase, self).Layout(request,
                                                                response,
                                                                **kwargs)
    return self.CallJavascript(response,
                               "AngularDirectiveRenderer.Layout",
                               directive=self.directive,
                               directive_args=self.directive_args)


class AngularDirectiveRenderer(AngularDirectiveRendererBase):
  """Renderers specified Angular directive as div."""

  layout_template = Template("""
<div class="full-width-height" id="{{unique|escape}}"></div>
""")


class AngularSpanDirectiveRenderer(AngularDirectiveRendererBase):
  """Renderers specified Angular directive as span."""

  layout_template = Template("""
<span id="{{unique|escape}}"></span>
""")


class EscapingRenderer(TemplateRenderer):
  """A simple renderer to escape a string."""
  layout_template = Template("{{this.to_escape|escape}}")

  def __init__(self, to_escape, **kwargs):
    self.to_escape = to_escape
    super(EscapingRenderer, self).__init__(**kwargs)


class TableColumn(object):
  """A column holds a bunch of cell values which are RDFValue instances."""

  width = None

  def __init__(self,
               name,
               header=None,
               renderer=None,
               sortable=False,
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
    """Render the data stored at the specific index."""
    value = self.rows.get(index)
    if value is None:
      return ""

    if row_options is not None:
      row_options["row_id"] = index

    if self.renderer:
      renderer = self.renderer(value)
      result = renderer.RawHTML(request)
    else:
      result = utils.SmartStr(value)

    return result


class TableRenderer(TemplateRenderer):
  """A renderer for tables.

  In order to have a table rendered, it is only needed to subclass
  this class in a plugin. Requests to the URL table/classname are then
  handled by this class.
  """

  fixed_columns = False
  show_total_count = False
  custom_class = ""

  # We receive change path events from this queue
  event_queue = "tree_select"
  table_options = {}
  message = ""

  def __init__(self, **kwargs):
    # A list of columns
    self.columns = []
    self.column_dict = {}
    self.row_classes_dict = {}
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
      **kwargs: column names and values for this row.
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

    self.size = max(self.size, row_index + 1)

  def AddRowFromFd(self, index, fd):
    """Adds the row from an AFF4 object."""
    for column in self.columns:
      # This sets AttributeColumns directly from their fd.
      try:
        column.AddRowFromFd(index, fd)
      except AttributeError:
        pass
    self.size = max(self.size, index + 1)

  def GetCell(self, row_index, column_name):
    """Gets the value of a Cell."""
    if row_index is None:
      row_index = self.size

    try:
      return self.column_dict[column_name].GetElement(row_index)
    except KeyError:
      pass

  def SetRowClass(self, row_index, value):
    if row_index is None:
      row_index = self.size

    self.row_classes_dict[row_index] = value

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
""") + TemplateRenderer.help_template

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
    tmp = http.HttpResponse(content_type="text/html")
    delegate_renderer = self.__class__(id=self.id, state=self.state.copy())
    self.table_contents = delegate_renderer.RenderAjax(request, tmp).content

    response = super(TableRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "TableRenderer.Layout",
                               renderer=self.__class__.__name__,
                               table_state=self.state,
                               message=self.message)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table between the start and end rows.

    This should normally be overridden by derived classes.

    Args:
      start_row: The initial row to populate.
      end_row: The final row to populate.
      request: The request object.
    """

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
    self.additional_rows = self.BuildTable(start_row, limit_row + start_row,
                                           request)

    end_row = min(start_row + limit_row, self.size)

    self.rows = []
    for index in xrange(start_row, end_row):
      row_options = {}
      try:
        row_options["class"] = self.row_classes_dict[index]
      except KeyError:
        pass

      row = []
      for c in self.columns:
        row.append(utils.SmartStr(c.RenderRow(index, request, row_options)))

      self.rows.append((row, row_options.items()))

    if self.additional_rows is None:
      self.additional_rows = self.size > end_row

    # If we did not write any additional rows in this round trip we ensure the
    # table does not try to fetch more rows. This is a safety check in case
    # BuildTable does not set the correct size and end row. Without this check
    # the browser will spin trying to fill the table.
    if not self.rows:
      self.additional_rows = False

    response = super(TableRenderer, self).Layout(
        request, response, apply_template=self.ajax_template)
    return self.CallJavascript(response,
                               "TableRenderer.RenderAjax",
                               message=self.message)

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
      for i in xrange(0, self.size):
        if i % 1000 == 0:
          # Flush the buffer
          yield fd.getvalue()
          fd.truncate(size=0)

        writer.writerow([RemoveTags(c.RenderRow(i, request)) for c in
                         self.columns])

      # The last chunk
      yield fd.getvalue()

    response = http.StreamingHttpResponse(streaming_content=Generator(),
                                          content_type="binary/x-csv")

    # This must be a string.
    response["Content-Disposition"] = ("attachment; filename=table.csv")

    return response


class TreeRenderer(TemplateRenderer):
  """An abstract Renderer to support a navigation tree."""

  publish_select_queue = "tree_select"

  layout_template = Template("""
<div id="{{unique|escape}}"></div>""")

  hidden_branches = []  # Branches to hide in the tree.

  def Layout(self, request, response):
    response = super(TreeRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "TreeRenderer.Layout",
                               renderer=self.__class__.__name__,
                               publish_select_queue=self.publish_select_queue,
                               tree_state=self.state)

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
    for name, friendly_name, icon, behaviour in self._elements:
      if name:
        fullpath = os.path.join(path, name)
        if fullpath in self.hidden_branches:
          continue
        data = dict(text=friendly_name,
                    li_attr=dict(id=DeriveIDFromPath(fullpath),
                                 path=fullpath))
        if behaviour == "branch":
          data["children"] = True
        else:
          data["icon"] = icon

        result.append(data)

    # If this is a completely empty tree we have to return at least something
    # or the tree will load forever.
    if not result and path == "/":
      result.append(dict(text=path,
                         li_attr=dict(id=DeriveIDFromPath(path),
                                      path=path)))

    return JsonResponse(result)

  def AddElement(self, name, behaviour="branch", icon=None, friendly_name=None):
    """This should be called by the RenderBranch method to prepare the tree."""
    if icon is None:
      icon = behaviour

    if friendly_name is None:
      friendly_name = name

    self._elements.append((name, friendly_name, icon, behaviour))
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
""") + TemplateRenderer.help_template

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

    response = super(TabLayout, self).Layout(request, response, apply_template)
    return self.CallJavascript(response,
                               "TabLayout.Layout",
                               disabled=self.disabled,
                               tab_layout_state=self.state,
                               tab_hash=self.tab_hash,
                               selected_tab=self.selected)


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
""")

  def Layout(self, request, response):
    """Layout."""
    self.id = request.REQ.get("id", hash(self))

    # Pre-render the top and bottom layout contents to avoid extra round trips.
    self.left_pane = self.classes[self.left_renderer](id="%s_leftPane" %
                                                      self.id).RawHTML(request)

    self.top_right_pane = self.classes[self.top_right_renderer](
        id="%s_rightTopPane" % self.id).RawHTML(request)

    self.bottom_right_pane = self.classes[self.bottom_right_renderer](
        id="%s_rightBottomPane" % self.id).RawHTML(request)

    response = super(Splitter, self).Layout(request, response)
    return self.CallJavascript(response,
                               "Splitter.Layout",
                               min_left_pane_width=self.min_left_pane_width,
                               max_left_pane_width=self.max_left_pane_width)


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
<div id="{{unique}}"/>
""") + TemplateRenderer.help_template

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

    response = super(Splitter2Way, self).Layout(request, response)
    return self.CallJavascript(response, "Splitter2Way.Layout")


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
<div id="{{unique}}"/>
""") + TemplateRenderer.help_template

  def Layout(self, request, response):
    """Layout."""
    self.id = self.id or request.REQ.get("id", hash(self))

    # Pre-render the top and bottom layout contents to avoid extra round trips.
    self.left_pane = self.classes[self.left_renderer](
        id="%s_leftPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    self.right_pane = self.classes[self.right_renderer](
        id="%s_rightPane" % self.id,
        state=self.state.copy()).RawHTML(request)

    response = super(Splitter2WayVertical, self).Layout(request, response)
    return self.CallJavascript(response,
                               "Splitter2WayVertical.Layout",
                               min_left_pane_width=self.min_left_pane_width,
                               max_left_pane_width=self.max_left_pane_width)


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
  return "_" + "-".join([invalid_chars.sub(lambda x: "_%02X" % ord(x.group(0)),
                                           x) for x in components if x])


class ErrorRenderer(TemplateRenderer):
  """Render Exceptions."""

  def Layout(self, request, response):
    response = self.CallJavascript(response,
                                   "ErrorRenderer.Layout",
                                   value=request.REQ.get("value", ""))


class EmptyRenderer(TemplateRenderer):
  """A do nothing renderer."""

  layout_template = Template("")


class ConfirmationDialogRenderer(TemplateRenderer):
  """Renderer used to render confirmation dialogs."""

  # If this is True, the container div won't have "modal-dialog" class. This is
  # useful when we want to render the dialog inside existing modal dialog,
  # because having 2 nested divs both having "modal-dialog" class confuses
  # Bootstrap.
  inner_dialog_only = False

  header = None
  cancel_button_title = "Close"
  proceed_button_title = "Proceed"

  # If check_access_subject is not None, ConfirmationDialogRenderer will first
  # do an Ajax call to a CheckAccess renderer to obtain proper token and only
  # then will do an update.
  check_access_subject = None

  # This is supplied by subclasses. Contents of this template are rendered
  # between <form></form> tags and when 'Proceed' button is pressed,
  # contents of the form get sent with the AJAX request and therefore
  # can be accessed through request.REQ from RenderAjax method.
  content_template = Template("")

  layout_template = Template("""
<div class="FormData {% if not this.inner_dialog_only %}modal-dialog{% endif %}">
  <div class="modal-content">
    {% if this.header %}
    <div class="modal-header">
      <button type="button" class="close" data-dismiss="modal"
        aria-hidden="true" ng-click="$dismiss()">
        x
      </button>
      <h3>{{this.header|escape}}</h3>
    </div>
    {% endif %}

    <div class="modal-body">
      <form id="form_{{unique|escape}}" class="form-horizontal">
        {{this.rendered_content|safe}}
      </form>
      <div id="results_{{unique|escape}}"></div>
      <div id="check_access_results_{{unique|escape}}" class="hide"></div>
    </div>
    <div class="modal-footer">
      <ul class="nav pull-left">
        <div class="navbar-text" id="footer_message_{{unique}}"></div>
      </ul>

      <button class="btn btn-default" data-dismiss="modal" name="Cancel"
        aria-hidden="true" ng-click="$dismiss()">
        {{this.cancel_button_title|escape}}</button>
      <button id="proceed_{{unique|escape}}" name="Proceed"
        class="btn btn-primary">
        {{this.proceed_button_title|escape}}</button>
    </div>
  </div>
</div>
""")

  @property
  def rendered_content(self):
    return self.FormatFromTemplate(self.content_template, unique=self.unique)

  def Layout(self, request, response):
    super(ConfirmationDialogRenderer, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "ConfirmationDialogRenderer.Layout",
        check_access_subject=utils.SmartStr(self.check_access_subject or ""))


class ImageDownloadRenderer(TemplateRenderer):
  """Baseclass for renderers which simply transfer an image graphic."""
  content_type = "image/png"

  def Content(self, request, response):
    _ = request, response
    return ""

  def Download(self, request, response):

    response = http.HttpResponse(content=self.Content(request, response),
                                 content_type=self.content_type)

    return response


def JsonDumpForScriptContext(dump_object):
  """Dump an object to json, encoding safely for <script> inclusion."""
  js_state_json = json.dumps(dump_object)
  # As the json will be written inside script tags in html context (as opposed
  # to being retrieved via XHR) it will be parsed as html by the browser first,
  # and then by the json parser, so we must escape < & > to prevent someone
  # including <script> tags and creating XSS security bugs.
  return js_state_json.replace("<", r"\\x3c").replace(">", r"\\x3e")


def JsonResponse(dump_object, xssi_protection=True):
  """Return a django JSON response object with correct headers."""
  result = JsonDumpForScriptContext(dump_object)
  if xssi_protection:
    result = ")]}\n" + result

  response = http.HttpResponse(result,
                               content_type="application/json; charset=utf-8")

  response["Content-Disposition"] = "attachment; filename=response.json"
  response["X-Content-Type-Options"] = "nosniff"

  return response
