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
from grr.lib.rdfvalues import structs as rdf_structs

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

      if delegate:
        # Repeated form renderers go in their own cache.
        if utils.issubclass(renderer_cls, RepeatedFieldFormRenderer):
          repeated_renderer_cache[delegate] = renderer_cls

        else:
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
    <div class="form-group col-sm-12">
      <label class="control-label">
        <a id="advanced_label_{{unique|escape}}"
          class="advanced-label">Advanced</a>
        <i class="advanced-icon glyphicon glyphicon-chevron-right"></i>
      </label>
    </div>
    <div class="clearfix"></div>
    <div class="hide advanced-controls"
      id="advanced_controls_{{unique|escape}}">
      {% for form_element in this.advanced_elements %}
        {{form_element|safe}}
      {% endfor %}
    </div>
  {% endif %}
</div>
""")

  def __init__(self,
               proto_obj=None,
               prefix="v_",
               supressions=None,
               opened=True,
               **kwargs):
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
      if (rdf_structs.SemanticDescriptor.Labels.HIDDEN not in descriptor.labels
          and "HIDDEN" not in descriptor.labels):
        kwargs = dict(descriptor=descriptor,
                      opened=self.opened,
                      container=self.proto_obj,
                      prefix=self.prefix + "-" + descriptor.name)

        if self.proto_obj.HasField(descriptor.name):
          kwargs["value"] = getattr(self.proto_obj, descriptor.name)

        type_renderer = GetTypeDescriptorRenderer(descriptor)(**kwargs)

        # Put the members which are labeled as advanced behind an advanced
        # button.
        if (rdf_structs.SemanticDescriptor.Labels.ADVANCED in descriptor.labels
            or "ADVANCED" in descriptor.labels):
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

      # Recover the type descriptor renderer for this field.
      descriptor = self.descriptors.get(field)
      if descriptor is None:
        continue

      type_renderer = GetTypeDescriptorRenderer(descriptor)(
          descriptor=descriptor,
          container=self.proto_obj,
          prefix=self.prefix + "-" + descriptor.name)

      # Delegate the arg parsing to the type descriptor renderer and set it
      # into the protobuf.
      result.Set(field, type_renderer.ParseArgs(request))

    return result


class TypeDescriptorFormRenderer(renderers.TemplateRenderer):
  """A renderer for a type descriptor form."""

  # This should be set to the type descriptor class we are responsible for.
  type_descriptor = None

  context_help_url = None

  # This is the default view of the description.
  default_description_view = renderers.Template("""
  {% if this.render_label %}
  <label class="control-label">
    <abbr title='{{this.descriptor.description|escape}}'>
      {{this.friendly_name}}
    </abbr>
  {% if this.context_help_url %}
    <a href="/help/{{this.context_help_url|escape}}" target="_blank">
    <i class="glyphicon glyphicon-question-sign"></i></a>
  {% endif %}
  </label>
  {% endif %}
""")

  friendly_name = None

  def __init__(self,
               descriptor=None,
               prefix="v_",
               opened=False,
               default=None,
               value=None,
               container=None,
               render_label=True,
               **kwargs):
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
    self.friendly_name = (self.friendly_name or self.descriptor.friendly_name or
                          self.descriptor.name)

    return super(TypeDescriptorFormRenderer, self).Layout(request, response)

  def ParseArgs(self, request):
    result = request.REQ.get(self.prefix)
    if result is not None:
      return result


class StringTypeFormRenderer(TypeDescriptorFormRenderer):
  """String form element renderer."""
  type_descriptor = type_info.ProtoString

  layout_template = ("""<div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text
{% if this.default %}
  value='{{ this.default|escape }}'
{% endif %}
      onchange="grr.forms.inputOnChange(this)"
      class="form-control unset"/>
  </div>
