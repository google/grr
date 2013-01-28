#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Debugging flows for the console."""


import os
import pdb
import pickle
import tempfile

from grr.lib import flow


class ClientAction(flow.GRRFlow):
  """A Simple flow to execute any client action."""

  # TODO(user): add flow_typeinfo definition.

  def __init__(self, action=None, save_to="/tmp",
               break_pdb=False, args=None, **kwargs):
    """Launch the action on the client.

    Args:
       action: The name of the action on the client.
       save_to: If not None, interpreted as an path to write pickle
           dumps of responses to.
       break_pdb: If True run pdb.set_trace when the responses come back.
       args: passthrough.
    """
    if not action:
      raise flow.FlowError("No action supplied.")
    self.save_to = save_to
    if self.save_to:
      if not os.path.isdir(save_to):
        os.makedirs(save_to, 0700)
    self.break_pdb = break_pdb
    self.action = action
    self.args = args

    super(ClientAction, self).__init__(**kwargs)

  @flow.StateHandler(next_state="Print")
  def Start(self):
    self.CallClient(self.action, self.args, next_state="Print")
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
