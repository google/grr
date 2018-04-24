#!/usr/bin/env python
"""Throttle user calls to flows."""

from grr.lib import rdfvalue
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow


class Error(Exception):
  """Base error class."""


class ErrorDailyFlowRequestLimitExceeded(Error):
  """Too many flows run by a user on a client."""


class ErrorFlowDuplicate(Error):
  """The same exact flow has run recently on this client."""

  def __init__(self, message, flow_urn=None):
    super(ErrorFlowDuplicate, self).__init__(message)

    if not flow_urn:
      raise ValueError("flow_urn has to be specified.")
    self.flow_urn = flow_urn


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

  def EnforceLimits(self, client_id, user, flow_name, flow_args, token=None):
    """Enforce DailyFlowRequestLimit and FlowDuplicateInterval.

    Look at the flows that have run on this client within the last day and check
    we aren't exceeding our limits. Raises if limits will be exceeded by running
    the specified flow.

    Args:
      client_id: client URN
      user: username string
      flow_name: flow name string
      flow_args: flow args rdfvalue for the flow being launched
      token: acl token

    Raises:
      ErrorDailyFlowRequestLimitExceeded: if the user has already run
        API.DailyFlowRequestLimit on this client in the previous 24h.
      ErrorFlowDuplicate: an identical flow was run on this machine by a user
        within the API.FlowDuplicateInterval
    """
    if not self.dup_interval and not self.daily_req_limit:
      return

    flows_dir = aff4.FACTORY.Open(client_id.Add("flows"), token=token)
    now = rdfvalue.RDFDatetime.Now()
    earlier = now - rdfvalue.Duration("1d")
    dup_boundary = now - self.dup_interval

    flow_count = 0
    flow_list = flows_dir.ListChildren(
        age=(earlier.AsMicrosecondsSinceEpoch(),
             now.AsMicrosecondsSinceEpoch()))

    # Save DB roundtrips by checking both conditions at once. This means the dup
    # interval has a maximum of 1 day.
    for flow_obj in aff4.FACTORY.MultiOpen(flow_list, token=token):
      flow_context = flow_obj.context

      # If dup_interval is set, check for identical flows run within the
      # duplicate interval.
      if self.dup_interval and flow_context.create_time > dup_boundary:
        if flow_obj.runner_args.flow_name == flow_name:

          # Raise if either the args are the same, or the args were empty, to
          # which None is the equivalent.
          if flow_obj.args == flow_args or (isinstance(
              flow_obj.args, flow.EmptyFlowArgs) and flow_args is None):
            raise ErrorFlowDuplicate(
                "Identical %s already run on %s at %s" %
                (flow_name, client_id, flow_context.create_time),
                flow_urn=flow_obj.urn)

      # Filter for flows started by user within the 1 day window.
      if flow_context.creator == user and flow_context.create_time > earlier:
        flow_count += 1

    # If limit is set, enforce it.
    if self.daily_req_limit and flow_count >= self.daily_req_limit:
      raise ErrorDailyFlowRequestLimitExceeded(
          "%s flows run since %s, limit: %s" % (flow_count, earlier,
                                                self.daily_req_limit))
