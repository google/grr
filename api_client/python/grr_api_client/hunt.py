#!/usr/bin/env python
"""Hunts-related part of GRR API client library."""

from collections.abc import Sequence
from typing import Optional, Union

from google.protobuf import message
from grr_api_client import client
from grr_api_client import context as context_lib
from grr_api_client import utils
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import timeline_pb2
from grr_response_proto.api import user_pb2


class HuntApprovalBase(object):
  """Base class for HuntApproval and HuntApprovalRef."""

  def __init__(
      self,
      hunt_id: str,
      approval_id: str,
      username: str,
      context: context_lib.GrrApiContext,
  ):
    super().__init__()

    if not hunt_id:
      raise ValueError("hunt_id can't be empty.")

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not username:
      raise ValueError("username can't be empty.")

    self.hunt_id: str = hunt_id
    self.approval_id: str = approval_id
    self.username: str = username

    self._context: context_lib.GrrApiContext = context

  # TODO(hanuszczak): There was an unresolved reference in this function, yet
  # none of the test caught it, indicating insufficient test coverage.
  def Grant(self) -> "HuntApproval":
    args = user_pb2.ApiGrantHuntApprovalArgs(
        hunt_id=self.hunt_id,
        username=self.username,
        approval_id=self.approval_id,
    )
    data = self._context.SendRequest("GrantHuntApproval", args)
    if not isinstance(data, user_pb2.ApiHuntApproval):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return HuntApproval(
        data=data, username=self.username, context=self._context
    )

  def Get(self) -> "HuntApproval":
    """Fetch and return a proper HuntApproval object."""

    args = user_pb2.ApiGetHuntApprovalArgs(
        hunt_id=self.hunt_id,
        approval_id=self.approval_id,
        username=self.username,
    )
    result = self._context.SendRequest("GetHuntApproval", args)
    if not isinstance(result, user_pb2.ApiHuntApproval):
      raise TypeError(f"Unexpected response type: '{type(result)}'")

    return HuntApproval(
        data=result, username=self._context.username, context=self._context
    )

  def WaitUntilValid(
      self,
      timeout: int = utils.DEFAULT_POLL_TIMEOUT,
  ) -> "HuntApproval":
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


class HuntApprovalRef(HuntApprovalBase):
  """Hunt approval reference (points to the approval, but has no data)."""


class HuntApproval(HuntApprovalBase):
  """Hunt approval object with fetched data."""

  def __init__(
      self,
      data: user_pb2.ApiHuntApproval,
      username: str,
      context: context_lib.GrrApiContext,
  ):
    super().__init__(
        hunt_id=utils.UrnStringToHuntId(data.subject.urn),
        approval_id=data.id,
        username=username,
        context=context,
    )

    self.data: user_pb2.ApiHuntApproval = data


class HuntResult(object):
  """Wrapper class for hunt results."""

  def __init__(
      self,
      data: hunt_pb2.ApiHuntResult,
      context: context_lib.GrrApiContext,
  ):
    super().__init__()
    self.data: hunt_pb2.ApiHuntResult = data

    self.client: client.ClientRef = client.ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context
    )
    self.timestamp: int = data.timestamp

  @property
  def payload(self) -> Union[message.Message, utils.UnknownProtobuf]:
    return utils.UnpackAny(self.data.payload)


class HuntError(object):
  """Wrapper class for hunt errors."""

  def __init__(
      self,
      data: hunt_pb2.ApiHuntError,
      context: context_lib.GrrApiContext,
  ):
    super().__init__()

    self.data: hunt_pb2.ApiHuntError = data
    self.log_message: str = self.data.log_message
    self.backtrace: str = self.data.backtrace

    self.client: client.ClientRef = client.ClientRef(
        client_id=utils.UrnStringToClientId(data.client_id), context=context
    )


class HuntLog(object):
  """Wrapper class for hunt logs."""

  def __init__(
      self,
      data: hunt_pb2.ApiHuntLog,
      context: context_lib.GrrApiContext,
  ):
    super().__init__()

    self.data: hunt_pb2.ApiHuntLog = data
    self.log_message = self.data.log_message  # str

    self.client: Optional[client.ClientRef] = None
    if data.client_id:
      self.client = client.ClientRef(
          client_id=utils.UrnStringToClientId(data.client_id), context=context
      )


class HuntClient(client.ClientRef):
  """Wrapper class for hunt clients."""

  def __init__(
      self,
      data: hunt_pb2.ApiHuntClient,
      context: context_lib.GrrApiContext,
  ):
    super().__init__(client_id=data.client_id, context=context)

    self.data: hunt_pb2.ApiHuntClient = data


