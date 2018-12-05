#!/usr/bin/env python
"""Clients-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import flow
from grr_api_client import utils
from grr_api_client import vfs
from grr_response_proto.api import client_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import user_pb2


class ClientApprovalBase(object):
  """Base class for ClientApproval and ClientApprovalRef."""

  def __init__(self,
               client_id=None,
               approval_id=None,
               username=None,
               context=None):
    super(ClientApprovalBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not username:
      raise ValueError("username can't be empty.")

    self.client_id = client_id
    self.approval_id = approval_id
    self.username = username

    self._context = context

  def Grant(self):
    args = user_pb2.ApiGrantClientApprovalArgs(
        client_id=self.client_id,
        username=self.username,
        approval_id=self.approval_id)
    data = self._context.SendRequest("GrantClientApproval", args)
    return ClientApproval(
        data=data, username=self.username, context=self._context)

  def Get(self):
    """Fetch and return a proper ClientApproval object."""

    args = user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=self.approval_id,
        username=self.username)
    result = self._context.SendRequest("GetClientApproval", args)
    return ClientApproval(
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


class ClientApprovalRef(ClientApprovalBase):
  """Client approval reference (pointer to an object without data)."""


class ClientApproval(ClientApprovalBase):
  """Client approval object with fetched data."""

  def __init__(self, data=None, username=None, context=None):

    if data is None:
      raise ValueError("data can't be None")

    super(ClientApproval, self).__init__(
        client_id=utils.UrnStringToClientId(data.subject.urn),
        approval_id=data.id,
        username=username,
        context=context)

    self.data = data


class ClientCrash(object):
  """Wrapper class for client crashes."""

  def __init__(self, data=None, context=None):
    super(ClientCrash, self).__init__()

    self.data = data

    self.timestamp = data.timestamp
    self.crash_message = data.crash_message
    self.backtrace = data.backtrace

    self.client = ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context)


class ClientBase(object):
  """Base class for Client and ClientRef."""

  def __init__(self, client_id=None, context=None):
    super(ClientBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty.")

    self.client_id = client_id
    self._context = context

  def File(self, path):
    """Returns a reference to a file with a given path on client's VFS."""

    return vfs.FileRef(
        client_id=self.client_id, path=path, context=self._context)

  def Flow(self, flow_id):
    """Return a reference to a flow with a given id on this client."""

    return flow.FlowRef(
        client_id=self.client_id, flow_id=flow_id, context=self._context)

  def CreateFlow(self, name=None, args=None, runner_args=None):
    """Create new flow on this client."""

    if not name:
      raise ValueError("name can't be empty")

    request = flow_pb2.ApiCreateFlowArgs(client_id=self.client_id)

    request.flow.name = name
    if runner_args:
      request.flow.runner_args.CopyFrom(runner_args)

    if args:
      request.flow.args.value = args.SerializeToString()
      request.flow.args.type_url = utils.GetTypeUrl(args)

    data = self._context.SendRequest("CreateFlow", request)
    return flow.Flow(data=data, context=self._context)

  def ListFlows(self):
    """List flows that ran on this client."""

    args = flow_pb2.ApiListFlowsArgs(client_id=self.client_id)

    items = self._context.SendIteratorRequest("ListFlows", args)
    return utils.MapItemsIterator(
        lambda data: flow.Flow(data=data, context=self._context), items)

  def Approval(self, username, approval_id):
    """Returns a reference to an approval."""

    return ClientApprovalRef(
        client_id=self.client_id,
        username=username,
        approval_id=approval_id,
        context=self._context)

  def CreateApproval(self,
                     reason=None,
                     notified_users=None,
                     email_cc_addresses=None,
                     keep_client_alive=False):
    """Create a new approval for the current user to access this client."""

    if not reason:
      raise ValueError("reason can't be empty")

    if not notified_users:
      raise ValueError("notified_users list can't be empty.")

    approval = user_pb2.ApiClientApproval(
        reason=reason,
        notified_users=notified_users,
        email_cc_addresses=email_cc_addresses or [])
    args = user_pb2.ApiCreateClientApprovalArgs(
        client_id=self.client_id,
        approval=approval,
        keep_client_alive=keep_client_alive)

    data = self._context.SendRequest("CreateClientApproval", args)
    return ClientApproval(
        data=data, username=self._context.username, context=self._context)

  def ListApprovals(self, state=user_pb2.ApiListClientApprovalsArgs.ANY):
    args = user_pb2.ApiListClientApprovalsArgs(
        client_id=self.client_id, state=state)
    items = self._context.SendIteratorRequest("ListClientApprovals", args)

    def MapClientApproval(data):
      return ClientApproval(
          data=data, username=self._context.username, context=self._context)

    return utils.MapItemsIterator(MapClientApproval, items)

  def AddLabels(self, labels):
    if not labels:
      raise ValueError("labels list can't be empty")

    args = client_pb2.ApiAddClientsLabelsArgs(
        client_ids=[self.client_id], labels=labels)
    self._context.SendRequest("AddClientsLabels", args)

  def AddLabel(self, label):
    return self.AddLabels([label])

  def RemoveLabels(self, labels):
    if not labels:
      raise ValueError("labels list can't be empty")

    args = client_pb2.ApiRemoveClientsLabelsArgs(
        client_ids=[self.client_id], labels=labels)
    self._context.SendRequest("RemoveClientsLabels", args)

  def RemoveLabel(self, label):
    return self.RemoveLabels([label])


class ClientRef(ClientBase):
  """Ref to the client."""

  def Get(self):
    """Fetch client's data and return a proper Client object."""

    args = client_pb2.ApiGetClientArgs(client_id=self.client_id)
    result = self._context.SendRequest("GetClient", args)
    return Client(data=result, context=self._context)


class Client(ClientBase):
  """Client object with fetched data."""

  def __init__(self, data=None, context=None):

    if data is None:
      raise ValueError("data can't be None")

    super(Client, self).__init__(
        client_id=utils.UrnStringToClientId(data.urn), context=context)

    self.data = data


def SearchClients(query=None, context=None):
  """List clients conforming to a givent query."""

  args = client_pb2.ApiSearchClientsArgs(query=query)

  items = context.SendIteratorRequest("SearchClients", args)
  return utils.MapItemsIterator(lambda data: Client(data=data, context=context),
                                items)
