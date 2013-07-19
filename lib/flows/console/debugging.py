#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Debugging flows for the console."""

import getpass
import os
import pdb
import pickle
import tempfile
import time

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import worker


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
    if self.state.save_to:
      if not os.path.isdir(self.state.save_to):
        os.makedirs(self.state.save_to, 0700)
    self.CallClient(self.state.action, request=self.state.args,
                    next_state="Print")
    self.state.args = None

  @flow.StateHandler()
  def Print(self, responses):
    """Dump the responses to a pickle file or allow for breaking."""
    if not responses.success:
      self.Log("ClientAction %s failed. Staus: %s" % (self.state.action,
                                                      responses.status))

    if self.state.break_pdb:
      pdb.set_trace()
    if self.state.save_to:
      self._SaveResponses(responses)

  def _SaveResponses(self, responses):
    """Save responses to pickle files."""
    if responses:
      fd = None
      try:
        fdint, fname = tempfile.mkstemp(prefix="responses-",
                                        dir=self.state.save_to)
        fd = os.fdopen(fdint, "wb")
        pickle.dump(responses, fd)
        self.Log("Wrote %d responses to %s", len(responses), fname)
      finally:
        if fd: fd.close()


def StartFlowAndWait(client_id, flow_name, **kwargs):
  """Launches the flow and waits for it to complete.

  Args:
     client_id: The client common name we issue the request.
     flow_name: The name of the flow to launch.
     **kwargs: passthrough to flow.

  Returns:
     A GRRFlow object.
  """
  session_id = flow.GRRFlow.StartFlow(client_id, flow_name, **kwargs)
  while 1:
    time.sleep(1)
    flow_obj = aff4.FACTORY.Open(session_id)
    if not flow_obj.IsRunning():
      break

  return flow_obj


def StartFlowAndWorker(client_id, flow_name, **kwargs):
  """Launches the flow and worker and waits for it to finish.

  Args:
     client_id: The client common name we issue the request.
     flow_name: The name of the flow to launch.
     **kwargs: passthrough to flow.

  Returns:
     A GRRFlow object.

  Note: you need raw access to run this flow as it requires running a worker.
  """
  queue = rdfvalue.RDFURN("DEBUG-%s-" % getpass.getuser())
  session_id = flow.GRRFlow.StartFlow(client_id, flow_name, queue=queue,
                                      **kwargs)
  # Empty token, only works with raw access.
  worker_thrd = worker.GRRWorker(
      queue=queue, token=access_control.ACLToken(), threadpool_size=1,
      run_cron=False)
  while True:
    try:
      worker_thrd.RunOnce()
    except KeyboardInterrupt:
      print "exiting"
      worker_thrd.thread_pool.Join()
      break

    time.sleep(2)
    flow_obj = aff4.FACTORY.Open(session_id)
    if not flow_obj.IsRunning():
      break

  # Terminate the worker threads
  worker_thrd.thread_pool.Join()

  return flow_obj
