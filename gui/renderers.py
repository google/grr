#!/usr/bin/env python

# Copyright 2010 Google Inc.
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


"""This module contains base classes for different kind of renderers."""

import csv
import json
import re
import StringIO


from django import http
from django import template

from grr.lib import aff4
from grr.lib import registry
from grr.lib import utils

# Global counter for ids
COUNTER = 1

# Maximum size of tables that can be downloaded
MAX_ROW_LIMIT = 1000000

class RDFValueColumn(object):
  """A column holds a bunch of cell values which are RDFValue instances."""

  def __init__(self, name, header=None, renderer=None, sortable=False):
    """Constructor.

    Args:

     name: The name of this column.The name of this column normally
       shown in the column header.

     header: (Optional) If exists, we call its Layout() method to
       render the column headers.

     renderer: The RDFValueRenderer that should be used in this column. Default
       is None - meaning it will be automatically calculated.

     sortable: Should this column be sortable.
    """
    self.name = name
    self.header = header
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
        response.write(str(self.header))
    else:
      response.write(str(self.name))

  def AddElement(self, index, element):
    self.rows[index] = element

  def RenderRow(self, index):
    """Render the RDFValue stored at the specific index."""
    value = self.rows.get(index, "")

    renderer = self.renderer
    if renderer is None:
      # What is the RDFValueRenderer for this attribute?
      renderer = RDFValueRenderer.RendererForRDFValue(
          value.__class__.__name__)

    # Intantiate the renderer and return the HTML
    if renderer:
      return renderer(value).RawHTML()
    else:
      return str(value)


class AttributeColumn(RDFValueColumn):
  """A table column which can be filled from an AFF4Object."""

  def __init__(self, name, **kwargs):
    # Locate the attribute
    self.attribute = aff4.Attribute.GetAttributeByName(name)

    RDFValueColumn.__init__(self, name, **kwargs)

  def AddRowFromFd(self, index, fd):
    """Add a new value from the fd."""
    value = fd.Get(self.attribute)
    if value:
      self.rows[index] = value


class Renderer(object):
  """Baseclass for renderer classes."""

  __metaclass__ = registry.MetaclassRegistry

  # The following should be set for renderers that should be visible from the
  # main menu. Note- this does not allow inheritance - must be set for each
  # class that should be visible.
  category = None
  description = None

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
    self.id = request.REQ.get("id", hash(self))
    self.unique = GetNextId()

    return response

  def RenderFromTemplate(self, template_obj, response, **kwargs):
    """A helper function to render output from a template.

    Args:
       template_obj: The template object to use.
       response: A HttpResponse object
       kwargs: Arguments to be expanded into the template.

    Returns:
       the same response object we got.
    """
    context = template.Context(kwargs)
    response.write(template_obj.render(context))
    return response

  def FormatFromTemplate(self, template_obj, **kwargs):
    """Return a safe formatted unicode object using a template."""
    return template_obj.render(template.Context(kwargs)).encode("utf8")

  def FormatFromString(self, string, **kwargs):
    """Returns a http response from a dynamically compiled template."""
    result = http.HttpResponse(mimetype="text/html")
    template_obj = template.Template(string)
    return self.RenderFromTemplate(template_obj, result, **kwargs)


