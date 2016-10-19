#!/usr/bin/env python
"""This file contains specialized renderers for semantic values.

Other files may also contain specialized renderers for semantic types relevant
to their function, but here we include the most basic and common renderers.
"""


from grr.gui import renderers
from grr.lib import aff4
from grr.lib import utils


def FindRendererForObject(rdf_obj):
  """Find the appropriate renderer for an RDFValue object."""

  # Default renderer.
  return ValueRenderer(rdf_obj)


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
    self.rendered_value = utils.SmartStr(self.proxy)

    return super(ValueRenderer, self).Layout(request, response)
