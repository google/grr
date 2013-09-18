#!/usr/bin/env python
"""This plugin adds artifact functionality to the UI."""


from grr.gui.plugins import forms
from grr.lib import artifact_lib
from grr.lib import rdfvalue


class ArtifactListRenderer(forms.MultiSelectListRenderer):
  """Renderer for listing the available Artifacts."""

  type = rdfvalue.ArtifactName

  def Layout(self, request, response):
    """Get available artifact information for display."""
    # Get all artifacts that aren't Bootstrap and aren't the base class.
    self.values = {}
    for arifact_name, artifact in artifact_lib.Artifact.classes.items():
      if artifact is not artifact_lib.Artifact.top_level_class:
        if set(["Bootstrap", "KnowledgeBase"]).isdisjoint(artifact.LABELS):
          self.values[arifact_name] = artifact
    super(ArtifactListRenderer, self).Layout(request, response)
