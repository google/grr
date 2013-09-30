#!/usr/bin/env python
"""This plugin renders form elements for constructing semantic protocol buffers.

How does this work:

1) A semantic protocol buffer class is provided to the
SemanticProtoFormRenderer, and then we ask to render the HTML for a form to
create such a proto instance. The output is the HTML form, with inputs for each
of the fields in the protocol buffer. The caller simply treats this as an opaque
HTML form (which is properly XSS protected).

2) The values can be constructed by calling
SemanticProtoFormRenderer().ParseArgs(request). This uses the request parameters
to construct data and returns the semantic protocol buffer instance.
"""



from grr.gui import renderers
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


# Caches for GetTypeDescriptorRenderer(), We can have a renderer for a repeated
# member by extending RepeatedFieldFormRenderer and a renderer for a single item
# by extending TypeDescriptorFormRenderer.
repeated_renderer_cache = {}
semantic_renderer_cache = {}


def GetTypeDescriptorRenderer(type_descriptor):
  """Return a TypeDescriptorFormRenderer responsible for the type_descriptor."""
  # Cache a mapping between type descriptors and their renderers for speed.
  if not semantic_renderer_cache:
    # Rebuild the cache on first access.
    for renderer_cls in TypeDescriptorFormRenderer.classes.values():
      # A renderer can specify that it works on a type. This is used for nested
      # protobuf.
      delegate = getattr(renderer_cls, "type", None)

      # Or a generic type descriptor (i.e. all items of this type).
      if delegate is None:
        delegate = getattr(renderer_cls, "type_descriptor", None)

      # Repeated form renderers go in their own cache.
      if utils.issubclass(renderer_cls, RepeatedFieldFormRenderer):
        repeated_renderer_cache[delegate] = renderer_cls
        continue

      if delegate:
        semantic_renderer_cache[delegate] = renderer_cls

  # Try to find a renderer for this type descriptor's type:
  if isinstance(type_descriptor, type_info.ProtoList):
    # Special handling for repeated fields - must read from
    # repeated_renderer_cache.
    delegate_type = getattr(type_descriptor.delegate, "type", None)
    cache = repeated_renderer_cache
    default = RepeatedFieldFormRenderer

  else:
    delegate_type = getattr(type_descriptor, "type", None)
    cache = semantic_renderer_cache
    default = StringTypeFormRenderer

  result = cache.get(delegate_type)

  # Try to find a handler for all fields of this type.
  if result is None:
    result = cache.get(type_descriptor.__class__)

  # Fallback in case we have no handler.
  if result is None:
    result = default

  return result


