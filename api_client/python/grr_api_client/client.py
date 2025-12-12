#!/usr/bin/env python
"""Clients-related part of GRR API client library."""

from collections import abc
from collections.abc import Sequence
import time

from grr_api_client import flow
from grr_api_client import utils
from grr_api_client import vfs
from grr_response_proto.api import client_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import user_pb2


class ClientApprovalBase(object):
  """Base class for ClientApproval and ClientApprovalRef."""

  def __init__(
      self, client_id=None, approval_id=None, username=None, context=None
  ):
    super().__init__()

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
        approval_id=self.approval_id,
    )
    data = self._context.SendRequest("GrantClientApproval", args)
    return ClientApproval(
        data=data, username=self.username, context=self._context
    )

  def Get(self):
    """Fetch and return a proper ClientApproval object."""

    args = user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=self.approval_id,
        username=self.username,
    )
    result = self._context.SendRequest("GetClientApproval", args)
    return ClientApproval(
        data=result, username=self._context.username, context=self._context
    )

  def WaitUntilValid(self, timeout=None):
    """Wait until the approval is valid (i.e. - approved).

    Args:
      timeout: timeout in seconds. None means default timeout (1 hour). 0 means
        no timeout (wait forever).

    Returns:
      Operation object with refreshed target_file.
    Raises:
      PollTimeoutError: if timeout is reached.
    """

    return utils.Poll(
        generator=self.Get, condition=lambda f: f.data.is_valid, timeout=timeout
    )


class ClientApprovalRef(ClientApprovalBase):
  """Client approval reference (pointer to an object without data)."""


class ClientApproval(ClientApprovalBase):
  """Client approval object with fetched data."""

  def __init__(self, data=None, username=None, context=None):

    if data is None:
      raise ValueError("data can't be None")

    super().__init__(
        client_id=utils.UrnStringToClientId(data.subject.urn),
        approval_id=data.id,
        username=username,
        context=context,
    )

    self.data = data


class ClientCrash(object):
  """Wrapper class for client crashes."""

  def __init__(self, data=None, context=None):
    super().__init__()

    self.data = data

    self.timestamp = data.timestamp
    self.crash_message = data.crash_message
    self.backtrace = data.backtrace

    self.client = ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context
    )


