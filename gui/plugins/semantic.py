#!/usr/bin/env python
"""This file contains specialized renderers for semantic values.

Other files may also contain specialized renderers for semantic types relevant
to their function, but here we include the most basic and common renderers.
"""

import itertools
import urllib

import logging

from grr.gui import renderers
from grr.gui.plugins import forms
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import structs


# Caches for FindRendererForObject(), We can have a renderer for a repeated
# member by extending RDFValueArrayRenderer and a renderer for a single item by
# extending RDFValueRenderer.
repeated_renderer_cache = {}
semantic_renderer_cache = {}


def FindRendererForObject(rdf_obj):
  """Find the appropriate renderer for an RDFValue object."""
  # Rebuild the cache if needed.
  if not semantic_renderer_cache:
    for cls in RDFValueRenderer.classes.values():
      if aff4.issubclass(cls, RDFValueArrayRenderer):
        repeated_renderer_cache[cls.classname] = cls

      elif aff4.issubclass(cls, RDFValueRenderer):
        semantic_renderer_cache[cls.classname] = cls

  rdf_obj_classname = rdf_obj.__class__.__name__

  # Try to find an RDFValueArray renderer for repeated types. This allows
  # renderers to be specified for repeated fields.
  if isinstance(rdf_obj, rdfvalue.RDFValueArray):
    return repeated_renderer_cache.get(
        rdf_obj_classname, RDFValueArrayRenderer)(rdf_obj)

  if isinstance(rdf_obj, structs.RepeatedFieldHelper):
    rdf_obj_classname = rdf_obj.type_descriptor.type.__name__
    return repeated_renderer_cache.get(
        rdf_obj_classname, RDFValueArrayRenderer)(rdf_obj)

  # If it is a semantic proto, we just use the RDFProtoRenderer.
  if isinstance(rdf_obj, structs.RDFProtoStruct):
    return semantic_renderer_cache.get(
        rdf_obj_classname, RDFProtoRenderer)(rdf_obj)

  # If it is a semantic value, we just use the RDFValueRenderer.
  if isinstance(rdf_obj, rdfvalue.RDFValue):
    return semantic_renderer_cache.get(
        rdf_obj_classname, RDFValueRenderer)(rdf_obj)

  elif isinstance(rdf_obj, dict):
    return DictRenderer(rdf_obj)

  # Default renderer.
  return RDFValueRenderer(rdf_obj)


class RDFValueColumn(renderers.TableColumn):
  """A column to store an RDFValue in a Table."""

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
    super(AttributeColumn, self).__init__(name, **kwargs)

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


class RDFValueRenderer(renderers.TemplateRenderer):
  """These are abstract classes for rendering RDFValues."""

  # This specifies the name of the RDFValue object we will render.
  classname = ""

  layout_template = renderers.Template("""
{{this.proxy|escape}}
""")

  def __init__(self, proxy, **kwargs):
    """Constructor.

    This class renders a specific AFF4 object which we delegate.

    Args:
      proxy: The RDFValue class we delegate.
      **kwargs: passthrough to baseclass.
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

  layout_template = renderers.Template("""
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

  layout_template = renderers.Template("""
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

  layout_template = renderers.Template("""
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
               t=renderers.DeriveIDFromPath(rest))
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
  layout_template = renderers.Template("""
<table class='proto_table'>
<tbody>
{% for key, desc, value in this.result %}
<tr>
  <td class="proto_key">
    {% if desc %}
      <abbr title='{{desc|escape}}'>
        {{key|escape}}
      </abbr>
    {% else %}
      {{key|escape}}
    {% endif %}
  </td>
  <td class="proto_value">
  {{value|safe}}
  </td>
</tr>
{% endfor %}
</tbody>
</table>
""")

  # This is a translation dispatcher for rendering special fields.
  translator = {}

  translator_error_template = renderers.Template("<pre>{{value|escape}}</pre>")

  def Ignore(self, unused_descriptor, unused_value):
    """A handler for ignoring a value."""
    return None

  hrb_template = renderers.Template("{{value|filesizeformat}}")

  def HumanReadableBytes(self, _, value):
    """Format byte values using human readable units."""
    return self.FormatFromTemplate(self.hrb_template, value=value)

  pre_template = renderers.Template("<pre>{{value|escape}}</pre>")

  def Pre(self, _, value):
    return self.FormatFromTemplate(self.pre_template, value=value)

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.result = []
    for descriptor, value in self.proxy.ListFields():
      name = descriptor.name
      friendly_name = descriptor.friendly_name or name

      # Try to translate the value if there is a special translator for it.
      if name in self.translator:
        try:
          value = self.translator[name](self, None, value)
          if value is not None:
            self.result.append((friendly_name, descriptor.description, value))

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

        self.result.append((friendly_name, descriptor.description,
                            renderer.RawHTML(request)))

    return super(RDFProtoRenderer, self).Layout(request, response)