class SemanticProtoFormRenderer(renderers.TemplateRenderer):
  """A form renderer for a semantic protobuf.

  Modified fields will be stored in the data of the containing element with the
  class 'FormData'.
  """

  layout_template = renderers.Template("""
<div id='{{unique}}'>
    {% for form_element in this.form_elements %}
      {{form_element|safe}}
    {% endfor %}
  {% if this.advanced_elements %}
  <div class="control-group">
    <a id="advanced_label_{{unique|escape}}"
      class="control-label advanced-label">Advanced</a>
    <div class="controls"><i class="advanced-icon icon-chevron-right"></i></div>
  </div>
  <div class="hide advanced-controls" id="advanced_controls_{{unique|escape}}">
    {% for form_element in this.advanced_elements %}
      {{form_element|safe}}
    {% endfor %}
  </div>
  {% endif %}
</div>
""")

  def __init__(self, proto_obj=None, prefix="v_", supressions=None,
               opened=True, **kwargs):
    """Create a semantic protobuf form renderer.

    How to use this renderer:
    1) Simply instantiate the renderer with a suitable proto_obj arg.

    2) Call the RawHTML(request) to receive a html document with the input
       fields. The document can be inserted into any template (with the safe
       filter).

    3) All form parameters will be stored in the jquery .data() object of the
       closest ".FormData" selector above us in the DOM. So code like this will
       result in all relevant data being submitted:

       grr.update("{{renderer}}", "{{id}}", $(".FormData").data());

    4) To construct an instance of the filled in protobuf, simply instantiate
       this renderer and call its ParseArgs() method on the request object
       obtained from the .data() object.

       instance = SemanticProtoFormRenderer(proto_obj).ParseArgs(request)

    Args:
      proto_obj: The class of the protobuf we should create.

      prefix: To prevent name clashes all our fields will be prefixed with this.

      supressions: A list of field names we suppress.

      opened: If specified, we open all nested protobufs.

      **kwargs: passthrough to baseclass.
    """
    self.proto_obj = proto_obj
    self.opened = opened
    self.supressions = set(supressions or [])
    self.descriptors = proto_obj.type_infos
    self.prefix = prefix
    super(SemanticProtoFormRenderer, self).__init__(**kwargs)

  def Layout(self, request, response):
    """Construct a form for filling in the protobuf."""
    self.form_elements = []
    self.advanced_elements = []
    for descriptor in self.descriptors:
      # Skip suppressed fields.
      if descriptor.name in self.supressions:
        continue

      # Ignore hidden labeled members.
      if (rdfvalue.SemanticDescriptor.Labels.HIDDEN not in descriptor.labels and
          "HIDDEN" not in descriptor.labels):
        kwargs = dict(descriptor=descriptor, opened=self.opened,
                      container=self.proto_obj,
                      prefix=self.prefix + "-" + descriptor.name)

        if self.proto_obj.HasField(descriptor.name):
          kwargs["value"] = getattr(self.proto_obj, descriptor.name)

        type_renderer = GetTypeDescriptorRenderer(descriptor)(**kwargs)

        # Put the members which are labeled as advanced behind an advanced
        # button.
        if (rdfvalue.SemanticDescriptor.Labels.ADVANCED in descriptor.labels or
            "ADVANCED" in descriptor.labels):
          # Allow the type renderer to draw the form.
          self.advanced_elements.append(type_renderer.RawHTML(request))
        else:
          self.form_elements.append(type_renderer.RawHTML(request))

    response = super(SemanticProtoFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "Layout")

  def ParseArgs(self, request):
    """Parse all the post parameters and build a new protobuf instance."""
    result = self.proto_obj

    # Name may be a deep reference a.b.c.d for nested protobufs.
    for name in request.REQ:
      if not name.startswith(self.prefix):
        continue

      if name.endswith("[]"):
        # This was an array value, e.g. multi select box and we need to strip.
        name = name[0:-2]

      # Strip the prefix from the name
      field = name[len(self.prefix) + 1:].split("-")[0]

      # We already did this field - skip it.
      if result.HasField(field):
        continue

      # Recover the type descriptor renderer for this field.
      descriptor = self.descriptors.get(field)
      if descriptor is None:
        continue

      type_renderer = GetTypeDescriptorRenderer(descriptor)(
          descriptor=descriptor, container=self.proto_obj,
          prefix=self.prefix + "-" + descriptor.name)

      # Delegate the arg parsing to the type descriptor renderer and set it
      # into the protobuf.
      result.Set(field, type_renderer.ParseArgs(request))

    return result


class TypeDescriptorFormRenderer(renderers.TemplateRenderer):
  """A renderer for a type descriptor form."""

  # This should be set to the type descriptor class we are responsible for.
  type_descriptor = None

  # This is the default view of the description.
  default_description_view = renderers.Template("""
  {% if this.render_label %}
  <label class="control-label">
    <abbr title='{{this.descriptor.description|escape}}'>
      {{this.friendly_name}}
    </abbr>
  </label>
  {% endif %}
""")

  friendly_name = None

  def __init__(self, descriptor=None, prefix="v_", opened=False, default=None,
               value=None, container=None, render_label=True, **kwargs):
    """Create a new renderer for a type descriptor.

    Args:
      descriptor: The descriptor to use.

      prefix: The prefix of our args. We can set any args specifically for our
        own use by prepending them with this unique prefix.

      opened: If this is specified, we open all our children.

      default: Use this default value to initialize form elements.

      value: This is the value of this field. Note that this is not the same as
        default - while default specifies value when the field is not set, value
        specifies that this field is actually set.

      container: The container of this field.

      render_label: If True, will render the label for this field.

      **kwargs: Passthrough to baseclass.
    """
    self.descriptor = descriptor
    self.value = value
    self.opened = opened
    self.container = container
    self.render_label = render_label
    self.default = default
    if default is None and descriptor:
      self.default = self.descriptor.GetDefault(container=self.container)

    self.prefix = prefix
    super(TypeDescriptorFormRenderer, self).__init__(**kwargs)

  def Layout(self, request, response):
    self.friendly_name = (self.friendly_name or
                          self.descriptor.friendly_name or
                          self.descriptor.name)

    return super(TypeDescriptorFormRenderer, self).Layout(request, response)

  def ParseArgs(self, request):
    result = request.REQ.get(self.prefix)
    if result is not None:
      return result


