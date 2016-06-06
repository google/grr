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
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import standard as aff4_standard
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs

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
  if isinstance(rdf_obj, rdf_protodict.RDFValueArray):
    return repeated_renderer_cache.get(rdf_obj_classname,
                                       RDFValueArrayRenderer)(rdf_obj)

  if isinstance(rdf_obj, rdf_structs.RepeatedFieldHelper):
    rdf_obj_classname = rdf_obj.type_descriptor.type.__name__
    return repeated_renderer_cache.get(rdf_obj_classname,
                                       RDFValueArrayRenderer)(rdf_obj)

  # If it is a semantic proto, we just use the RDFProtoRenderer.
  if isinstance(rdf_obj, rdf_structs.RDFProtoStruct):
    return semantic_renderer_cache.get(rdf_obj_classname,
                                       RDFProtoRenderer)(rdf_obj)

  # If it is a semantic value, we just use the RDFValueRenderer.
  if isinstance(rdf_obj, rdfvalue.RDFValue):
    return semantic_renderer_cache.get(rdf_obj_classname,
                                       RDFValueRenderer)(rdf_obj)

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

  def __init__(self, proxy=None, **kwargs):
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
<span type=subject aff4_path='{{this.aff4_path|escape}}'
  tree_node_id='{{this.tree_node_id|escape}}'>
  {{this.basename|escape}}
</span>
""")

  def Layout(self, request, response):
    if not self.proxy:
      return

    aff4_path = request.REQ.get("aff4_path", "")
    aff4_path = rdfvalue.RDFURN(aff4_path)
    self.basename = self.proxy.RelativeName(aff4_path) or self.proxy
    self.aff4_path = self.proxy
    self.tree_node_id = renderers.DeriveIDFromPath("/".join(
        self.aff4_path.Split()[1:]))

    return super(SubjectRenderer, self).Layout(request, response)


class RDFBytesRenderer(RDFValueRenderer):
  """A renderer for RDFBytes."""
  classname = "RDFBytes"

  def Layout(self, request, response):
    self.proxy = utils.SmartStr(self.proxy).encode("string-escape")
    super(RDFBytesRenderer, self).Layout(request, response)


class LiteralExpressionRenderer(RDFBytesRenderer):
  classname = "LiteralExpression"


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
    for descriptor, value in self.proxy.ListSetFields():
      name = descriptor.name
      friendly_name = descriptor.friendly_name or name

      # Try to translate the value if there is a special translator for it.
      if name in self.translator:
        try:
          value = self.translator[name](self, request, value)
          if value is not None:
            self.result.append((friendly_name, descriptor.description, value))

          # If the translation fails for whatever reason, just output the string
          # value literally (after escaping)
        except KeyError:
          value = self.FormatFromTemplate(self.translator_error_template,
                                          value=value)
        except Exception as e:  # pylint: disable=broad-except
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
{% if this.next_start %}
<tr class="proto_separator"></tr>
<tr>
 <td><div id="{{unique}}"> (<a>Additional data available</a>) </div></td>
</tr>
{% endif %}
</tbody>
</table>
""")

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    # Remove these from the request in case we need to pass it to another
    # renderer.
    start = int(request.REQ.pop("start", 0))
    length = int(request.REQ.pop("length", 10))

    # We can get called again to render from an existing cache.
    cache = request.REQ.pop("cache", None)
    if cache:
      self.cache = aff4.FACTORY.Open(cache, token=request.token)
      self.proxy = rdf_protodict.RDFValueArray(self.cache.Read(1000000))

    else:
      # We need to create a cache if this is too long.
      if len(self.proxy) > length:
        # Make a cache
        with aff4.FACTORY.Create(None,
                                 aff4_standard.TempMemoryFile,
                                 token=request.token) as self.cache:
          data = rdf_protodict.RDFValueArray()
          data.Extend(self.proxy)
          self.cache.Write(data.SerializeToString())

    self.data = []

    self.next_start = 0
    for i, element in enumerate(self.proxy):
      if i < start:
        continue

      elif len(self.data) > length:
        self.next_start = i
        self.length = 100
        break

      renderer = FindRendererForObject(element)
      if renderer:
        try:
          self.data.append(renderer.RawHTML(request))
        except Exception as e:  # pylint: disable=broad-except
          logging.error("Unable to render %s with %s: %s", type(element),
                        renderer, e)

    response = super(RDFValueArrayRenderer, self).Layout(request, response)
    if self.next_start:
      response = self.CallJavascript(response,
                                     "RDFValueArrayRenderer.Layout",
                                     next_start=self.next_start,
                                     cache_urn=self.cache.urn,
                                     array_length=self.length)
    return response


