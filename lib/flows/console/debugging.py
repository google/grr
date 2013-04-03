#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Debugging flows for the console."""


import os
import pdb
import pickle
import tempfile

from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info


class ClientAction(flow.GRRFlow):
  """A Simple flow to execute any client action."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="action",
          description="The action to execute."),
      type_info.String(
          name="save_to",
          default="/tmp",
          description=("If not None, interpreted as an path to write pickle "
                       "dumps of responses to.")),
      type_info.Bool(
          name="break_pdb",
          description="If True, run pdb.set_trace when responses come back.",
          default=False),
      type_info.RDFValueType(
          description="Client action arguments.",
          name="args",
          rdfclass=rdfvalue.RDFValue),
      )

  @flow.StateHandler(next_state="Print")
  def Start(self):
    if self.save_to:
      if not os.path.isdir(self.save_to):
        os.makedirs(self.save_to, 0700)
    self.CallClient(self.action, request=self.args, next_state="Print")
    self.args = None

  @flow.StateHandler()
  def Print(self, responses):
    """Dump the responses to a pickle file or allow for breaking."""
    if not responses.success:
      self.Log("ClientAction %s failed. Staus: %s" % (self.action,
                                                      responses.status))

    if self.break_pdb:
      pdb.set_trace()
    if self.save_to:
      self._SaveResponses(responses)

  def _SaveResponses(self, responses):
    """Save responses to pickle files."""
    if responses:
      fd = None
      try:
        fdint, fname = tempfile.mkstemp(prefix="responses-", dir=self.save_to)
        fd = os.fdopen(fdint, "wb")
        pickle.dump(responses, fd)
        self.Log("Wrote %d responses to %s", len(responses), fname)
      finally:
        if fd: fd.close()