class StringTypeFormRenderer(TypeDescriptorFormRenderer):
  """String form element renderer."""
  type_descriptor = type_info.ProtoString

  layout_template = ("""<div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text
{% if this.default %}
  value='{{ this.default|escape }}'
{% endif %}
      onchange="grr.forms.inputOnChange(this)"
      class="unset"/>
  </div>
</div>
""")

  def Layout(self, request, response):
    super(StringTypeFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "StringTypeFormRenderer.Layout",
                               default=self.default, value=self.value,
                               prefix=self.prefix)


class ProtoRDFValueFormRenderer(StringTypeFormRenderer):
  """A Generic renderer for RDFValue Semantic types."""

  type_descriptor = type_info.ProtoRDFValue

  def Layout(self, request, response):
    if self.value is not None:
      self.value = self.value.SerializeToString()

    if self.default is not None:
      self.default = self.default.SerializeToString()

    return super(ProtoRDFValueFormRenderer, self).Layout(request, response)


class IntegerTypeFormRenderer(StringTypeFormRenderer):
  type_descriptor = type_info.ProtoUnsignedInteger

  def ParseArgs(self, request):
    result = request.REQ.get(self.prefix)
    if result is None:
      return

    try:
      return long(result)
    except ValueError as e:
      raise ValueError("Unable to parse field %s: %s" % (self.prefix, e))


class SignedIntegerTypeFormRenderer(IntegerTypeFormRenderer):
  type_descriptor = type_info.ProtoSignedInteger


class IntegerU32TypeFormRenderer(IntegerTypeFormRenderer):
  type_descriptor = type_info.ProtoFixedU32


class Integer32TypeFormRenderer(IntegerTypeFormRenderer):
  type_descriptor = type_info.ProtoFixed32


class Integer64TypeFormRenderer(IntegerTypeFormRenderer):
  type_descriptor = type_info.ProtoFixed64


class FloatTypeFormRenderer(StringTypeFormRenderer):
  type_descriptor = type_info.ProtoFloat

  def ParseArgs(self, request):
    result = request.REQ.get(self.prefix)
    if result is None:
      return

    try:
      return float(result)
    except ValueError as e:
      raise ValueError("Unable to parse field %s: %s" % (self.prefix, e))


