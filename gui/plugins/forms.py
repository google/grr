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


# A cache for GetTypeDescriptorRenderer(),
type_descriptor_cache = None


def GetTypeDescriptorRenderer(type_descriptor):
  """Return the TypeDescriptorRenderer responsible for the type_descriptor."""
  global type_descriptor_cache

  # Cache a mapping between type descriptors and their renderers for speed.
  if type_descriptor_cache is None:
    # Rebuild the cache on first access.
    cache = {}
    for renderer_cls in TypeDescriptorFormRenderer.classes.values():
      # A renderer can specify that it works on a type. This is used for nested
      # protobuf.
      delegate = getattr(renderer_cls, "type", None)

      # Or a generic type descriptor (i.e. all items of this type).
      if delegate is None:
        delegate = getattr(renderer_cls, "type_descriptor", None)

      if delegate:
        cache[delegate] = renderer_cls

    # Atomic setting to prevent races.
    type_descriptor_cache = cache

  # Try to find a renderer for this type descriptor's type:
  result = type_descriptor_cache.get(getattr(type_descriptor, "type", None))
  if result is None:
    result = type_descriptor_cache.get(type_descriptor.__class__)

  if result is None:
    result = StringTypeFormRenderer

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
  <div class="accordion" id="accordion{{unique}}">
    <div class="accordion-group">
      <div class="accordion-heading">
       <a class="accordion-toggle" data-toggle="collapse"
         data-parent="#accordion{{unique}}" href="#collapse{{unique}}">
         <div class="control-group">
           <div class="controls">
            Advanced...
           </div>
         </div>
      </a>
      </div>
      <div id="collapse{{unique}}" class="accordion-body collapse">
        <div class="accordion-inner">
          {% for form_element in this.advanced_elements %}
            {{form_element|safe}}
          {% endfor %}
        </div>
      </div>
    </div>
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
          kwargs["default"] = getattr(self.proto_obj, descriptor.name)

        type_renderer = GetTypeDescriptorRenderer(descriptor)(**kwargs)

        # Put the members which are labeled as advanced behind an advanced
        # button.
        if (rdfvalue.SemanticDescriptor.Labels.ADVANCED in descriptor.labels or
            "ADVANCED" in descriptor.labels):
          # Allow the type renderer to draw the form.
          self.advanced_elements.append(type_renderer.RawHTML(request))
        else:
          self.form_elements.append(type_renderer.RawHTML(request))

    return super(SemanticProtoFormRenderer, self).Layout(request, response)

  def ParseArgs(self, request):
    """Parse all the post parameters and build a new protobuf instance."""
    result = self.proto_obj

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
  <label class="control-label">
    <abbr title='{{this.descriptor.description|escape}}'>
      {{this.friendly_name}}
    </abbr>
  </label>
""")

  friendly_name = None

  def __init__(self, descriptor=None, prefix="v_", opened=False, default=None,
               container=None, **kwargs):
    """Create a new renderer for a type descriptor.

    Args:
      descriptor: The descriptor to use.

      prefix: The prefix of our args. We can set any args specifically for our
        own use by prepending them with this unique prefix.

      opened: If this is specified, we open all our children.
      default: Use this default value to initialize form elements.

      container: The container of this field.

      **kwargs: Passthrough to baseclass.
    """
    self.descriptor = descriptor
    self.opened = opened
    self.container = container
    self.default = default
    self.prefix = prefix
    super(TypeDescriptorFormRenderer, self).__init__(**kwargs)

  def Layout(self, request, response):
    self.friendly_name = (self.friendly_name or
                          self.descriptor.friendly_name or
                          self.descriptor.name)

    self.value = self.descriptor.GetDefault(container=self.container)
    if self.value is None:
      self.value = ""

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
      type=text value='{{ this.value|escape }}'
      onchange="grr.forms.inputOnChange(this)"
      class="unset"/>
  </div>
</div>
""")

  def Layout(self, request, response):
    super(StringTypeFormRenderer, self).Layout(request, response)
    if self.default is not None:
      self.CallJavascript(response, "StringTypeFormRenderer.Layout",
                          default=utils.SmartUnicode(self.default),
                          prefix=self.prefix)


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
     <ins class='fg-button ui-icon ui-icon-plus' id='{{unique|escape}}'
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
<script>
 // Mark the content as already fetched so we do not need to fetch again.
 $("#{{id|escapejs}}").addClass("Fetched");
