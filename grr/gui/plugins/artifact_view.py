#!/usr/bin/env python
"""This plugin adds artifact functionality to the UI."""

from grr.gui import renderers
from grr.gui.plugins import forms
from grr.gui.plugins import semantic
from grr.lib import artifact_registry
from grr.lib import parsers


class ArtifactListRenderer(forms.MultiSelectListRenderer):
  """Renderer for listing the available Artifacts."""

  type = artifact_registry.ArtifactName

  artifact_template = ("""
          <div id='{{unique|escape}}_artifact_description'>
            <h4><div name='artifact_name'/></h4>
            <div name='artifact_description'/>
            <table>
              <tr><td>Labels<td><div name='artifact_labels'/></tr>
              <tr><td>Platforms<td><div name='artifact_supported_os'/></tr>
              <tr><td>Conditions<td><div name='artifact_conditions'/></tr>
              <tr><td>Dependencies<td><div name='artifact_dependencies'/></tr>
              <tr><td>Links<td><div name='artifact_links'/></tr>
              <tr><td>Output Type<td><div name='artifact_output_type'/></tr>
            </table>
            <h5>Artifact Sources</h5>
            <table name='artifact_sources'>
              <tbody></tbody>
            </table>
            <h5>Artifact Processors</h5>
            <table name='artifact_processors'>
              <tbody></tbody>
            </table>
          </div>""")

  layout_template = (
      """<div class="form-group">""" +
      forms.TypeDescriptorFormRenderer.default_description_view + """
  <div id='{{unique|escape}}_artifact_renderer' class="controls">
  <div>
    <table class='artifact_table'>
      <tr>
        <td>
          <input id='{{unique|escape}}_search'
            placeholder="Search"></input><br>
          <select id='{{unique|escape}}_os_filter'
            placeholder="OS Filter"></input>
        <td>
        <td>
      </tr>
      <tr>
        <td class="artifact_table">
          <select id='{{unique|escape}}_artifact_list' class='artifact_list'
            multiple />
        <td class="artifact_table">
          <select id='{{this.prefix|escape}}' class='artifact_list' multiple/>
        <td class="artifact_table">""" + artifact_template + """
      </tr>
      <tr>
        <td>
          <a id='{{unique|escape}}_artifact_add'>Add</a>
          <a id='{{unique|escape}}_artifact_add_all'
            class='pull-right'>Add all  </a>
        <td>
          <a id='{{unique|escape}}_select_clear'>Clear</a>
          <a id='{{unique|escape}}_select_remove'
            class='pull-right'>Remove  </a>
        <td>
      </tr>
    </table>
  </div>
  </div>

</div>
""")

  def Layout(self, request, response):
    """Get available artifact information for display."""
    # Get all artifacts that aren't Bootstrap and aren't the base class.
    self.labels = artifact_registry.Artifact.ARTIFACT_LABELS
    artifact_dict = {}

    # Convert artifacts into a dict usable from javascript.
    for art in artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True):
      if "Bootstrap" in art.labels:
        continue

      art_dict = art.ToExtendedDict()
      # We don't use art.name here since it isn't JSON serializable, the name
      # inside the extended dict has already been converted, so use that.
      art_name = art_dict["name"]
      artifact_dict[art_name] = art_dict
      processors = []
      for processor in parsers.Parser.GetClassesByArtifact(art_name):
        processors.append({"name": processor.__name__,
                           "output_types": processor.output_types,
                           "doc": processor.GetDescription()})
      artifact_dict[art_name]["processors"] = processors

    # Skip the our parent and call the TypeDescriptorFormRenderer direct.
    response = renderers.TypeDescriptorFormRenderer.Layout(self, request,
                                                           response)
    return self.CallJavascript(
        response,
        "ArtifactListRenderer.Layout",
        prefix=self.prefix,
        artifacts=artifact_dict,
        labels=self.labels,
        supported_os=artifact_registry.Artifact.SUPPORTED_OS_LIST)


class ArtifactRDFValueRenderer(semantic.RDFValueRenderer):
  """A special renderer for ArtifactRDFValues."""

  classname = "Artifact"

  layout_template = renderers.Template("""
<div id={{unique|escape}}_artifact_description>""" + ArtifactListRenderer.
                                       artifact_template + """
</div>
""")

  def Layout(self, request, response):
    self.artifact_str = self.proxy.ToPrettyJson()
    response = super(ArtifactRDFValueRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "ArtifactRDFValueRenderer.Layout",
                               artifact_str=self.artifact_str)


class ArtifactRawRDFValueRenderer(semantic.RDFValueRenderer):
  """A renderer for showing JSON format for ArtifactRDFValues."""

  classname = "Artifact"

  layout_template = renderers.Template(
      "<pre>{{this.artifact_str|escape}}</pre>")

  def Layout(self, request, response):
    self.artifact_str = self.proxy.ToPrettyJson(extended=True)
    super(ArtifactRawRDFValueRenderer, self).Layout(request, response)


class ArtifactManagerView(renderers.AngularDirectiveRenderer):
  """Artifact Manager table with toolbar."""

  description = "Artifact Manager"
  behaviours = frozenset(["Configuration"])
  order = 50

  directive = "grr-artifact-manager-view"