class EmbeddedProtoFormRenderer(TypeDescriptorFormRenderer):
  """A form renderer for an embedded semantic protobuf."""
  type_descriptor = type_info.ProtoEmbedded

  layout_template = ("""<div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
   <div class='nested_opener'>
{% if this.opened %}
     {{this.prefetched|safe}}
{% else %}
     <i class='nested-icon icon-plus' id='{{unique|escape}}'
       data-rdfvalue='{{this.type_name}}' data-prefix='{{this.prefix}}'
      />
     <div id='content_{{unique|escape}}'></div>
{% endif %}
   </div>
  </div>
</div>
""")

  ajax_template = renderers.Template("""
{{this.delegated_renderer_layout|safe}}
""")

  def Layout(self, request, response):
    """Build the form elements for the nested protobuf."""
    self.type_name = self.descriptor.type.__name__

    # If we have data under us we must open the expander to show it.
    if self.value is not None:
      self.opened = True

    if self.opened:
      delegated_renderer = SemanticProtoFormRenderer(
          proto_obj=self.value or self.default, opened=False,
          prefix=self.prefix)

      self.prefetched = delegated_renderer.RawHTML(request)

    response = super(EmbeddedProtoFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "EmbeddedProtoFormRenderer.Layout")

  def RenderAjax(self, request, response):
    """Renders the nested proto inside the expanded div."""
    prefix = request.REQ.get("prefix")
    class_name = request.REQ.get("rdfvalue")

    # We render a form for the nested type descriptor set. In order to protect
    # against name collisions, we simply ensure that the delegated renderer uses
    # a unique name to this member prefix. The result is that nested fields have
    # names like v.pathspec.path - each . represents another level of nesting in
    # the protobuf.
    delegated_renderer = SemanticProtoFormRenderer(
        rdfvalue.RDFValue.classes[class_name](), opened=False, prefix=prefix)

    self.delegated_renderer_layout = delegated_renderer.RawHTML(request)

    response = renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.ajax_template)
    return self.CallJavascript(response, "RenderAjax")

  def ParseArgs(self, request):
    """Parse all the post parameters and build a new protobuf instance."""
    result = self.descriptor.type()
    descriptors = result.type_infos

    # Name may be a deep reference a.b.c.d for nested protobufs.
    for name in request.REQ:
      if not name.startswith(self.prefix):
        continue

      # Strip the prefix from the name
      field = name[len(self.prefix) + 1:].split("-")[0]

      # We already did this field - skip it.
      if result.HasField(field):
        continue

      # Recover the type descriptor renderer for this field.
      descriptor = descriptors.get(field)
      if descriptor is None:
        continue

      type_renderer = GetTypeDescriptorRenderer(descriptor)(
          descriptor=descriptor, container=self.container,
          prefix=self.prefix + "-" + descriptor.name)

      # Delegate the arg parsing to the type descriptor renderer and set it
      # into the protobuf.
      try:
        result.Set(field, type_renderer.ParseArgs(request))
      except ValueError as e:
        raise ValueError("Unable to set field %s: %s" % (field, e))

    return result


class DynamicFormRenderer(EmbeddedProtoFormRenderer):
  """Render a dynamic protobuf type member."""

  type_descriptor = type_info.ProtoDynamicEmbedded


class RepeatedFieldFormRenderer(TypeDescriptorFormRenderer):
  """A renderer for a protobuf repeated field."""

  type_descriptor = type_info.ProtoList

  layout_template = renderers.Template("""
  <div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
    <div class="controls">
      <button class="btn form-add" id="add_{{unique|escape}}"
        data-count=0 data-prefix="{{this.prefix|escape}}">
        <i class="icon-plus"></i>
      </button>
    </div>
  </div>
  <div id="content_{{unique}}" />
""")

  ajax_template = renderers.Template("""
<button type=button class="control-label close" data-dismiss="alert">x</button>
<div class="control-group" id="{{unique|escape}}"
  data-index="{{this.index}}" data-prefix="{{this.prefix}}">

  {{this.delegated|safe}}
</div>
""")

  def Layout(self, request, response):
    """Build form elements for repeated fields."""
    self.owner = self.descriptor.owner.__name__
    self.field = self.descriptor.name

    response = super(RepeatedFieldFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "Layout",
                               owner=self.descriptor.owner.__name__,
                               field=self.descriptor.name,
                               prefix=self.prefix)

  def ParseArgs(self, request):
    """Parse repeated fields from post parameters."""
    result = []

    # The form tells us how many items there should be. Note that they can be
    # sparse since when an item is removed, the count is not decremented.
    count = int(request.REQ.get("%s_count" % self.prefix, 0))

    # Parse out the items and fill them into the result. Note that we do not
    # support appending empty repeated fields. Such fields may happen by adding
    # and removing the form for the repeated member.
    for index in range(0, count+1):
      delegate_prefix = "%s-%s" % (self.prefix, index)
      delegate = self.descriptor.delegate
      delegate_renderer = GetTypeDescriptorRenderer(delegate)(
          descriptor=delegate, opened=True, container=self.container,
          prefix=delegate_prefix)

      child = delegate_renderer.ParseArgs(request)
      if child:
        result.append(child)

    return result

  def RenderAjax(self, request, response):
    """Insert a new form for another repeated member."""
    self.prefix = request.REQ.get("prefix")
    self.index = request.REQ.get("index", 0)
    self.owner = request.REQ.get("owner")
    self.field = request.REQ.get("field")

    self.delegate_prefix = "%s-%s" % (self.prefix, self.index)

    # Recover the type descriptor of this field from the post args.
    cls = rdfvalue.RDFValue.classes[self.owner]
    delegate = cls.type_infos[self.field].delegate

    delegated_renderer = GetTypeDescriptorRenderer(delegate)(
        descriptor=delegate, opened=True, container=self.container,
        prefix=self.delegate_prefix, render_label=False)

    self.delegated = delegated_renderer.RawHTML(request)

    response = super(RepeatedFieldFormRenderer, self).RenderAjax(
        request, response)
    return self.CallJavascript(response, "RenderAjax")