class TableRenderer(Renderer):
  """A renderer for tables.

  In order to have a table rendered, it is only needed to subclass
  this class in a plugin. Requests to the URL table/ClassName are then
  handled by this class.
  """

  # We receive change path events from this queue
  event_queue = "tree_select"
  table_options = {}

  def __init__(self):
    # A list of columns
    self.columns = []
    self.column_dict = {}
    # Number of rows
    self.size = 0
    self.message = ""
    # Make a copy of the table options so they can be mutated.
    self.table_options = self.table_options.copy()
    self.table_options["iDisplayLength"] = 50

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
      except KeyError: pass

    row_index += 1
    self.size = max(self.size, row_index)

  def AddCell(self, row_index, column_name, value):
    if row_index is None:
      row_index = self.size

    try:
      self.column_dict[column_name].AddElement(row_index, value)
    except KeyError: pass

    self.size = max(self.size, row_index)

  # This is the data table sDom parameter to control table formatting.
  format = template.Template("""<"H"lrp><"TableBody"t><"F">""")

  table_template = template.Template("""
<div id="toolbar_{{unique}}" class="toolbar"></div>
<div class="tableWrapper" id="table_wrapper_{{unique}}">
<table id="table_{{ unique }}" class="table">
    <thead>
      {% autoescape off %}
<tr> {{ headers }} </tr>
      {% endautoescape %}
    </thead>
    <tbody>
    </tbody>
</table>
</div>
<script>
  grr.grrTable("{{ renderer|escapejs }}",
               "{{ id|escapejs }}",
               "{{ format|escapejs }}", grr.state,
      {% autoescape off %}
               {{ options }});
      {% endautoescape %}

  grr.subscribe("GeometryChange", function () {
    grr.fixHeight($("#table_wrapper_{{unique}}"));
    $(".TableBody").each(function () {grr.fixHeight($(this))});
  }, "table_{{unique}}");

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
    response = super(TableRenderer, self).Layout(request, response)

    self.table_options = self.table_options.copy()
    self.table_options.setdefault("aoColumnDefs", []).append(
        {"bSortable": False,
         "aTargets": [i for i, c in enumerate(self.columns) if not c.sortable]})

    self.table_options["sTableId"] = GetNextId()

    headers = http.HttpResponse(mimetype="text/html")
    for i in self.columns:
      # Ask each column to draw itself
      headers.write("<th>")
      i.LayoutHeader(request, headers)
      headers.write("</th>")

    encoder = json.JSONEncoder()
    return self.RenderFromTemplate(
        self.table_template, response,
        headers=headers.content,
        unique=self.unique, format=self.format.render(
            template.Context(dict(unique=self.unique))),
        options=encoder.encode(self.table_options),
        id=self.id, renderer=self.__class__.__name__)

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
    super(TableRenderer, self).RenderAjax(request, response)

    start_row = int(request.REQ.get("iDisplayStart", 0))
    limit_row = int(request.REQ.get("iDisplayLength", 10))

    try:
      self.BuildTable(start_row, limit_row + start_row, request)
    except Exception, e:
      self.message = str(e)

    response = dict(sEcho=request.REQ.get("sEcho", 0),
                    message=self.message,
                    aaData=[],
                    iTotalDisplayRecords=self.size,
                    iTotalRecords=self.size)

    for index in xrange(start_row, min(start_row+limit_row, self.size)):
      response["aaData"].append([str(c.RenderRow(index)) for c in self.columns])

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(response),
                             mimetype="application/json")

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

        writer.writerow([RemoveTags(c.RenderRow(i)) for c in self.columns])

      # The last chunk
      yield fd.getvalue()

    response = http.HttpResponse(content=Generator(),
                                 mimetype="binary/x-csv")

    # This must be a string.
    response["Content-Disposition"] = ("attachment; filename=table.csv")

    return response


class TreeRenderer(Renderer):
  """An abstract Renderer to support a navigation tree."""

  publish_select_queue = "tree_select"

  # This state object will be updated (Default global state).
  state = "grr.state"

  renderer_template = template.Template("""
<script>
grr.grrTree("{{ renderer }}", "{{ id }}",
            "{{ publish_select_queue }}", {{ state|escapejs }});
</script>""")

  def Layout(self, request, response):
    response = super(TreeRenderer, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.renderer_template, response,
        publish_select_queue=self.publish_select_queue,
        id=self.id, state=self.state,
        renderer=self.__class__.__name__)


class TabLayout(Renderer):
  """This renderer creates a set of tabs containing other renderers."""

  names = []
  renderers = []

  # These are pre-compiled templates
  layout_template = template.Template("""
<div id="tab_container_{{ unique }}">
<ul>
 {% for child, name in indexes %}
  <li>
   <a tab_name="{{name}}"
    href="render/Layout/{{ child }}?tab=tab_container_{{unique}}">
   <span>{{ name }}</span></a>
  </li>
 {% endfor %}
</ul>
</div>

<script>
  $("#tab_container_{{ unique }}").tabs({
    ajaxOptions: {
      data: grr.state,
      type: grr.ajax_method,
    },
  }).bind('tabsselect', function (event, ui) {
    grr.state.selected_tab = ui.tab.attributes.tab_name.nodeValue;
  }).tabs("select", {{ select }});

  //Fix up the height of the tab containers.
  grr.subscribe("GeometryChange", function () {
    $(".ui-tabs-panel").each(function() {
     grr.fixHeight($(this));
    });
  }, "tab_container_{{ unique }}");
</script>

""")

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    response = super(TabLayout, self).Layout(request, response)

    selected_tab = request.REQ.get("selected_tab")
    try:
      selected = self.names.index(selected_tab)
    except ValueError:
      selected = 0

    indexes = [(self.renderers[i], self.names[i])
               for i in range(len(self.names))]

    return self.RenderFromTemplate(
        self.layout_template,
        response, path=request.path, id=self.id,
        unique=self.unique, select=selected, indexes=indexes
        )


class Splitter(Renderer):
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

  # This ensures that many Splitters can be placed in the same page by
  # making ids unique.
  splitter_template = template.Template("""
      <div id="{{id|escapejs}}_leftPane" class="leftPane"></div>
      <div id="{{id|escapejs}}_rightPane" class="rightPane">
        <div id="{{ id|escapejs }}_rightSplitterContainer"
         class="rightSplitterContainer">
          <div id="{{id|escapejs}}_rightTopPane"
           class="rightTopPane"></div>
          <div id="{{id|escapejs}}_rightBottomPane"
           class="rightBottomPane"></div>
        </div>
      </div>
<script>
      $("#{{ id|escapejs }}")
          .splitter({
              minAsize: 100,
              maxAsize: 3000,
              splitVertical: true,
              A: $('#{{id|escapejs}}_leftPane'),
              B: $('#{{id|escapejs}}_rightPane'),
              slave: $("#{{id|escapejs}}_rightSplitterContainer"),
              closeableto: 0})
          .bind("resize", function () {grr.publish("GeometryChange");});

      $("#{{id|escapejs}}_rightSplitterContainer")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_rightTopPane'),
              B: $('#{{id|escapejs}}_rightBottomPane'),
              closeableto: 100});

