#!/usr/bin/env python
"""Hunts-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import client
from grr_api_client import utils
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import user_pb2


class HuntApprovalBase(object):
  """Base class for HuntApproval and HuntApprovalRef."""

  def __init__(self,
               hunt_id=None,
               approval_id=None,
               username=None,
               context=None):
    super(HuntApprovalBase, self).__init__()

    if not hunt_id:
      raise ValueError("hunt_id can't be empty.")

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not username:
      raise ValueError("username can't be empty.")

    self.hunt_id = hunt_id
    self.approval_id = approval_id
    self.username = username

    self._context = context

  def Grant(self):
    args = hunt_pb2.ApiGrantHuntApprovalArgs(
        hunt_id=self.hunt_id,
        username=self.username,
        approval_id=self.approval_id)
    data = self._context.SendRequest("GrantHuntApproval", args)
    return HuntApproval(
        data=data, username=self.username, context=self._context)

  def Get(self):
    """Fetch and return a proper HuntApproval object."""

    args = user_pb2.ApiGetHuntApprovalArgs(
        hunt_id=self.hunt_id,
        approval_id=self.approval_id,
        username=self.username)
    result = self._context.SendRequest("GetHuntApproval", args)
    return HuntApproval(
        data=result, username=self._context.username, context=self._context)

  def WaitUntilValid(self, timeout=None):
    """Wait until the approval is valid (i.e. - approved).

    Args:
      timeout: timeout in seconds. None means default timeout (1 hour).
               0 means no timeout (wait forever).
    Returns:
      Operation object with refreshed target_file.
    Raises:
      PollTimeoutError: if timeout is reached.
    """

    return utils.Poll(
        generator=self.Get,
        condition=lambda f: f.data.is_valid,
        timeout=timeout)


class HuntApprovalRef(HuntApprovalBase):
  """Hunt approval reference (points to the approval, but has no data)."""


class HuntApproval(HuntApprovalBase):
  """Hunt approval object with fetched data."""

  def __init__(self, data=None, username=None, context=None):

    if data is None:
      raise ValueError("data can't be None")

    super(HuntApproval, self).__init__(
        hunt_id=utils.UrnStringToHuntId(data.subject.urn),
        approval_id=data.id,
        username=username,
        context=context)

    self.data = data


class HuntResult(object):
  """Wrapper class for hunt results."""

  def __init__(self, data=None, context=None):
    super(HuntResult, self).__init__()
    self.data = data

    self.client = client.ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context)
    self.timestamp = data.timestamp

  @property
  def payload(self):
    return utils.UnpackAny(self.data.payload)


class HuntError(object):
  """Wrapper class for hunt errors."""

  def __init__(self, data=None, context=None):
    super(HuntError, self).__init__()

    self.data = data
    self.log_message = self.data.log_message
    self.backtrace = self.data.backtrace

    self.client = client.ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context)


class HuntLog(object):
  """Wrapper class for hunt logs."""

  def __init__(self, data=None, context=None):
    super(HuntLog, self).__init__()

    self.data = data
    self.log_message = self.data.log_message

    self.client = None
    if data.client_id:
      self.client = client.ClientRef(
          client_id=utils.UrnStringToClientId(data.client_id), context=context)


class HuntClient(client.ClientRef):
  """Wrapper class for hunt clients."""

  def __init__(self, data=None, context=None):
    super(HuntClient, self).__init__(client_id=data.client_id, context=context)

    self.data = data


class HuntBase(object):
  """Base class for HuntRef and Hunt."""

  def __init__(self, hunt_id=None, context=None):
    super(HuntBase, self).__init__()

    if not hunt_id:
      raise ValueError("hunt_id can't be empty.")

    self.hunt_id = hunt_id
    self._context = context

  def Approval(self, username, approval_id):
    """Returns a reference to an approval."""

    return HuntApprovalRef(
        hunt_id=self.hunt_id,
        username=username,
        approval_id=approval_id,
        context=self._context)

  def CreateApproval(self,
                     reason=None,
                     notified_users=None,
                     email_cc_addresses=None):
    """Create a new approval for the current user to access this hunt."""

    if not reason:
      raise ValueError("reason can't be empty")

    if not notified_users:
      raise ValueError("notified_users list can't be empty.")

    approval = user_pb2.ApiHuntApproval(
        reason=reason,
        notified_users=notified_users,
        email_cc_addresses=email_cc_addresses or [])
    args = user_pb2.ApiCreateHuntApprovalArgs(
        hunt_id=self.hunt_id, approval=approval)

    data = self._context.SendRequest("CreateHuntApproval", args)
    return HuntApproval(
        data=data, username=self._context.username, context=self._context)

  def Modify(self, client_limit=None, client_rate=None, expires=None):
    """Modifies a number of hunt arguments."""
    args = hunt_pb2.ApiModifyHuntArgs(hunt_id=self.hunt_id)

    if client_limit is not None:
      args.client_limit = client_limit

    if client_rate is not None:
      args.client_rate = client_rate

    if expires is not None:
      args.expires = expires

    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def Delete(self):
    args = hunt_pb2.ApiDeleteHuntArgs(hunt_id=self.hunt_id)
    self._context.SendRequest("DeleteHunt", args)

  def Start(self):
    args = hunt_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=hunt_pb2.ApiHunt.STARTED)
    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def Stop(self):
    args = hunt_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=hunt_pb2.ApiHunt.STOPPED)
    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def ListResults(self):
    args = hunt_pb2.ApiListHuntResultsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntResults", args)
    return utils.MapItemsIterator(
        lambda data: HuntResult(data=data, context=self._context), items)

  def ListLogs(self):
    args = hunt_pb2.ApiListHuntLogsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntLogs", args)
    return utils.MapItemsIterator(
        lambda data: HuntLog(data=data, context=self._context), items)

  def ListErrors(self):
    args = hunt_pb2.ApiListHuntErrorsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntErrors", args)
    return utils.MapItemsIterator(
        lambda data: HuntError(data=data, context=self._context), items)

  def ListCrashes(self):
    args = hunt_pb2.ApiListHuntCrashesArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntCrashes", args)
    return utils.MapItemsIterator(
        lambda data: client.ClientCrash(data=data, context=self._context),
        items)

  CLIENT_STATUS_STARTED = hunt_pb2.ApiListHuntClientsArgs.STARTED
  CLIENT_STATUS_OUTSTANDING = hunt_pb2.ApiListHuntClientsArgs.OUTSTANDING
  CLIENT_STATUS_COMPLETED = hunt_pb2.ApiListHuntClientsArgs.COMPLETED

  def ListClients(self, client_status):
    args = hunt_pb2.ApiListHuntClientsArgs(
        hunt_id=self.hunt_id, client_status=client_status)
    items = self._context.SendIteratorRequest("ListHuntClients", args)
    return utils.MapItemsIterator(
        lambda data: HuntClient(data=data, context=self._context), items)

  def GetClientCompletionStats(self):
    args = hunt_pb2.ApiGetHuntClientCompletionStatsArgs(hunt_id=self.hunt_id)
    return self._context.SendRequest("GetHuntClientCompletionStats", args)

  def GetStats(self):
    args = hunt_pb2.ApiGetHuntStatsArgs(hunt_id=self.hunt_id)
    return self._context.SendRequest("GetHuntStats", args).stats

  def GetFilesArchive(self):
    args = hunt_pb2.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt_id)
    return self._context.SendStreamingRequest("GetHuntFilesArchive", args)

  def GetExportedResults(self, plugin_name):
    args = hunt_pb2.ApiGetExportedHuntResultsArgs(
        hunt_id=self.hunt_id, plugin_name=plugin_name)
    return self._context.SendStreamingRequest("GetExportedHuntResults", args)


class HuntRef(HuntBase):
  """Ref to a hunt."""

  def Get(self):
    """Fetch hunt's data and return proper Hunt object."""

    args = hunt_pb2.ApiGetHuntArgs(hunt_id=self.hunt_id)
    data = self._context.SendRequest("GetHunt", args)
    return Hunt(data=data, context=self._context)