class EnumFormRenderer(TypeDescriptorFormRenderer):
  """Renders the form for protobuf enums."""

  type_descriptor = type_info.ProtoEnum

  layout_template = """<div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
<div class="controls">

<select id="{{this.prefix}}" class="unset"
  onchange="grr.forms.inputOnChange(this)"
  >
{% for enum_name, enum_value in this.items %}
 <option {% ifequal enum_value this.default %}selected{% endifequal %}
   value="{{enum_value|escape}}">
   {{enum_name|escape}}{% ifequal enum_value this.default %} (default)
                       {% endifequal %}
 </option>
{% endfor %}
</select>
</div>
</div>
"""

  def Layout(self, request, response):
    self.items = sorted(self.descriptor.enum.items(), key=lambda x: x[1])
    super(EnumFormRenderer, self).Layout(request, response)

    if self.value is not None:
      self.value = int(self.value)

    if self.default is not None:
      self.default = int(self.default)

    return self.CallJavascript(response, "Layout",
                               default=self.default, value=self.value,
                               prefix=self.prefix)


class ProtoBoolFormRenderer(EnumFormRenderer):
  """Render a checkbox for boolean values."""
  type_descriptor = type_info.ProtoBoolean

  layout_template = renderers.Template("""
<div class="control-group">
<div class="controls">

<label class="checkbox">
  <input id='{{this.prefix}}' type=checkbox class="unset"
      {% if this.value %}checked {% endif %}
      onchange="grr.forms.checkboxOnChange(this)"
      value='{{ this.value|escape }}'/>

  <abbr title='{{this.descriptor.description|escape}}'>
    {{this.friendly_name}}
  </abbr>
</label>

</div>
</div>
""")

  def ParseArgs(self, request):
    value = request.REQ.get(self.prefix)
    if value is None:
      return

    if value.lower() in ["yes", "true"]:
      return True

    return False


class RDFDatetimeFormRenderer(StringTypeFormRenderer):
  """Allow the user to enter a timestamp using the date and time pickers."""
  type = rdfvalue.RDFDatetime

  layout_template = ("""<div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}_picker' class="pickerIcon"/>

    <input id='{{this.prefix}}'
      type=text value='Click to set'
      onchange="grr.forms.inputOnChange(this)"
      class="unset hasDatepicker"/>

  </div>
</div>
""")

  def Layout(self, request, response):
    value = self.value or rdfvalue.RDFDatetime()
    self.date, self.time = str(value).split()

    # From now on we treat the RDFDatetime as a human readable string.
    if self.value is not None:
      self.value = str(self.value)

    self.default = str(self.default)

    response = super(RDFDatetimeFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "Layout", prefix=self.prefix)

  def ParseArgs(self, request):
    date = request.REQ.get(self.prefix)

    if date is None:
      return

    return rdfvalue.RDFDatetime().ParseFromHumanReadable(date)