grr.layout("{{ left_renderer }}", "{{id|escapejs}}_leftPane");
grr.layout("{{ top_right_renderer }}", "{{id|escapejs}}_rightTopPane");
grr.layout("{{ bottom_right_renderer }}", "{{id|escapejs}}_rightBottomPane");
</script>
""")

  def Layout(self, request, response):
    response = super(Splitter, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.splitter_template,
        response,
        id=self.id,
        left_renderer=self.left_renderer,
        top_right_renderer=self.top_right_renderer,
        bottom_right_renderer=self.bottom_right_renderer)


class Splitter2Way(Splitter):
  """A two way top/bottom Splitter."""
  top_renderer = ""
  bottom_renderer = ""

  splitter_template = template.Template("""
      <div id="{{id|escapejs}}_topPane" class="rightTopPane"></div>
      <div id="{{id|escapejs}}_bottomPane" class="rightBottomPane"></div>
<script>
      $("#{{id|escapejs}}")
          .splitter({
              splitHorizontal: true,
              A: $('#{{id|escapejs}}_topPane'),
              B: $('#{{id|escapejs}}_bottomPane'),
              closeableto: 100})
          .bind("resize", function () {grr.publish("GeometryChange");});

grr.layout("{{ top_renderer }}", "{{id|escapejs}}_topPane");
grr.layout("{{ bottom_renderer }}", "{{id|escapejs}}_bottomPane");
</script>
""")

  def Layout(self, request, response):
    """Layout the two way splitter into the correct container."""
    response = Renderer.Layout(self, request, response)

    return self.RenderFromTemplate(
        self.splitter_template,
        response,
        id=self.id,
        top_renderer=self.top_renderer,
        bottom_renderer=self.bottom_renderer)


class TextInput(Renderer):
  """A Renderer to produce a text input field.

  The renderer will publish keystrokes to the publish_queue.
  """
  # The descriptive text
  text = ""
  name = ""
  publish_queue = ""

  template = template.Template("""
<div class="GrrSearch">
{{ text }}<br>
<input type="text" name="{{ name }}" id="{{ id }}_text"></input></div>
<script>
   grr.installEventsForText("{{ id|escapejs }}_text",
                            "{{ queue_name|escapejs }}");
</script>
""")

  def Layout(self, request, response):
    """Display a search screen for the host."""
    response = super(TextInput, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.template, response,
        id=str(self.id) + self.name,
        name=self.name,
        queue_name=self.publish_queue,
        text=self.text)


class Button(Renderer):
  """A Renderer for a button."""
  text = "A button"

  template = template.Template("""
<button id="{{ id }}_button">{{ text }}</button>
<script>
 $('#{{ id }}_button').button()
