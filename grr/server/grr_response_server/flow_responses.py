#!/usr/bin/env python
"""The class encapsulating flow responses."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import operator

from grr_response_core.lib import queues
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import data_store
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class Responses(object):
  """An object encapsulating all the responses to a request."""

  def __init__(self):
    self.status = None
    self.success = True
    self.request = None
    self.responses = []

  @classmethod
  def FromResponses(cls, request=None, responses=None):
    """Creates a Responses object from new style flow request and responses."""
    res = cls()
    res.request = request
    if request:
      res.request_data = request.request_data

    for r in responses or []:
      if isinstance(r, rdf_flow_objects.FlowResponse):
        res.responses.append(r.payload)
      elif isinstance(r, rdf_flow_objects.FlowStatus):
        res.status = r
        res.success = r.status == "OK"
      elif isinstance(r, rdf_flow_objects.FlowIterator):
        pass
      else:
        raise TypeError("Got unexpected response type: %s" % type(r))
    return res

  @classmethod
  def FromLegacyResponses(cls, request=None, responses=None):
    """Creates a Responses object from old style flow request and responses."""
    res = cls()
    res.request = request
    if request:
      res.request_data = rdf_protodict.Dict(request.data)
    dropped_responses = []
    # The iterator that was returned as part of these responses. This should
    # be passed back to actions that expect an iterator.
    res.iterator = None

    if not responses:
      return res

    # This may not be needed if we can assume that responses are
    # returned in lexical order from the data_store.
    responses.sort(key=operator.attrgetter("response_id"))

    if request.HasField("request"):
      client_action_name = request.request.name
      action_registry = server_stubs.ClientActionStub.classes
      if client_action_name not in action_registry:
        raise RuntimeError(
            "Got unknown client action: %s." % client_action_name)
      expected_response_classes = action_registry[
          client_action_name].out_rdfvalues

    old_response_id = None

    # Filter the responses by authorized states
    for msg in responses:
      # Check if the message is authenticated correctly.
      if msg.auth_state != msg.AuthorizationState.AUTHENTICATED:
        logging.warning("%s: Messages must be authenticated (Auth state %s)",
                        msg.session_id, msg.auth_state)
        dropped_responses.append(msg)
        # Skip this message - it is invalid
        continue

      # Handle retransmissions
      if msg.response_id == old_response_id:
        continue

      old_response_id = msg.response_id

      # Check for iterators
      if msg.type == msg.Type.ITERATOR:
        if res.iterator:
          raise ValueError("Received multiple iterator messages at once.")
        res.iterator = rdf_client_action.Iterator(msg.payload)
        continue

      # Look for a status message
      if msg.type == msg.Type.STATUS:
        # Our status is set to the first status message that we see in
        # the responses. We ignore all other messages after that.
        res.status = rdf_flows.GrrStatus(msg.payload)

        # Check this to see if the call succeeded
        res.success = res.status.status == res.status.ReturnedStatus.OK

        # Ignore all other messages
        break

      if msg.type == msg.Type.MESSAGE:
        if request.HasField("request"):
          # Let's do some verification for requests that came from clients.
          if not expected_response_classes:
            raise RuntimeError("Client action %s does not specify out_rdfvalue."
                               % client_action_name)
          else:
            args_rdf_name = msg.args_rdf_name
            if not args_rdf_name:
              raise RuntimeError("Deprecated message format received: "
                                 "args_rdf_name is None.")
            elif args_rdf_name not in [
                x.__name__ for x in expected_response_classes
            ]:
              raise RuntimeError("Response type was %s but expected %s for %s."
                                 % (args_rdf_name, expected_response_classes,
                                    client_action_name))
      # Use this message
      res.responses.append(msg.payload)

    if res.status is None:
      # This is a special case of de-synchronized messages.
      if dropped_responses:
        logging.error(
            "De-synchronized messages detected:\n %s",
            "\n".join([utils.SmartUnicode(x) for x in dropped_responses]))

      res.LogFlowState(responses)

      raise ValueError("No valid Status message.")

    return res

  def __iter__(self):
    return iter(self.responses)

  def First(self):
    """A convenience method to return the first response."""
    for x in self:
      return x

  def __len__(self):
    return len(self.responses)

  def __nonzero__(self):
    return bool(self.responses)

  def LogFlowState(self, responses):
    session_id = responses[0].session_id

    logging.error(
        "No valid Status message.\nState:\n%s\n%s\n%s",
        data_store.DB.ResolvePrefix(session_id.Add("state"), "flow:"),
        data_store.DB.ResolvePrefix(
            session_id.Add("state/request:%08X" % responses[0].request_id),
            "flow:"),
        data_store.DB.ResolvePrefix(queues.FLOWS, "notify:%s" % session_id))


class FakeResponses(Responses):
  """An object which emulates the responses.

  This is only used internally to call a state method inline.
  """

  def __init__(self, messages, request_data):
    super(FakeResponses, self).__init__()
    self.success = True
    self.responses = messages or []
    self.request_data = request_data
    self.iterator = None