class OptionFormRenderer(renderers.TemplateRenderer):
  """Renders the form for protobuf enums."""
  default = None
  friendly_name = "Select and option"
  help = "Please Select an option"
  option_name = "option"
  options = []

  layout_template = renderers.Template("""
<div class="control-group">
  <label class="control-label">
    <abbr title='{{this.help|escape}}'>
      {{this.friendly_name|escape}}
    </abbr>
  </label>

  <div class="controls">

  <select id="{{this.prefix}}-option" class="unset"
    onchange="grr.forms.inputOnChange(this)"
    >
    {% for name, description in this.options %}
     <option
       {% ifequal name this.default %}selected{% endifequal %}
       value="{{name|escape}}"
       >
         {{description|escape}}
         {% ifequal name this.default %} (default){% endifequal %}
     </option>
    {% endfor %}
  </select>
  </div>
</div>
""")

  def __init__(self, prefix="option", **kwargs):
    super(OptionFormRenderer, self).__init__(**kwargs)
    self.prefix = prefix

  def ParseOption(self, option, request):
    """Override this to parse the specific option selected."""

  def ParseArgs(self, request):
    option = request.REQ.get("%s-option" % self.prefix)
    return self.ParseOption(option, request)

  def RenderOption(self, option, request, response):
    """Extend this to render a different form for each option."""

  def Layout(self, request, response):
    super(OptionFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "OptionFormRenderer.Layout",
                               prefix=self.prefix)

  def RenderAjax(self, request, response):
    self.prefix = request.REQ.get("prefix", self.option_name)
    option = request.REQ.get(self.prefix + "-option", 1)

    self.RenderOption(option, request, response)


class MultiFormRenderer(renderers.TemplateRenderer):
  """Display multiple forms for the same base renderer.

  The different forms are distinguished by different prefixes.
  """

  # This renderer will be called for each new child.
  child_renderer = renderers.TemplateRenderer
  option_name = "option"
  button_text = "Add Option"

  layout_template = renderers.Template("""
{% if this.item %}

<button type=button class=close data-dismiss="alert">x</button>

<form id='{{unique}}' class='OptionList well well-large form-horizontal'
  data-item='{{this.item|escape}}'
  >

  {{this.item_type_selector|safe}}
  <div id='{{unique}}-{{this.item|escape}}' />
</form>

{% else %}
<button class="btn" id="AddButton{{unique}}" data-item_count=0 >
 {{this.button_text|escape}}
</button>
{% endif %}
""")

  def ParseArgs(self, request):
    """Pareses all children for the request."""
    result = []
    count = int(request.REQ.get("%s_count" % self.option_name, 0))
    for item in range(count):
      parsed_item = self.child_renderer(
          prefix="%s_%s" % (self.option_name, item)).ParseArgs(request)
      if parsed_item is not None:
        result.append(parsed_item)

    return result

  def Layout(self, request, response):
    self.item = request.REQ.get("item")
    if self.item is not None:
      self.item_type_selector = self.child_renderer(
          prefix="%s_%s" % (self.option_name, self.item)).RawHTML(request)
    else:
      self.CallJavascript(response, "MultiFormRenderer.Layout",
                          option=self.option_name)

    return super(MultiFormRenderer, self).Layout(request, response)


class MultiSelectListRenderer(RepeatedFieldFormRenderer):
  """Renderer for choosing multiple options from a list.

  Set self.values to the list of things that should be rendered.
  """
  type_descriptor = None
  type = None
  values = []

  layout_template = ("""<div class="control-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <select id='{{this.prefix}}' multiple
      onchange="grr.forms.inputOnChange(this)">
      {% for val in this.values %}
        <option value='{{val|escape}}'>{{val|escape}}
        </option>
      {% endfor %}
    </select>
  </div>
</div>
<script>
  // Height hack as CSS isn't handled properly for multiselect.
  var multiselect_height = parseInt($("#{{this.prefix}} option").length) * 15;
  $("#{{this.prefix}}").css("height", multiselect_height);
</script>
""")

  def ParseArgs(self, request):
    """Parse all the post parameters and build a list."""
    result = []
    for value in request.REQ.getlist("%s[]" % self.prefix):
      result.append(value)
    return result