</script>
""")

  def Layout(self, request, response):
    """Display a search screen for the host."""
    response = super(Button, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.template, response,
        id=self.id,
        text=self.text)


def GetNextId():
  """Generate a unique id."""
  global COUNTER
  COUNTER += 1
  return COUNTER


class RDFValueRenderer(Renderer):
  """These are abstract classes for rendering RDFValues."""

  # This specifies the name of the RDFValue object we will render.
  ClassName = ""

  def __init__(self, proxy):
    """Constructor.

    This class renders a specific AFF4 object which we delegate.

    Args:
      proxy: The RDFValue class we delegate.
    """
    super(RDFValueRenderer, self).__init__()
    self.proxy = proxy

  def Layout(self, _, response):
    """Render ourselves into the response."""
    return response.write(str(self.proxy))

  def RawHTML(self, request=None):
    """This returns raw HTML, after sanitization by Layout()."""
    result = http.HttpResponse(mimetype="text/html")
    self.Layout(request, result)

    return result.content

  @classmethod
  def RendererForRDFValue(cls, rdfvalue_cls_name):
    """Returns the class of the RDFValueRenderer which renders rdfvalue_cls."""
    for candidate in cls.classes.values():
      if (issubclass(candidate, RDFValueRenderer) and
          candidate.ClassName == rdfvalue_cls_name):
        return candidate


class SubjectRenderer(RDFValueRenderer):
  """A special renderer for Subject columns."""
  ClassName = "Subject"

  subject_template = template.Template("""
<span type=subject>{{subject}}</span>
""")

  def Layout(self, _, response):
    return self.RenderFromTemplate(self.subject_template, response,
                                   subject=self.proxy)


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

  proto_template = template.Template("""
<table class='proto_table'>
<tbody>
{% for key, value in data %}
<tr>
<td class="proto_key">{{key}}</td><td class="proto_value">
{% autoescape off %}
{{value}}
{% endautoescape %}
</td>
</tr>
{% endfor %}
</tbody>
</table>
""")

  # This is a translation dispatcher for rendering special fields.
  translator = None

  def Ignore(self, unused_descriptor, unused_value):
    """A handler for ignoring a value."""
    return None

  time_template = template.Template("{{value}}")

  def Time(self, _, value):
    return self.FormatFromTemplate(self.time_template,
                                   value=aff4.RDFDatetime(value))

  def Time32Bit(self, _, value):
    return self.FormatFromTemplate(self.time_template,
                                   value=aff4.RDFDatetime(value*1000000))

  pre_template = template.Template("<pre>{{value}}</pre>")

  def Pre(self, _, value):
    return self.FormatFromTemplate(self.pre_template, value=value)

  def Enum(self, descriptor, value):
    try:
      return descriptor.enum_type.values_by_number[value].name
    except (AttributeError, KeyError):
      return value

  def ProtoDict(self, _, value):
    """Render a ProtoDict as a string of values."""
    st = ["%s:%s" % (k, v) for k, v in utils.ProtoDict(value).ToDict().items()]
    return " ".join(st)

  def RenderField(self, field_name):
    protobuf = getattr(self.proxy, self.proxy_field)
    value = getattr(protobuf, field_name)
    try:
      if self.translator:
        value = self.translator[field_name](self, None, value)
    except KeyError: pass

    return value

  def Layout(self, _, response):
    """Render the protobuf as a table."""
    result = []

    for descriptor, value in getattr(self.proxy, self.proxy_field).ListFields():
      # Try to translate the value
      name = descriptor.name
      try:
        if self.translator:
          value = self.translator[name](self, descriptor, value)
      except KeyError: pass
      if value:
        result.append((name, value))

    return self.RenderFromTemplate(self.proto_template, response, data=result)


class RDFProtoArrayRenderer(RDFProtoRenderer):
  """Renders arrays of protobufs."""

  proto_template = template.Template("""
<table class='proto_table'>
<tbody>
{% for proto_table in data %}
<tr class="proto_separator"></tr>
  {% for key, value in proto_table %}
    <tr>
      <td class="proto_key">{{key}}</td><td class="proto_value">
        {% autoescape off %}
        {{value}}
        {% endautoescape %}
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
          if self.translator:
            value = self.translator[name](self, descriptor, value)
        except KeyError: pass
        if value:
          proto_table.append((name, value))

      result.append(proto_table)

    return self.RenderFromTemplate(self.proto_template, response, data=result)


class IconRenderer(RDFValueRenderer):

  layout_template = template.Template("""
<img class='grr-icon' src='/static/images/{{icon}}' />""")

  def Layout(self, _, response):
    icon = str(self.proxy)
    if "." not in icon: icon += ".png"

    return self.RenderFromTemplate(
        self.layout_template, response, icon=icon)


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