class ClientBase(object):
  """Base class for Client and ClientRef."""

  def __init__(self, client_id=None, context=None):
    super().__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty.")

    self.client_id = client_id
    self._context = context

  def File(self, path):
    """Returns a reference to a file with a given path on client's VFS."""

    return vfs.FileRef(
        client_id=self.client_id, path=path, context=self._context
    )

  def Flow(self, flow_id):
    """Return a reference to a flow with a given id on this client."""

    return flow.FlowRef(
        client_id=self.client_id, flow_id=flow_id, context=self._context
    )

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

  def Interrogate(self):
    """Run an Interrogate Flow on this client."""
    request = client_pb2.ApiInterrogateClientArgs(client_id=self.client_id)
    data = self._context.SendRequest("InterrogateClient", request)
    # Return a populated Flow, similar to the behavior of CreateFlow().
    return self.Flow(data.operation_id).Get()

  def ListFlows(self):
    """List flows that ran on this client."""

    args = flow_pb2.ApiListFlowsArgs(client_id=self.client_id)

    items = self._context.SendIteratorRequest("ListFlows", args)
    return utils.MapItemsIterator(
        lambda data: flow.Flow(data=data, context=self._context), items
    )

  def Approval(self, username, approval_id):
    """Returns a reference to an approval."""

    return ClientApprovalRef(
        client_id=self.client_id,
        username=username,
        approval_id=approval_id,
        context=self._context,
    )

  def CreateApproval(
      self,
      reason=None,
      notified_users=None,
      email_cc_addresses=None,
      expiration_duration_days=0,
  ):
    """Create a new approval for the current user to access this client."""

    if not reason:
      raise ValueError("reason can't be empty")

    if not notified_users:
      raise ValueError("notified_users list can't be empty.")

    expiration_time_us = 0
    if expiration_duration_days != 0:
      expiration_time_us = int(
          (time.time() + expiration_duration_days * 24 * 3600) * 1e6
      )

    approval = user_pb2.ApiClientApproval(
        reason=reason,
        notified_users=notified_users,
        email_cc_addresses=email_cc_addresses or [],
        expiration_time_us=expiration_time_us,
    )
    args = user_pb2.ApiCreateClientApprovalArgs(
        client_id=self.client_id,
        approval=approval,
    )

    data = self._context.SendRequest("CreateClientApproval", args)
    return ClientApproval(
        data=data, username=self._context.username, context=self._context
    )

  def ListApprovals(self, state=user_pb2.ApiListClientApprovalsArgs.ANY):
    args = user_pb2.ApiListClientApprovalsArgs(
        client_id=self.client_id, state=state
    )
    items = self._context.SendIteratorRequest("ListClientApprovals", args)

    def MapClientApproval(data):
      return ClientApproval(
          data=data, username=self._context.username, context=self._context
      )

    return utils.MapItemsIterator(MapClientApproval, items)

  def VerifyAccess(self):
    args = client_pb2.ApiVerifyAccessArgs(client_id=self.client_id)
    self._context.SendRequest("VerifyAccess", args)

  def _ProcessLabels(self, labels):
    """Checks that 'labels' arguments for AddLabels/RemoveLabels is correct."""

    if isinstance(labels, (str, bytes)):
      raise TypeError(
          "'labels' argument is expected to be an "
          "iterable of strings, not {!r}.".format(labels)
      )

    if not isinstance(labels, abc.Iterable):
      raise TypeError(
          "Expected iterable container, but got {!r} instead.".format(labels)
      )

    labels_list = list(labels)
    if not labels_list:
      raise ValueError("Labels iterable can't be empty.")

    for l in labels_list:
      if not isinstance(l, str):
        raise TypeError(
            "Expected labels as strings, got {!r} instead.".format(l)
        )

    return labels_list

  def AddLabels(self, labels):
    labels = self._ProcessLabels(labels)

    args = client_pb2.ApiAddClientsLabelsArgs(
        client_ids=[self.client_id], labels=labels
    )
    self._context.SendRequest("AddClientsLabels", args)

  def AddLabel(self, label):
    return self.AddLabels([label])

  def RemoveLabels(self, labels):
    labels = self._ProcessLabels(labels)

    args = client_pb2.ApiRemoveClientsLabelsArgs(
        client_ids=[self.client_id], labels=labels
    )
    self._context.SendRequest("RemoveClientsLabels", args)

  def RemoveLabel(self, label):
    return self.RemoveLabels([label])

  def Get(self):
    """Fetch client's data and return a proper Client object."""

    args = client_pb2.ApiGetClientArgs(client_id=self.client_id)
    result = self._context.SendRequest("GetClient", args)
    return Client(data=result, context=self._context)

  def KillFleetspeak(self, force: bool) -> None:
    """Kills fleetspeak on the given client."""
    args = client_pb2.ApiKillFleetspeakArgs()
    args.client_id = self.client_id
    args.force = force
    self._context.SendRequest("KillFleetspeak", args)

  def RestartFleetspeakGrrService(self) -> None:
    """Restarts the GRR fleetspeak service on the given client."""
    args = client_pb2.ApiRestartFleetspeakGrrServiceArgs()
    args.client_id = self.client_id
    self._context.SendRequest("RestartFleetspeakGrrService", args)

  def DeleteFleetspeakPendingMessages(self) -> None:
    """Deletes fleetspeak messages pending for the given client."""
    args = client_pb2.ApiDeleteFleetspeakPendingMessagesArgs()
    args.client_id = self.client_id
    self._context.SendRequest("DeleteFleetspeakPendingMessages", args)

  def GetFleetspeakPendingMessageCount(self) -> int:
    """Returns the number of fleetspeak messages pending for the given client."""
    args = client_pb2.ApiGetFleetspeakPendingMessageCountArgs()
    args.client_id = self.client_id
    result = self._context.SendRequest("GetFleetspeakPendingMessageCount", args)
    return result.count

  def GetFleetspeakPendingMessages(
      self, offset: int = 0, limit: int = 0, want_data: bool = False
  ) -> Sequence[client_pb2.ApiFleetspeakMessage]:
    """Returns messages pending for the given client."""
    args = client_pb2.ApiGetFleetspeakPendingMessagesArgs()
    args.client_id = self.client_id
    args.offset = offset
    args.limit = limit
    args.want_data = want_data
    result = self._context.SendRequest("GetFleetspeakPendingMessages", args)
    return result.messages


class ClientRef(ClientBase):
  """Ref to the client."""

  def __repr__(self):
    return "ClientRef(client_id={!r})".format(self.client_id)


class Client(ClientBase):
  """Client object with fetched data."""

  def __init__(self, data=None, context=None):

    if data is None:
      raise ValueError("data can't be None")

    super().__init__(
        client_id=utils.UrnStringToClientId(data.urn), context=context
    )

    self.data = data

  def __repr__(self):
    return "Client(data=<{} client_id={!r}>, ...)".format(
        type(self.data).__name__, self.data.client_id
    )


def SearchClients(query=None, context=None):
  """List clients conforming to a givent query."""

  args = client_pb2.ApiSearchClientsArgs(query=query)

  items = context.SendIteratorRequest("SearchClients", args)
  return utils.MapItemsIterator(
      lambda data: Client(data=data, context=context), items
  )