class HuntBase(object):
  """Base class for HuntRef and Hunt."""

  def __init__(
      self,
      hunt_id: str,
      context: context_lib.GrrApiContext,
  ):
    super().__init__()

    if not hunt_id:
      raise ValueError("hunt_id can't be empty.")

    self.hunt_id: str = hunt_id
    self._context: context_lib.GrrApiContext = context

  def Approval(
      self,
      username: str,
      approval_id: str,
  ) -> HuntApprovalRef:
    """Returns a reference to an approval."""

    return HuntApprovalRef(
        hunt_id=self.hunt_id,
        username=username,
        approval_id=approval_id,
        context=self._context,
    )

  def CreateApproval(
      self,
      reason: str,
      notified_users: Sequence[str],
      email_cc_addresses: Optional[Sequence[str]] = None,
  ) -> HuntApproval:
    """Create a new approval for the current user to access this hunt."""

    if not reason:
      raise ValueError("reason can't be empty")

    if not notified_users:
      raise ValueError("notified_users list can't be empty.")

    if email_cc_addresses is None:
      email_cc_addresses = []

    approval = user_pb2.ApiHuntApproval(
        reason=reason,
        notified_users=notified_users,
        email_cc_addresses=email_cc_addresses,
    )
    args = user_pb2.ApiCreateHuntApprovalArgs(
        hunt_id=self.hunt_id, approval=approval
    )

    data = self._context.SendRequest("CreateHuntApproval", args)
    if not isinstance(data, user_pb2.ApiHuntApproval):
      raise TypeError(f"unexpected response type: '{type(data)}'")

    return HuntApproval(
        data=data, username=self._context.username, context=self._context
    )

  def Modify(
      self,
      client_limit: Optional[int] = None,
      client_rate: Optional[int] = None,
      duration: Optional[int] = None,
  ) -> "Hunt":
    """Modifies a number of hunt arguments."""
    args = hunt_pb2.ApiModifyHuntArgs(hunt_id=self.hunt_id)

    if client_limit is not None:
      args.client_limit = client_limit

    if client_rate is not None:
      args.client_rate = client_rate

    if duration is not None:
      args.duration = duration

    data = self._context.SendRequest("ModifyHunt", args)
    if not isinstance(data, hunt_pb2.ApiHunt):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return Hunt(data=data, context=self._context)

  def Delete(self):
    args = hunt_pb2.ApiDeleteHuntArgs(hunt_id=self.hunt_id)
    self._context.SendRequest("DeleteHunt", args)

  def Start(self) -> "Hunt":
    args = hunt_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=hunt_pb2.ApiHunt.STARTED
    )
    data = self._context.SendRequest("ModifyHunt", args)
    if not isinstance(data, hunt_pb2.ApiHunt):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return Hunt(data=data, context=self._context)

  def Stop(self) -> "Hunt":
    args = hunt_pb2.ApiModifyHuntArgs(
        hunt_id=self.hunt_id, state=hunt_pb2.ApiHunt.STOPPED
    )
    data = self._context.SendRequest("ModifyHunt", args)
    if not isinstance(data, hunt_pb2.ApiHunt):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return Hunt(data=data, context=self._context)

  def ListResults(self) -> utils.ItemsIterator[HuntResult]:
    args = hunt_pb2.ApiListHuntResultsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntResults", args)
    return utils.MapItemsIterator(
        lambda data: HuntResult(data=data, context=self._context), items
    )

  def ListLogs(self) -> utils.ItemsIterator[HuntLog]:
    args = hunt_pb2.ApiListHuntLogsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntLogs", args)
    return utils.MapItemsIterator(
        lambda data: HuntLog(data=data, context=self._context), items
    )

  def ListErrors(self) -> utils.ItemsIterator[HuntError]:
    args = hunt_pb2.ApiListHuntErrorsArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntErrors", args)
    return utils.MapItemsIterator(
        lambda data: HuntError(data=data, context=self._context), items
    )

  def ListCrashes(self) -> utils.ItemsIterator[client.ClientCrash]:
    args = hunt_pb2.ApiListHuntCrashesArgs(hunt_id=self.hunt_id)
    items = self._context.SendIteratorRequest("ListHuntCrashes", args)
    return utils.MapItemsIterator(
        lambda data: client.ClientCrash(data=data, context=self._context), items
    )

  CLIENT_STATUS_STARTED = hunt_pb2.ApiListHuntClientsArgs.STARTED
  CLIENT_STATUS_OUTSTANDING = hunt_pb2.ApiListHuntClientsArgs.OUTSTANDING
  CLIENT_STATUS_COMPLETED = hunt_pb2.ApiListHuntClientsArgs.COMPLETED

  def ListClients(
      self,
      client_status: hunt_pb2.ApiListHuntClientsArgs.ClientStatus,
  ) -> utils.ItemsIterator[HuntClient]:
    args = hunt_pb2.ApiListHuntClientsArgs(
        hunt_id=self.hunt_id, client_status=client_status
    )
    items = self._context.SendIteratorRequest("ListHuntClients", args)
    return utils.MapItemsIterator(
        lambda data: HuntClient(data=data, context=self._context), items
    )

  def GetClientCompletionStats(
      self,
  ) -> hunt_pb2.ApiGetHuntClientCompletionStatsResult:
    args = hunt_pb2.ApiGetHuntClientCompletionStatsArgs(hunt_id=self.hunt_id)

    response = self._context.SendRequest("GetHuntClientCompletionStats", args)
    if not isinstance(response, hunt_pb2.ApiGetHuntClientCompletionStatsResult):
      raise TypeError(f"Unexpected response type: '{type(response)}'")

    return response

  def GetStats(self) -> jobs_pb2.ClientResourcesStats:
    args = hunt_pb2.ApiGetHuntStatsArgs(hunt_id=self.hunt_id)

    response = self._context.SendRequest("GetHuntStats", args)
    if not isinstance(response, hunt_pb2.ApiGetHuntStatsResult):
      raise TypeError(f"Unexpected response type: '{type(response)}'")

    return response.stats

  def GetFilesArchive(self) -> utils.BinaryChunkIterator:
    args = hunt_pb2.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt_id)
    return self._context.SendStreamingRequest("GetHuntFilesArchive", args)

  def GetExportedResults(
      self,
      plugin_name: str,
  ) -> utils.BinaryChunkIterator:
    args = hunt_pb2.ApiGetExportedHuntResultsArgs(
        hunt_id=self.hunt_id, plugin_name=plugin_name
    )
    return self._context.SendStreamingRequest("GetExportedHuntResults", args)

  def GetCollectedTimelines(
      self,
      fmt=timeline_pb2.ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED,
  ) -> utils.BinaryChunkIterator:
    args = timeline_pb2.ApiGetCollectedHuntTimelinesArgs()
    args.hunt_id = self.hunt_id
    args.format = fmt

    return self._context.SendStreamingRequest("GetCollectedHuntTimelines", args)