class Hunt(HuntBase):
  """Hunt object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    hunt_id = utils.UrnStringToHuntId(data.urn)

    super(Hunt, self).__init__(hunt_id=hunt_id, context=context)

    self.data = data


def CreateHunt(flow_name=None,
               flow_args=None,
               hunt_runner_args=None,
               context=None):
  """Creates a new hunt.

  Args:
    flow_name: String with a name of a flow that will run on all the clients
        in the hunt.
    flow_args: Flow arguments to be used. A proto, that depends on a flow.
    hunt_runner_args: flows_pb2.HuntRunnerArgs instance. Used to specify
        description, client_rule_set, output_plugins and other useful
        hunt attributes.
    context: API context.

  Raises:
    ValueError: if flow_name is empty.

  Returns:
    Hunt object corresponding to the created hunt.
  """
  if not flow_name:
    raise ValueError("flow_name can't be empty")

  request = hunt_pb2.ApiCreateHuntArgs(flow_name=flow_name)
  if flow_args:
    request.flow_args.value = flow_args.SerializeToString()
    request.flow_args.type_url = utils.GetTypeUrl(flow_args)

  if hunt_runner_args:
    request.hunt_runner_args.CopyFrom(hunt_runner_args)

  data = context.SendRequest("CreateHunt", request)
  return Hunt(data=data, context=context)


def ListHunts(context=None):
  """List all GRR hunts."""

  items = context.SendIteratorRequest("ListHunts", hunt_pb2.ApiListHuntsArgs())
  return utils.MapItemsIterator(lambda data: Hunt(data=data, context=context),
                                items)


def ListHuntApprovals(context=None):
  """List all hunt approvals belonging to requesting user."""
  items = context.SendIteratorRequest("ListHuntApprovals",
                                      hunt_pb2.ApiListHuntApprovalsArgs())

  def MapHuntApproval(data):
    return HuntApproval(data=data, username=context.username, context=context)

  return utils.MapItemsIterator(MapHuntApproval, items)