class RDFValueArrayRenderer(RDFValueRenderer):
  """Renders arrays of RDFValues."""

  # {{entry}} comes from the individual rdfvalue renderers so it is assumed to
  # be safe.
  layout_template = renderers.Template("""
<table class='proto_table'>
<tbody>
{% for entry in this.data %}
<tr class="proto_separator"></tr>
<tr>
   <td>{{entry|safe}}</td>
</tr>
{% endfor %}
{% if this.additional_data %}
<tr class="proto_separator"></tr>
<tr>
 <td> (Additional data available) </td>
</tr>
{% endif %}
</tbody>
</table>
""")

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.data = []

    for element in self.proxy:
      if len(self.data) > 10:
        self.additional_data = True
        break

      renderer = FindRendererForObject(element)
      if renderer:
        try:
          self.data.append(renderer.RawHTML(request))
        except Exception as e:  # pylint: disable=broad-except
          logging.error(
              "Unable to render %s with %s: %s", type(element), renderer, e)

    return super(RDFValueArrayRenderer, self).Layout(request, response)


class DictRenderer(RDFValueRenderer):
  """Renders dicts."""

  classname = "Dict"

  # {{value}} comes from the translator so its assumed to be safe.
  layout_template = renderers.Template("""
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

  translator_error_template = renderers.Template("<pre>{{value|escape}}</pre>")

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


class IconRenderer(RDFValueRenderer):
  width = 0
  layout_template = renderers.Template("""
<div class="centered">
<img class='grr-icon' src='/static/images/{{this.proxy.icon}}.png'
 alt='{{this.proxy.description}}' title='{{this.proxy.description}}'
 /></div>""")


class RDFValueCollectionRenderer(renderers.TableRenderer):
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


class ProgressButtonRenderer(RDFValueRenderer):
  """Renders a button that shows a progress graph."""

  # This specifies the name of the RDFValue object we will render.
  classname = "ProgressGraph"

  layout_template = renderers.Template("""
Open a graph showing the download progress in a new window:
<button id="{{ unique|escape }}">
 Generate
</button>
<script>
  var button = $("#{{ unique|escapejs }}").button();

  var state = {flow_id: '{{this.flow_id|escapejs}}'};
  grr.downloadHandler(button, state, false,
                      '/render/Download/ProgressGraphRenderer');
</script>
""")

  def Layout(self, request, response):
    self.flow_id = request.REQ.get("flow")
    return super(ProgressButtonRenderer, self).Layout(request, response)


class FlowStateRenderer(DictRenderer):
  """A Flow state is similar to a dict."""
  classname = "FlowState"


class DataObjectRenderer(DictRenderer):
  """A flow data object is also similar to a dict."""
  classname = "DataObject"


class AES128KeyFormRenderer(forms.StringTypeFormRenderer):
  """Renders an encryption key."""

  type = rdfvalue.AES128Key

  layout_template = """
<div class="control-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text value='{{ this.default|escape }}'
      onchange="grr.forms.inputOnChange(this)"
    />
  </div>
</div>
<script>
$("#{{this.prefix}}").change();
</script>
"""

  def Layout(self, request, response):
    self.default = str(self.descriptor.type().Generate())
    return super(AES128KeyFormRenderer, self).Layout(request, response)


class ClientURNRenderer(RDFValueRenderer):
  """A renderer for a client id."""

  classname = "ClientURN"

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}' onclick='grr.loadFromHash(
    "{{this.hash|escape}}");'>
  {{this.proxy|escape}}
</a>
""")

  def Layout(self, request, response):
    h = dict(main="HostInformation", c=self.proxy)
    self.hash = urllib.urlencode(sorted(h.items()))
    return super(ClientURNRenderer, self).Layout(request, response)
