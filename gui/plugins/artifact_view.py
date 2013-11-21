#!/usr/bin/env python
"""This plugin adds artifact functionality to the UI."""

from grr.gui import renderers
from grr.gui.plugins import forms
from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue


class ArtifactListRenderer(forms.MultiSelectListRenderer):
  """Renderer for listing the available Artifacts."""

  type = rdfvalue.ArtifactName

  layout_template = ("""<div class="control-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
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
        <td>
          <select id='{{unique|escape}}_artifact_list' class='artifact_list'
            multiple />
        <td>
          <select id='{{this.prefix|escape}}' class='artifact_list' multiple/>
        <td>
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
            <h5>Artifact Collectors</h5>
            <table name='artifact_collectors'>
              <tbody></tbody>
            </table>
            <h5>Artifact Processors</h5>
            <table name='artifact_processors'>
              <tbody></tbody>
            </table>
          </div>
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
    self.artifacts = {}
    for arifact_name, artifact in artifact_lib.Artifact.classes.items():
      if artifact is not artifact_lib.Artifact.top_level_class:
        if set(["Bootstrap"]).isdisjoint(artifact.LABELS):
          self.artifacts[arifact_name] = artifact
    self.labels = artifact_lib.ARTIFACT_LABELS

    # Convert artifacts into a dict usable from javascript.
    artifact_dict = {}
    for artifact_name, artifact in self.artifacts.items():
      processors = []
      for processor in parsers.Parser.GetClassesByArtifact(artifact_name):
        processors.append({"name": processor.__name__,
                           "output_types": processor.output_types,
                           "description": processor.GetDescription()})
      collectors = []
      for collector in artifact.COLLECTORS:
        collectors.append({"action": collector.action,
                           "args": collector.args})
      artifact_dict[artifact_name] = {
          "labels": artifact.LABELS or ["None"],
          "description": artifact.GetDescription(),
          "short_description": artifact.GetShortDescription(),
          "conditions": [c.__name__ for c in artifact.CONDITIONS] or ["None"],
          "dependencies": ([str(c) for c in
                            artifact.GetArtifactPathDependencies()]
                           or ["None"]),
          "supported_os": artifact.SUPPORTED_OS or ["All"],
          "output_type": artifact.GetOutputType(),
          "processors": processors,
          "links": artifact.URLS,
          "collectors": collectors,
          }

    # Skip the our parent and call the TypeDescriptorFormRenderer direct.
    response = renderers.TypeDescriptorFormRenderer.Layout(self, request,
                                                           response)
    return self.CallJavascript(response, "ArtifactListRenderer.Layout",
                               prefix=self.prefix,
                               artifacts=artifact_dict,
                               supported_os=artifact_lib.SUPPORTED_OS_LIST,
                               labels=self.labels)
