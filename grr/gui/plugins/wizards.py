#!/usr/bin/env python
"""Implementation of an interactive wizard widget."""
from grr.gui import renderers
from grr.gui.plugins import forms
from grr.lib import aff4


class WizardRenderer(renderers.TemplateRenderer):
  """This renderer creates a wizard."""

  render_as_modal = True
  current_page = 0

  # WizardPage objects that defined this wizard's behaviour.
  title = ""
  pages = []

  # This will be used for identifying the wizard when publishing the events.
  wizard_name = "wizard"

  layout_template = renderers.Template("""
<div id="Wizard_{{unique|escape}}"
  class="Wizard{% if this.render_as_modal %} modal-dialog{% endif %} FormData"
  data-current='{{this.current_page|escape}}'
  data-max_page='{{this.max_pages|escape}}'
  >
{% if this.render_as_modal %}<div class="modal-content">{% endif %}

{% for i, page, page_cls, page_renderer in this.raw_pages %}
  <div id="Page_{{i|escape}}" class="WizardPage"
   data-renderer="{{page_renderer|escape}}"
   style="display: none">
    <div class="WizardBar modal-header">
      <button type="button" class="close" data-dismiss="modal"
        aria-hidden="true">x</button>
      <h3>{{this.title|escape}} -
        <span class="Description">
         {{page_cls.description|escape}}
        </span>
      </h3>
    </div>

    <div class="modal-body">
     {{page|safe}}
    </div>
  </div>
{% endfor %}

  <div class="modal-footer navbar-inner">
    <ul class="nav pull-left">
      <div id="Message{{unique}}"/>
      <div class="navbar-text" id="footer_message_{{unique}}"></div>
    </ul>
    <ul class="nav nav pull-right">
      <button class="btn btn-default Back" style='display: none'>Back</button>
      <button class="btn btn-primary Next">Next</button>
      <button class="btn btn-primary Finish" style='display: none'
        data-dismiss="modal"
      >
        Finish
      </button>
    </ul>
  </div>

{% if this.render_as_modal %}</div>{% endif %}
</div>
""")

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    self.raw_pages = []
    for i, page_cls in enumerate(self.pages):
      # Make the page renderers dump all their data to the wizard DOM node.
      page_renderer = page_cls(id="Page_%d" % i)
      self.raw_pages.append((i, page_renderer.RawHTML(request), page_cls,
                             page_cls.__name__))

    self.max_pages = len(self.pages) - 1
    super(WizardRenderer, self).Layout(request, response)

    return self.CallJavascript(response, "WizardRenderer.Layout")


class AFF4AttributeFormRenderer(forms.TypeDescriptorFormRenderer):
  """A renderer for AFF4 attribute forms."""

  type = aff4.AFF4Attribute

  layout_template = """<div class="form-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
<div class="controls">

<select id="{{this.prefix}}" class="unset"
  onchange="grr.forms.inputOnChange(this)"
  >
{% for name in this.attributes %}
 {% if name %}
   <option {% ifequal name this.value %}selected{% endifequal %}
     value="{{name|escape}}">
     {{name|escape}}
     {% ifequal name this.value %} (default){% endifequal %}
   </option>
 {% endif %}
{% endfor %}
</select>
</div>
</div>
"""

  def __init__(self, **kwargs):
    super(AFF4AttributeFormRenderer, self).__init__(**kwargs)
    self.attributes = ["Unset"]
    self.attributes.extend(sorted(aff4.Attribute.NAMES.keys()))
