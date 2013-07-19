#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
# -*- mode: python; encoding: utf-8 -*-

"""Tests for artifacts."""




# Need to import artifacts so they get registered
# pylint: disable=unused-import
from grr.artifacts import win_artifacts
# pylint: enable=unused-import

from grr.lib import artifact
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.general import collectors


class FakeFlow(collectors.ArtifactCollectorFlow):
  """Fake flow object."""

  def __init__(self):
    self.state = rdfvalue.FlowState()
    self.state.Register("client", None)


class ArtifactTest(test_lib.GRRBaseTest):

  def testArtifactsValidate(self):
    """Check each artifact we have passes validation."""

    fake_flow = FakeFlow()
    for a_cls in artifact.Artifact.classes:
      if a_cls == "Artifact":
        continue    # Skip the base object.
      art = artifact.Artifact.classes[a_cls]
      art_obj = art(parent_flow=FakeFlow())
      art_obj.Validate()

    art_cls = artifact.Artifact.classes["ApplicationEventLog"]
    art_obj = art_cls(parent_flow=fake_flow)
    art_obj.LABELS.append("BadLabel")

    self.assertRaises(artifact.ArtifactDefinitionError, art_obj.Validate)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
