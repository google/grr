#!/usr/bin/env python
"""This is a test component."""

from grr.client import actions
from grr.lib.rdfvalues import client as rdf_client


class TestComponentAction(actions.ActionPlugin):
  in_rdfvalue = rdf_client.ListDirRequest
  out_rdfvalues = [rdf_client.StatEntry]

  def Run(self, args):
    print args

    self.SendReply(symlink="I am a symlink")