class DictRenderer(RDFValueRenderer):
  """Renders dicts."""

  classname = "Dict"
  # Keys to filter from the output.
  filter_keys = None

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

  def __init__(self, proxy=None, filter_keys=None, **kwargs):
    self.filter_keys = filter_keys or []
    super(DictRenderer, self).__init__(proxy=proxy, **kwargs)

  def Layout(self, request, response):
    """Render the protodict as a table."""
    self.data = []

    for key, value in sorted(self.proxy.items()):
      rendered_value = None

      if key in self.filter_keys:
        continue
      try:
        renderer = FindRendererForObject(value)
        if renderer:
          rendered_value = renderer.RawHTML(request)
        else:
          raise TypeError("Unknown renderer")

      # If the translation fails for whatever reason, just output the string
      # value literally (after escaping)
      except TypeError:
        rendered_value = self.FormatFromTemplate(self.translator_error_template,
                                                 value=value)
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("Failed to render {0}. Err: {1}".format(type(value), e))

      if rendered_value is not None:
        self.data.append((key, rendered_value))

    return super(DictRenderer, self).Layout(request, response)


class ListRenderer(RDFValueArrayRenderer):
  classname = "list"


class IconRenderer(RDFValueRenderer):
  width = 0
  layout_template = renderers.Template("""
<div class="centered">
<img class='grr-icon {{this.proxy.icon}}'
 src='/static/images/{{this.proxy.icon}}.png'
 alt='{{this.proxy.description}}' title='{{this.proxy.description}}'
 /></div>""")


class RDFValueCollectionRenderer(renderers.TableRenderer):
  """Renderer for RDFValueCollection objects."""

  post_parameters = ["aff4_path"]
  size = 0
  show_total_count = True
  layout_template = """
{% if this.size > 0 %}
  {% if this.show_total_count %}
    <h5>{{this.size}} Entries</h5>
  {% endif %}
{% endif %}
""" + renderers.TableRenderer.layout_template

  def __init__(self, **kwargs):
    super(RDFValueCollectionRenderer, self).__init__(**kwargs)
    self.AddColumn(RDFValueColumn("Value", width="100%"))

  def BuildTable(self, start_row, end_row, request):
    """Builds a table of rdfvalues."""
    try:
      aff4_path = self.state.get("aff4_path") or request.REQ.get("aff4_path")
      collection = aff4.FACTORY.Open(aff4_path,
                                     aff4_type=collects.RDFValueCollection,
                                     token=request.token)
    except IOError:
      return

    try:
      self.size = len(collection)
    except AttributeError:
      self.show_total_count = False

    row_index = start_row
    for value in itertools.islice(collection, start_row, end_row):
      self.AddCell(row_index, "Value", value)
      row_index += 1

  def Layout(self, request, response, aff4_path=None):
    if aff4_path:
      self.state["aff4_path"] = str(aff4_path)
      collection = aff4.FACTORY.Create(aff4_path,
                                       mode="r",
                                       aff4_type=collects.RDFValueCollection,
                                       token=request.token)

      try:
        self.size = len(collection)
      except AttributeError:
        self.show_total_count = False

    return super(RDFValueCollectionRenderer, self).Layout(request, response)


class FlowStateRenderer(DictRenderer):
  """A Flow state is similar to a dict."""
  classname = "FlowState"


class DataObjectRenderer(DictRenderer):
  """A flow data object is also similar to a dict."""
  classname = "DataObject"


class AES128KeyFormRenderer(forms.StringTypeFormRenderer):
  """Renders an encryption key."""

  type = rdf_crypto.AES128Key

  layout_template = """
<div class="form-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text value='{{ this.default|escape }}'
      onchange="grr.forms.inputOnChange(this)"
    />
  </div>
</div>
"""

  def Layout(self, request, response):
    self.default = str(self.descriptor.type().Generate())
    response = super(AES128KeyFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "AES128KeyFormRenderer.Layout",
                               prefix=self.prefix)


