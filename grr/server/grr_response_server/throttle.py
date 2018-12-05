#!/usr/bin/env python
"""Throttle user calls to flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class Error(Exception):
  """Base error class."""


class DailyFlowRequestLimitExceededError(Error):
  """Too many flows run by a user on a client."""


class DuplicateFlowError(Error):
  """The same exact flow has run recently on this client."""

  def __init__(self, message, flow_id):
    super(DuplicateFlowError, self).__init__(message)

    if not flow_id:
      raise ValueError("flow_id has to be specified.")
    self.flow_id = flow_id


class FlowThrottler(object):
  """Checks for excessive or repetitive flow requests."""

  def __init__(self, daily_req_limit=None, dup_interval=None):
    """Create flow throttler object.

    Args:
      daily_req_limit: Number of flows allow per user per client. Integer.
      dup_interval: rdfvalue.Duration time during which duplicate flows will be
        blocked.
    """
    self.daily_req_limit = daily_req_limit
    self.dup_interval = dup_interval

  def _LoadFlows(self, client_id, min_create_time, token):
    """Yields all flows for the given client_id and time range.

    Args:
      client_id: client URN
      min_create_time: minimum creation time (inclusive)
      token: acl token
    Yields: flow_objects.Flow objects
    """
    if data_store.RelationalDBFlowsEnabled():
      flow_list = data_store.REL_DB.ReadAllFlowObjects(
          client_id, min_create_time=min_create_time)
      for flow_obj in flow_list:
        if not flow_obj.parent_flow_id:
          yield flow_obj
    else:
      now = rdfvalue.RDFDatetime.Now()
      client_id_urn = rdf_client.ClientURN(client_id)
      flows_dir = aff4.FACTORY.Open(client_id_urn.Add("flows"), token=token)
      # Save DB roundtrips by checking both conditions at once.
      flow_list = flows_dir.ListChildren(
          age=(min_create_time.AsMicrosecondsSinceEpoch(),
               now.AsMicrosecondsSinceEpoch()))
      for flow_obj in aff4.FACTORY.MultiOpen(flow_list, token=token):
        yield rdf_flow_objects.Flow(
            args=flow_obj.args,
            flow_class_name=flow_obj.runner_args.flow_name,
            flow_id=flow_obj.urn.Basename(),
            create_time=flow_obj.context.create_time,
            creator=flow_obj.creator,
        )

  def EnforceLimits(self, client_id, user, flow_name, flow_args, token=None):
    """Enforce DailyFlowRequestLimit and FlowDuplicateInterval.

    Look at the flows that have run on this client recently and check
    we aren't exceeding our limits. Raises if limits will be exceeded by running
    the specified flow.

    Args:
      client_id: client URN
      user: username string
      flow_name: flow name string
      flow_args: flow args rdfvalue for the flow being launched
      token: acl token

    Raises:
      DailyFlowRequestLimitExceededError: if the user has already run
        API.DailyFlowRequestLimit on this client in the previous 24h.
      DuplicateFlowError: an identical flow was run on this machine by a user
        within the API.FlowDuplicateInterval
    """
    if not self.dup_interval and not self.daily_req_limit:
      return

    now = rdfvalue.RDFDatetime.Now()
    yesterday = now - rdfvalue.Duration("1d")
    dup_boundary = now - self.dup_interval
    min_create_time = min(yesterday, dup_boundary)

    flow_count = 0
    flows = self._LoadFlows(client_id, min_create_time, token=token)

    if flow_args is None:
      flow_args = flow.EmptyFlowArgs()

    for flow_obj in flows:
      if (flow_obj.create_time > dup_boundary and
          flow_obj.flow_class_name == flow_name and flow_obj.args == flow_args):
        raise DuplicateFlowError(
            "Identical %s already run on %s at %s" % (flow_name, client_id,
                                                      flow_obj.create_time),
            flow_id=flow_obj.flow_id)

      # Filter for flows started by user within the 1 day window.
      if flow_obj.creator == user and flow_obj.create_time > yesterday:
        flow_count += 1

    # If limit is set, enforce it.
    if self.daily_req_limit and flow_count >= self.daily_req_limit:
      raise DailyFlowRequestLimitExceededError(
          "%s flows run since %s, limit: %s" % (flow_count, yesterday,
                                                self.daily_req_limit))