</div>
""")

  def Layout(self, request, response):
    super(StringTypeFormRenderer, self).Layout(request, response)
    parameters = dict(default=self.default, prefix=self.prefix)
    if self.value:
      parameters["value"] = utils.SmartUnicode(self.value)

    return self.CallJavascript(response, "StringTypeFormRenderer.Layout",
                               **parameters)


class BinaryStringTypeFormRenderer(StringTypeFormRenderer):
  """Binary string form element renderer."""

  type_descriptor = type_info.ProtoBinary

  def ParseArgs(self, request):
    res = super(BinaryStringTypeFormRenderer, self).ParseArgs(request)
    return res.decode("string_escape")


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

  layout_template = ("""<div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
   <div class='nested_opener'>
{% if this.opened %}
     {{this.prefetched|safe}}
{% else %}
     <i class='nested-icon glyphicon glyphicon-plus' id='{{unique|escape}}'
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
      delegated_renderer = SemanticProtoFormRenderer(proto_obj=self.value or
                                                     self.default,
                                                     opened=False,
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
        self, request,
        response, apply_template=self.ajax_template)
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
          descriptor=descriptor,
          container=self.container,
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

  # If True, will add one element on the first show.
  add_element_on_first_show = True

  layout_template = renderers.Template("""
  <div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
    <div class="controls">
      <button class="btn btn-default form-add" id="add_{{unique|escape}}"
        data-count="{{this.default_data_count|escape}}"
        data-prefix="{{this.prefix|escape}}">
        <i class="glyphicon glyphicon-plus"></i>
      </button>
    </div>
  </div>
  <div id="content_{{unique}}">
{{this.content|safe}}
  </div>
""")

  ajax_template = renderers.Template("""
<button type=button class="control-label close"
  id="remove_{{unique|escapejs}}">x</button>
<div class="form-group" id="{{unique|escapejs}}"
  data-index="{{this.index}}" data-prefix="{{this.prefix}}">

  {{this.delegated|safe}}
</div>
""")

  @property
  def default_data_count(self):
    if self.add_element_on_first_show:
      return 1
    else:
      return 0

  def Layout(self, request, response):
    """Build form elements for repeated fields."""
    self.owner = self.descriptor.owner.__name__
    self.field = self.descriptor.name

    parameters = dict(owner=self.descriptor.owner.__name__,
                      field=self.descriptor.name,
                      prefix=self.prefix,
                      index=0)
    request.REQ.update(parameters)

    if self.add_element_on_first_show:
      self.content = self.RawHTML(request, method=self.RenderAjax)
    else:
      self.content = ""

    response = super(RepeatedFieldFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "RepeatedFieldFormRenderer.Layout",
                               **parameters)

  def ParseArgs(self, request):
    """Parse repeated fields from post parameters."""
    result = []

    # The form tells us how many items there should be. Note that they can be
    # sparse since when an item is removed, the count is not decremented.
    count = int(request.REQ.get("%s_count" % self.prefix,
                                self.default_data_count))

    # Parse out the items and fill them into the result. Note that we do not
    # support appending empty repeated fields. Such fields may happen by adding
    # and removing the form for the repeated member.
    for index in range(count):
      delegate_prefix = "%s-%s" % (self.prefix, index)
      delegate = self.descriptor.delegate
      delegate_renderer = GetTypeDescriptorRenderer(delegate)(
          descriptor=delegate,
          opened=True,
          container=self.container,
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

    try:
      value = self.value[self.index]
    except (TypeError, IndexError):
      value = None

    delegated_renderer = GetTypeDescriptorRenderer(delegate)(
        descriptor=delegate,
        opened=True,
        container=self.container,
        prefix=self.delegate_prefix,
        render_label=False,
        value=value)

    self.delegated = delegated_renderer.RawHTML(request)

    response = super(RepeatedFieldFormRenderer, self).RenderAjax(request,
                                                                 response)
    return self.CallJavascript(response, "RepeatedFieldFormRenderer.RenderAjax")


class EnumFormRenderer(TypeDescriptorFormRenderer):
  """Renders the form for protobuf enums."""

  type_descriptor = type_info.ProtoEnum

  layout_template = """<div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
<div class="controls">

<select id="{{this.prefix}}" class="form-control unset"
  onchange="grr.forms.inputOnChange(this)"
  >
{% for enum_name in this.items %}
 <option {% ifequal enum_name this.default %}selected{% endifequal %}
   value="{{enum_name|escape}}">
   {{enum_name|escape}}{% ifequal enum_name this.default %} (default)
                       {% endifequal %}
 </option>
{% endfor %}
</select>
</div>
</div>
"""

  def Layout(self, request, response):
    enum_dict = dict(self.descriptor.enum.items())
    self.items = sorted(enum_dict.keys(), key=lambda k: enum_dict[k])
    super(EnumFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "Layout",
                               default=self.default,
                               value=self.value,
                               prefix=self.prefix)


class ProtoBoolFormRenderer(TypeDescriptorFormRenderer):
  """Render a checkbox for boolean values."""
  type_descriptor = type_info.ProtoBoolean

  layout_template = renderers.Template("""
<div class="form-group">
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

  def Layout(self, request, response):
    super(ProtoBoolFormRenderer, self).Layout(request, response)
    if self.default is not None:
      self.default = bool(self.default)
    if self.value is not None:
      self.value = bool(self.default)

    return self.CallJavascript(response,
                               "Layout",
                               default=self.default,
                               value=self.value,
                               prefix=self.prefix)

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

  layout_template = ("""<div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text value='Click to set'
      onchange="grr.forms.inputOnChange(this)"
      class="pull-left form-control unset hasDatepicker"
    />
    <input id='{{this.prefix}}_picker' class="pickerIcon"/>
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
    return self.CallJavascript(response,
                               "RDFDatetimeFormRenderer.Layout",
                               prefix=self.prefix)

  def ParseArgs(self, request):
    date = request.REQ.get(self.prefix)

    if date is None:
      return

    return rdfvalue.RDFDatetime().ParseFromHumanReadable(date)


class OptionFormRenderer(TypeDescriptorFormRenderer):
  """Renders the form for protobuf enums."""
  default = None
  friendly_name = "Select and option"
  help = "Please Select an option"
  option_name = "option"
  options = []

  layout_template = renderers.Template("""
<div class="form-group">
""" + TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <div class="OptionList well well-large">

      <label class="control-label">
        <abbr title='{{this.help|escape}}'>
          {{this.friendly_name|escape}}
        </abbr>
      </label>

      <div class="controls" style="margin-bottom: 1em">
        <select id="{{this.prefix|escape}}-option" class="form-control unset"
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

      <div id='{{unique|escape}}-option-form'></div>

    </div>
  </div>

</div>
""")

  def __init__(self,
               prefix="option",
               default_item_type=None,
               render_label=False,
               **kwargs):
    """Constructor.

    Args:
      prefix: Id of the select control will be [prefix]-option. Having
              different prefixes allows one to have multiple
              OptionFormRenderers on the same page.
      default_item_type: Item type of the option item that will be selected
                         by default.
      render_label: If True, will render the label for this field.
      **kwargs: passthrough to baseclass.
    """
    super(OptionFormRenderer, self).__init__(render_label=render_label,
                                             **kwargs)
    self.prefix = prefix
    self.default_item_type = default_item_type

  def ParseOption(self, option, request):
    """Override this to parse the specific option selected."""

  def ParseArgs(self, request):
    option = request.REQ.get("%s-option" % self.prefix)
    if option:
      return self.ParseOption(option, request)

  def RenderOption(self, option, request, response):
    """Extend this to render a different form for each option."""

  def Layout(self, request, response):
    super(OptionFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "OptionFormRenderer.Layout",
                               prefix=self.prefix,
                               default_item_type=self.default_item_type)

  def RenderAjax(self, request, response):
    self.prefix = request.REQ.get("prefix", self.option_name)
    option = request.REQ.get(self.prefix + "-option", None)

    self.RenderOption(option, request, response)


class MultiFormRenderer(renderers.TemplateRenderer):
  """Display multiple forms for the same base renderer.

  The different forms are distinguished by different prefixes.
  """

  # This renderer will be called for each new child.
  child_renderer = renderers.TemplateRenderer
  option_name = "option"
  button_text = "Add Option"
  # If this is true, adds one default form when rendering. Useful when you
  # don't want the list of forms to be empty.
  add_one_default = True

  layout_template = renderers.Template("""
{% if this.item %}

<button id="RemoveButton{{unique}}" type=button class=close
  data-dismiss="alert">x</button>
{{this.child|safe}}
{% else %}
<button class="btn btn-default" id="AddButton{{unique}}" data-item_count=0 >
 {{this.button_text|escape}}
</button>
{% endif %}
""")

  def ParseArgs(self, request):
    """Pareses all children for the request."""
    result = []
    count = int(request.REQ.get("%s_count" % self.option_name, 0))
    for item in range(count):
      parsed_item = self.child_renderer(prefix="%s_%s" %
                                        (self.option_name, item),
                                        item=item).ParseArgs(request)
      if parsed_item is not None:
        result.append(parsed_item)

    return result

  def Layout(self, request, response):
    """Renders given item's form. Calls Layout() js code if no item is given."""
    self.item = request.REQ.get("item")
    default_item_type = request.REQ.get("default_item_type", None)

    if self.item is not None:
      self.child = self.child_renderer(
          prefix="%s_%s" % (self.option_name, self.item),
          item=self.item,
          default_item_type=default_item_type).RawHTML(request)

      self.CallJavascript(response,
                          "MultiFormRenderer.LayoutItem",
                          option=self.option_name)
    else:
      self.CallJavascript(response,
                          "MultiFormRenderer.Layout",
                          option=self.option_name,
                          add_one_default=self.add_one_default)

    return super(MultiFormRenderer, self).Layout(request, response)


class MultiSelectListRenderer(RepeatedFieldFormRenderer):
  """Renderer for choosing multiple options from a list.

  Set self.values to the list of things that should be rendered.
  """
  type_descriptor = None
  type = None
  values = []

  layout_template = ("""<div class="form-group">
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
""")

  def Layout(self, request, response):
    response = super(MultiSelectListRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "MultiSelectListRenderer.Layout",
                               prefix=self.prefix)

  def ParseArgs(self, request):
    """Parse all the post parameters and build a list."""
    result = []
    for k, v in request.REQ.iteritems():
      if k.startswith(self.prefix):
        result.append(v)

    return result


class UnionMultiFormRenderer(OptionFormRenderer):
  """Renderer that renders union-style RDFValues.

  Certain RDFValues have union-like semantics. I.e. they are essentially
  selectors of a number of predefined other protobufs. There's a single
  field that identifies the type of the selected "subvalue" and then
  nested rdfvalues corresponding to different selections. For examples:

  message FileFinderFilter {
    enum Type {
      MODIFICATION_TIME = 0 [(description) = "Modification time"];
      ACCESS_TIME = 1 [(description) = "Access time"];
    }

    optional Type filter_type = 1;
    optional FileFinderModificationTimeFilter modification_time = 2;
    optional FileFinderAccessTimeFilter access_time = 3;
  }

  UnionMultiFormRenderer renders this kind of rdfvalues. Field specified in
  union_by_field is used to determine available values. union_by_field
  field has to be Enum. Corresponding nested values have to have names
  equal to enum values' names, but in lower case.

  Renderer renders a dropdown with a type selector and renders a form
  corresponding to a currently selected type.
  """
  union_by_field = None

  def __init__(self, render_label=True, **kwargs):
    super(UnionMultiFormRenderer, self).__init__(render_label=render_label,
                                                 **kwargs)
    union_field_enum = self.type.type_infos.get(self.union_by_field)

    self.friendly_name = union_field_enum.friendly_name
    self.option_name = union_field_enum.name
    self.help = union_field_enum.description

    self.options = []
    for name, value in sorted(union_field_enum.enum.iteritems(),
                              key=lambda x: int(x[1])):
      self.options.append((int(value), value.description or name))

  def ParseOption(self, option, request):
    union_field_enum = self.type.type_infos.get(self.union_by_field)
    union_field_value = union_field_enum.reverse_enum[int(option)]

    result = self.type()
    setattr(result, self.union_by_field, union_field_value)

    union_field_name = union_field_enum.reverse_enum[int(option)].lower()
    if hasattr(result, union_field_name):
      setattr(result,
              union_field_name,
              SemanticProtoFormRenderer(
                  getattr(result, union_field_name),
                  id=self.id,
                  prefix=self.prefix).ParseArgs(request))
    return result

  def RenderOption(self, option, request, response):
    result = self.type()
    union_field_enum = self.type.type_infos.get(self.union_by_field)
    union_field_name = union_field_enum.reverse_enum[int(option)].lower()
    if hasattr(result, union_field_name):
      SemanticProtoFormRenderer(
          getattr(result, union_field_name),
          id=self.id,
          prefix=self.prefix).Layout(request, response)