class HuntRef(HuntBase):
  """Ref to a hunt."""

  def Get(self) -> "Hunt":
    """Fetch hunt's data and return proper Hunt object."""

    args = hunt_pb2.ApiGetHuntArgs(hunt_id=self.hunt_id)
    data = self._context.SendRequest("GetHunt", args)
    if not isinstance(data, hunt_pb2.ApiHunt):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return Hunt(data=data, context=self._context)


class Hunt(HuntBase):
  """Hunt object with fetched data."""

  def __init__(
      self,
      data: hunt_pb2.ApiHunt,
      context: context_lib.GrrApiContext,
  ):
    hunt_id = utils.UrnStringToHuntId(data.urn)

    super().__init__(hunt_id=hunt_id, context=context)

    self.data: hunt_pb2.ApiHunt = data


def CreateHunt(
    flow_name: str,
    flow_args: message.Message,
    hunt_runner_args: flows_pb2.HuntRunnerArgs,
    context: context_lib.GrrApiContext,
) -> Hunt:
  """Creates a new hunt.

  Args:
    flow_name: String with a name of a flow that will run on all the clients in
      the hunt.
    flow_args: Flow arguments to be used. A proto, that depends on a flow.
    hunt_runner_args: flows_pb2.HuntRunnerArgs instance. Used to specify
      description, client_rule_set, output_plugins and other useful hunt
      attributes.
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
    request.flow_args.Pack(flow_args)

  if hunt_runner_args:
    request.hunt_runner_args.CopyFrom(hunt_runner_args)

  data = context.SendRequest("CreateHunt", request)
  if not isinstance(data, hunt_pb2.ApiHunt):
    raise TypeError(f"Unexpected response type: '{type(data)}'")

  return Hunt(data=data, context=context)


def ListHunts(context: context_lib.GrrApiContext) -> utils.ItemsIterator[Hunt]:
  """List all GRR hunts."""

  items = context.SendIteratorRequest("ListHunts", hunt_pb2.ApiListHuntsArgs())
  return utils.MapItemsIterator(
      lambda data: Hunt(data=data, context=context), items
  )


# TODO(hanuszczak): There was an unresolved reference in this function, yet none
# of the test caught it, indicating insufficient test coverage.
def ListHuntApprovals(
    context: context_lib.GrrApiContext,
) -> utils.ItemsIterator[HuntApproval]:
  """List all hunt approvals belonging to requesting user."""
  items = context.SendIteratorRequest(
      "ListHuntApprovals", user_pb2.ApiListHuntApprovalsArgs()
  )

  def MapHuntApproval(data):
    return HuntApproval(data=data, username=context.username, context=context)

  return utils.MapItemsIterator(MapHuntApproval, items)