</script>
""")

  def Layout(self, request, response):
    """Build the form elements for the nested protobuf."""
    default = self.descriptor.GetDefault(container=self.container)

    self.type_name = default.__class__.__name__

    if self.opened:
      delegated_renderer = SemanticProtoFormRenderer(
          default, opened=False, prefix=self.prefix)

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

    return renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.ajax_template)

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
<div class="accordion" id="accordion{{unique}}">
  <div class="accordion-group">
    <div class="accordion-heading">
      <button class="btn" id="add_{{unique}}"
       data-count=0
       data-prefix="{{this.prefix}}"
       >
      <img src="static/images/new.png"
       alt="Add {{this.descriptor.friendly_name}}" />
      </button>
    </div>
    <div id="collapse{{unique}}" class="accordion-body in">
      <div class="accordion-inner">
        <div id="content_{{unique}}" />
      </div>
    </div>
  </div>
</div>
<script>
$("button#add_{{unique}}").click(function (event) {
  var count = $(this).data("count") + 1;
  var new_id = 'content_{{unique}}_' + count;

  $(this).data("count", count);

  // Store the total count of members in the form.
  $(this).closest(".FormData").data()[
     "{{this.prefix}}_count"] = count;

  $("#content_{{unique}}").append('<div id="' + new_id + '"/>');

  grr.update("{{renderer}}", new_id, {
    'index': count,
    'prefix': "{{this.prefix}}",
    'owner': "{{this.owner}}",
    'field': "{{this.field}}",
  });

  event.preventDefault();
}).click();
</script>
""")

  ajax_template = renderers.Template("""
<div class="alert fade in" id="{{unique}}"
  data-index="{{this.index}}"
  data-prefix="{{this.prefix}}"
  >
  <button type=button class=close data-dismiss="alert">x</button>
  {{this.delegated|safe}}
</div>

<script>

$("#{{unique}}").on('close', function () {
  var data = $(this).data();

  grr.forms.clearPrefix(this, data.prefix + "-" + data.index + "-");
});

</script>
""")

  def Layout(self, request, response):
    """Build form elements for repeated fields."""
    self.index = 0
    self.delegate_prefix = self.prefix + "-%s-" % self.index
    self.owner = self.descriptor.owner.__name__
    self.field = self.descriptor.name

    delegate = self.descriptor.delegate
    delegate_renderer = GetTypeDescriptorRenderer(delegate)(
        descriptor=delegate, opened=True, container=self.container,
        prefix=self.delegate_prefix)

    self.delegated = delegate_renderer.RawHTML(request)
    self.delegate_name = delegate.__class__.__name__

    return super(RepeatedFieldFormRenderer, self).Layout(request, response)

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
        prefix=self.delegate_prefix)

    self.delegated = delegated_renderer.RawHTML(request)

    return super(RepeatedFieldFormRenderer, self).RenderAjax(
        request, response)


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
 <option {% ifequal enum_value this.value %}selected{% endifequal %}
   value="{{enum_value|escape}}">
   {{enum_name|escape}}
   {% ifequal enum_value this.value %} (default){% endifequal %}
 </option>
{% endfor %}
</select>
</div>
</div>
"""

  def Layout(self, request, response):
    self.items = sorted(self.descriptor.enum.items(), key=lambda x: x[1])
    return super(EnumFormRenderer, self).Layout(request, response)


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
<script>
 $('#{{this.prefix}}_picker').datepicker({
   showAnim: '',
   changeMonth: true,
   changeYear: true,
   showOn: "button",
   buttonImage: "static/images/clock.png",
   buttonImageOnly: true,
   altField: "#{{this.prefix}}",
 });
</script>
""")

  def Layout(self, request, response):
    now = rdfvalue.RDFDatetime()
    self.date, self.time = str(now).split()

    return super(RDFDatetimeFormRenderer, self).Layout(request, response)

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