class ClientURNRenderer(RDFValueRenderer):
  """A renderer for a client id."""

  classname = "ClientURN"

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}' onclick='grr.loadFromHash(
    "{{this.hash|escape}}");'>
  {{this.proxy|escape}}
</a>

<div id="ClientInfo_{{unique|escape}}" class="modal fade" role="dialog"
     aria-hidden="true">
  <div class="modal-dialog">
   <div class="modal-content">
    <div class="modal-header">
     <button type="button" class="close"
       aria-hidden="true" data-dismiss="modal">
      &times;
     </button>
     <h4 class="modal-title">Client {{this.proxy}}</h4>
    </div>
    <div id="ClientInfoContent_{{unique|escape}}" class="modal-body"/></div>
   </div>
  </div>
</div>

<button
 class="btn btn-default btn-xs" id="ClientInfoButton_{{unique}}">
 <span class="glyphicon glyphicon-info-sign"></span>
</button>
""")

  ajax_template = renderers.Template("""
{{this.summary|safe}}
""")

  def Layout(self, request, response):
    h = dict(main="HostInformation", c=self.proxy)
    self.hash = urllib.urlencode(sorted(h.items()))
    response = super(ClientURNRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "Layout",
                               urn=utils.SmartStr(self.proxy))

  def RenderAjax(self, request, response):
    self.urn = request.REQ.get("urn")
    if self.urn:
      fd = aff4.FACTORY.Open(self.urn, token=request.token)
      self.summary = FindRendererForObject(fd.GetSummary()).RawHTML(request)

    return super(ClientURNRenderer, self).RenderAjax(request, response)


class KeyValueFormRenderer(forms.TypeDescriptorFormRenderer):
  """A renderer for a Dict's KeyValue protobuf."""
  type = rdf_protodict.KeyValue

  layout_template = renderers.Template("""<div class="form-group">
<div id="{{unique}}" class="control input-append">
 <input id='{{this.prefix}}_key'
  type=text
{% if this.default %}
  value='{{ this.default.key|escape }}'
{% endif %}
  onchange="grr.forms.inputOnChange(this)"
  class="unset"/>
 <input id='{{this.prefix}}_value'
  type=text
{% if this.default %}
  value='{{ this.default.value|escape }}'
{% endif %}
  onchange="grr.forms.inputOnChange(this)"
  class="unset"/>

 <div class="btn-group">
  <button class="btn btn-default dropdown-toggle" data-toggle="dropdown">
    <span class="Type">Auto</span>  <span class="caret"></span>
  </button>

  <ul class="dropdown-menu" data-name="{{this.prefix}}_type">
   <li><a data-type="String">String</a></li>
   <li><a data-type="Integer">Integer</a></li>
   <li><a data-type="Bytes">Bytes</a></li>
   <li><a data-type="Float">Float</a></li>
   <li><a data-type="Boolean">Boolean</a></li>
  </ul>
 </div>
 </div>
</div>
""")

  def Layout(self, request, response):
    response = super(KeyValueFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "Layout")

  def GuessValueType(self, value):
    """Get the type of value."""
    if value in ["None", "none", None]:
      return None

    if value in ["True", "true", "yes"]:
      return True

    if value in ["False", "false", "no"]:
      return False

    try:
      return int(value)
    except (TypeError, ValueError):
      try:
        return float(value)
      except (TypeError, ValueError):
        try:
          return value.decode("utf8")
        except UnicodeDecodeError:
          return value

  def ParseArgs(self, request):
    """Parse the request into a KeyValue proto."""
    key = request.REQ.get("%s_key" % self.prefix)
    value = request.REQ.get("%s_value" % self.prefix)
    value_type = request.REQ.get("%s_type" % self.prefix)

    if key is None:
      return

    result = rdf_protodict.KeyValue()
    result.k.SetValue(key)

    # Automatically try to detect the value
    if value_type is None:
      value = self.GuessValueType(value)
    elif value_type == "Integer":
      value = int(value)
    elif value_type == "Float":
      value = float(value)
    elif value_type == "Boolean":
      if value in ["True", "true", "yes", "1"]:
        value = True

      elif value in ["False", "false", "no", "0"]:
        value = False

      else:
        raise ValueError("Value %s is not a boolean" % value)
    elif value_type == "String":
      value = value.decode("utf8")

    result.v.SetValue(value)

    return result
