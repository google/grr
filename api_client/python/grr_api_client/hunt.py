#!/usr/bin/env python
"""Hunts-related part of GRR API client library."""

from grr_api_client import client
from grr_api_client import utils
from grr.proto import api_pb2


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
    args = api_pb2.ApiGrantHuntApprovalArgs(
        hunt_id=self.hunt_id,
        username=self.username,
        approval_id=self.approval_id)
    data = self._context.SendRequest("GrantHuntApproval", args)
    return HuntApproval(
        data=data, username=self.username, context=self._context)


class HuntApprovalRef(HuntApprovalBase):
  """Ref to the hunt approval."""

  def Get(self):
    """Fetch and return a proper HuntApproval object."""

    args = api_pb2.ApiGetHuntApprovalArgs(
        hunt_id=self.hunt_id,
        approval_id=self.approval_id,
        username=self.username)
    result = self._context.SendRequest("GetHuntApproval", args)
    return HuntApproval(
        data=result, username=self._context.username, context=self._context)


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

    approval = api_pb2.ApiHuntApproval(
        reason=reason,
        notified_users=notified_users,
        email_cc_addresses=email_cc_addresses or [])
    args = api_pb2.ApiCreateHuntApprovalArgs(
        hunt_id=self.hunt_id, approval=approval)

    data = self._context.SendRequest("CreateHuntApproval", args)
    return HuntApproval(
        data=data, username=self._context.username, context=self._context)

  def Modify(self, client_limit=None, client_rate=None, expires=None):
    """Modifies a number of hunt arguments."""
    args = api_pb2.ApiModifyHuntArgs(hunt_id=self.hunt_id)

    if client_limit is not None:
      args.client_limit = client_limit

    if client_rate is not None:
      args.client_rate = client_rate

    if expires is not None:
      args.expires = expires

    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def Start(self):
    args = api_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=api_pb2.ApiHunt.STARTED)
    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def Stop(self):
    args = api_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=api_pb2.ApiHunt.STOPPED)
    data = self._context.SendRequest("ModifyHunt", args)
    return Hunt(data=data, context=self._context)

  def ListResults(self):
    args = api_pb2.ApiListHuntResultsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntResults", args)
    return utils.MapItemsIterator(
        lambda data: HuntResult(data=data, context=self._context), items)

  def GetFilesArchive(self):
    args = api_pb2.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt_id)
    return self._context.SendStreamingRequest("GetHuntFilesArchive", args)


class HuntRef(HuntBase):
  """Ref to a hunt."""

  def Get(self):
    """Fetch hunt's data and return proper Hunt object."""

    args = api_pb2.ApiGetHuntArgs(hunt_id=self.hunt_id)
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

  request = api_pb2.ApiCreateHuntArgs(flow_name=flow_name)
  if flow_args:
    request.flow_args.value = flow_args.SerializeToString()
    request.flow_args.type_url = utils.GetTypeUrl(flow_args)

  if hunt_runner_args:
    request.hunt_runner_args.CopyFrom(hunt_runner_args)

  data = context.SendRequest("CreateHunt", request)
  return Hunt(data=data, context=context)


def ListHunts(context=None):
  """List all GRR hunts."""

  items = context.SendIteratorRequest("ListHunts", api_pb2.ApiListHuntsArgs())
  return utils.MapItemsIterator(
      lambda data: Hunt(data=data, context=context),
      items)


def ListHuntApprovals(context=None):
  """List all hunt approvals belonging to requesting user."""
  items = context.SendIteratorRequest("ListHuntApprovals",
                                      api_pb2.ApiListHuntApprovalsArgs())

  def MapHuntApproval(data):
    return HuntApproval(data=data, username=context.username, context=context)

  return utils.MapItemsIterator(MapHuntApproval, items)
