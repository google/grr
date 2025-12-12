#!/usr/bin/env python
"""The base class for flow objects."""

import collections
import dataclasses
import functools
import logging
import re
import traceback
import types
from typing import Any, Callable, Collection, Dict, Generic, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Tuple, Type, TypeVar, Union

from google.protobuf import any_pb2
from google.protobuf import message as pb_message
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.registry import FlowRegistry
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import flow_responses
from grr_response_server import hunt
from grr_response_server import notification as notification_lib
from grr_response_server import output_plugin as output_plugin_lib
from grr_response_server import output_plugin_registry
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.models import clients as models_clients
from grr_response_server.models import protodicts as models_protodicts
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_flow_runner
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import mig_output_plugin
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2

FLOW_STARTS = metrics.Counter("flow_starts", fields=[("flow", str)])
FLOW_ERRORS = metrics.Counter(
    "flow_errors",
    fields=[("flow", str), ("is_child", bool), ("exception", str)],
)
FLOW_COMPLETIONS = metrics.Counter("flow_completions", fields=[("flow", str)])
GRR_WORKER_STATES_RUN = metrics.Counter("grr_worker_states_run")
HUNT_OUTPUT_PLUGIN_ERRORS = metrics.Counter(
    "hunt_output_plugin_errors", fields=[("plugin", str)]
)
HUNT_RESULTS_RAN_THROUGH_PLUGIN = metrics.Counter(
    "hunt_results_ran_through_plugin", fields=[("plugin", str)]
)

# We keep this set to avoid increasing the streamz cardinality too much.
_REPORTED_EXCEPTION_NAMES = set()
_MAX_EXCEPTION_NAMES = 100
_METRICS_UNKNOWN_EXCEPTION = "Unknown"
_METRICS_DISCARDED_EXCEPTION = "Discarded"
# Captures the possible exception name (only group). String must have a
# capitalized letter (only letters) followed by an opening parens.
# Should match:
#   * "raise SomeWord("              -> "SomeWord"
#   * "raise package.is_ignored.A("  -> "A"
#   * "raise A(...) raise B(...)"    -> "B"
# Should NOT match:
#   * "raise (", "raise Sep arate(", "raise startsWithLower(", "raise HasNum9("
_LOOKS_LIKE_EXCEPTION = re.compile(
    r"raise\s(?:[a-z0-9_]+\.)*([A-Z][A-Za-z]*)\("
)


def _ExtractExceptionName(text: str) -> str:
  if not text:
    return _METRICS_UNKNOWN_EXCEPTION

  matches = _LOOKS_LIKE_EXCEPTION.findall(text)
  if not matches:
    return _METRICS_UNKNOWN_EXCEPTION

  return matches[-1]


class Error(Exception):
  """Base class for this package's exceptions."""


class FlowError(Error):
  """A generic flow error."""


class RRGUnsupportedError(Error):
  """Raised when a RRG action was invoked on a client without RRG support."""


class RRGVersion(NamedTuple):
  """Tuple representing a RRG version."""

  major: int
  minor: int
  patch: int


# TODO(hanuszczak): Consider refactoring the interface of this class.
class FlowBehaviour(object):
  """A Behaviour is a property of a flow.

  Behaviours advertise what kind of flow this is. The flow can only advertise
  predefined behaviours.
  """

  # A constant which defines all the allowed behaviours and their descriptions.
  LEXICON = {
      # What GUI mode should this flow appear in?
      "BASIC": (
          "Include in the simple UI. This flow is designed for simpler use."
      ),
      "ADVANCED": (
          "Include in advanced UI. This flow takes more experience to use."
      ),
      "DEBUG": "This flow only appears in debug mode.",
  }

  def __init__(self, *args):
    self.set = set()
    for arg in args:
      if arg not in self.LEXICON:
        raise ValueError("Behaviour %s not known." % arg)

      self.set.add(str(arg))

  def __add__(self, other):
    other = str(other)

    if other not in self.LEXICON:
      raise ValueError("Behaviour %s not known." % other)

    return self.__class__(other, *list(self.set))

  def __sub__(self, other):
    other = str(other)

    result = self.set.copy()
    result.discard(other)

    return self.__class__(*list(result))

  def __iter__(self):
    return iter(self.set)


BEHAVIOUR_ADVANCED = FlowBehaviour("ADVANCED")
BEHAVIOUR_BASIC = FlowBehaviour("ADVANCED", "BASIC")
BEHAVIOUR_DEBUG = FlowBehaviour("DEBUG")


# This is a mypy-friendly way of defining named tuples:
# https://mypy.readthedocs.io/en/stable/kinds_of_types.html#named-tuples
class ClientPathArchiveMapping(NamedTuple):
  """Mapping between a client path and a path inside an archive."""

  client_path: db.ClientPath
  archive_path: str


def _ValidateProto(r: Any):
  if not isinstance(r, pb_message.Message):
    raise ValueError(f"Type {type(r)} is not a proto. Analyzing: {r}")


_ProtoArgsT = TypeVar("_ProtoArgsT", bound=pb_message.Message)

# TypeVar `default` is available from Python 3.13, then we can add:
# `default=flows_pb2.DefaultFlowStore`
_ProtoStoreT = TypeVar("_ProtoStoreT", bound=pb_message.Message)

_ProtoProgressT = TypeVar("_ProtoProgressT", bound=pb_message.Message)


class FlowBase(
    Generic[_ProtoArgsT, _ProtoStoreT, _ProtoProgressT], metaclass=FlowRegistry
):
  """The base class for new style flow objects."""

  # Alternatively we can specify a single semantic protobuf that will be used to
  # provide the args.
  args_type = rdf_flows.EmptyFlowArgs
  proto_args_type: Type[_ProtoArgsT] = flows_pb2.EmptyFlowArgs
  # _proto_args acts as a cache for the proto representation of the args.
  # If modified, there will be no effect on the source of truth args
  _proto_args: Optional[_ProtoArgsT]

  # `Store` stores flow-specific data that is persisted across multiple state
  # method invocations. Each flow class should have a dedicated `Store` proto
  # message defined.
  proto_store_type: Type[_ProtoStoreT] = flows_pb2.DefaultFlowStore
  _store: Optional[_ProtoStoreT]

  # An RDFProtoStruct to be produced by the flow's 'progress'
  # property. To be used by the API/UI to report on the flow's progress in a
  # structured way. Can be overridden and has to match GetProgress's
  # return type.
  progress_type = rdf_flow_objects.DefaultFlowProgress
  proto_progress_type: Type[_ProtoProgressT] = flows_pb2.DefaultFlowProgress
  _progress: Optional[_ProtoProgressT]

  # This is used to arrange flows into a tree view
  category = ""
  friendly_name = None

  block_hunt_creation = False

  # Behaviors set attributes of this flow. See FlowBehavior() in
  # grr_response_server/flow.py.
  behaviours = BEHAVIOUR_ADVANCED

  # Tuple, containing the union of all possible types this flow might
  # return. By default, any RDFValue might be returned.
  result_types = (rdfvalue.RDFValue,)
  proto_result_types = (any_pb2.Any,)

  # This is used to control whether to allow RDF-based methods and properties.
  # If set to True, only proto-based methods and properties are allowed.
  only_protos_allowed = False

  _result_metadata: flows_pb2.FlowResultMetadata

  completed_requests: list[flows_pb2.FlowRequest]

  def __init__(self, rdf_flow: rdf_flow_objects.Flow):
    self.rdf_flow = rdf_flow
    self._proto_args = None

    self.flow_requests = []
    self.proto_flow_requests: list[flows_pb2.FlowRequest] = []
    self.flow_responses = []
    self.proto_flow_responses: list[
        Union[flows_pb2.FlowResponse, flows_pb2.FlowStatus]
    ] = []
    self.rrg_requests: list[rrg_pb2.Request] = []
    self.client_action_requests = []
    self.proto_client_action_requests: list[jobs_pb2.GrrMessage] = []
    self.completed_requests: list[flows_pb2.FlowRequest] = []
    self.replies_to_process = []
    self.proto_replies_to_process: list[flows_pb2.FlowResult] = []
    self.replies_to_write = []
    self.proto_replies_to_write: list[flows_pb2.FlowResult] = []

    self._state = None
    self._store = None
    self._progress = None

    self._client_version = None
    self._client_os = None
    self._client_knowledge_base: Optional[knowledge_base_pb2.KnowledgeBase] = (
        None
    )
    self._client_info: Optional[rdf_client.ClientInformation] = None
    self._client_labels: Optional[set[str]] = None

    self._python_agent_support: Optional[bool] = None
    self._rrg_startup: Optional[rrg_startup_pb2.Startup] = None

    self._num_replies_per_type_tag = collections.Counter()
    if rdf_flow.HasField("result_metadata"):
      self._result_metadata = rdf_flow.result_metadata.AsPrimitiveProto()
    else:
      self._result_metadata = flows_pb2.FlowResultMetadata()

  def Start(self) -> None:
    """The first state of the flow."""

  def End(self) -> None:
    """Final state.

    This method is called prior to destruction of the flow.
    """

  def CallState(
      self,
      next_state: str = "",
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      responses: Optional[Sequence[rdf_structs.RDFStruct]] = None,
  ):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked at a later time.

    Args:
       next_state: The state in this flow to be invoked.
       start_time: Start the flow at this time. This delays notification for
         flow processing into the future. Note that the flow may still be
         processed earlier if there are client responses waiting.
       responses: If specified, responses to be passed to the next state.

    Raises:
      ValueError: The next state specified does not exist.
      FlowError: Method shouldn't be used in this flow (only_protos_allowed).
    """
    # Start method is special and not ran with `RunStateMethod` by `StartFlow`.
    # Rather, we call `CallState` directly because it can be scheduled for the
    # future (`start_time`), different than `RunStateMethod` that runs now.
    if self.only_protos_allowed and next_state != "Start":
      raise FlowError(
          "`CallState` is not allowed for flows that only allow protos. Use"
          " `CallStateProto` instead."
      )
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    request_id = self.GetNextOutboundId()
    if responses:
      for index, r in enumerate(responses):
        wrapped_response = rdf_flow_objects.FlowResponse(
            client_id=self.rdf_flow.client_id,
            flow_id=self.rdf_flow.flow_id,
            request_id=request_id,
            response_id=index,
            payload=r,
        )
        self.flow_responses.append(wrapped_response)
      self.flow_responses.append(
          rdf_flow_objects.FlowStatus(
              client_id=self.rdf_flow.client_id,
              flow_id=self.rdf_flow.flow_id,
              request_id=request_id,
              response_id=len(responses) + 1,
              status=rdf_flow_objects.FlowStatus.Status.OK,
          )
      )
      nr_responses_expected = len(responses) + 1
    else:
      nr_responses_expected = 0

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=request_id,
        next_state=next_state,
        start_time=start_time,
        nr_responses_expected=nr_responses_expected,
        needs_processing=True,
    )
    self.flow_requests.append(flow_request)

  def CallStateProto(
      self,
      next_state: str = "",
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      responses: Optional[Sequence[pb_message.Message]] = None,
      request_data: Optional[dict[str, Any]] = None,
  ):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked at a later time.

    Args:
       next_state: The state in this flow to be invoked.
       start_time: Start the flow at this time. This delays notification for
         flow processing into the future. Note that the flow may still be
         processed earlier if there are client responses waiting.
       responses: If specified, responses to be passed to the next state.
       request_data: Supplementary data to be passed to the next state.

    Raises:
      ValueError: The next state specified does not exist.
    """
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    request_id = self.GetNextOutboundId()
    if responses:
      for index, r in enumerate(responses):
        _ValidateProto(r)
        wrapped_response = flows_pb2.FlowResponse(
            client_id=self.rdf_flow.client_id,
            flow_id=self.rdf_flow.flow_id,
            request_id=request_id,
            response_id=index,
        )
        wrapped_response.any_payload.Pack(r)
        # TODO: Remove dynamic `payload` field.
        wrapped_response.payload.Pack(r)
        self.proto_flow_responses.append(wrapped_response)
      self.proto_flow_responses.append(
          flows_pb2.FlowStatus(
              client_id=self.rdf_flow.client_id,
              flow_id=self.rdf_flow.flow_id,
              request_id=request_id,
              response_id=len(responses) + 1,
              status=flows_pb2.FlowStatus.Status.OK,
          )
      )
      nr_responses_expected = len(responses) + 1
    else:
      nr_responses_expected = 0

    flow_request = flows_pb2.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=request_id,
        next_state=next_state,
        nr_responses_expected=nr_responses_expected,
        needs_processing=True,
    )
    if request_data is not None:
      flow_request.request_data.CopyFrom(models_protodicts.Dict(request_data))
    if start_time is not None:
      flow_request.start_time = int(start_time)
    self.proto_flow_requests.append(flow_request)

  def CallStateInline(
      self,
      messages: Optional[
          Sequence[
              Union[
                  rdf_flow_objects.FlowResponse,
                  rdf_flow_objects.FlowStatus,
                  rdf_flow_objects.FlowIterator,
              ],
          ]
      ] = None,
      next_state: str = "",
      request_data: Optional[Mapping[str, Any]] = None,
      responses: Optional[flow_responses.Responses] = None,
  ):
    """Calls a state inline (immediately).

    If `responses` is not specified, `messages` and `request_data` are used to
    create a `flow_responses.Responses` object. Otherwise `responses` is used
    as is.

    Args:
      messages: responses to be passed to the state (only used if `responses` is
        not provided).
      next_state: The state to be called.
      request_data: An arbitrary dict to be passed to the called state (only
        used if `responses` is not provided).
      responses: Responses to pass to the state (as is). If not specified,
        `messages` and `request_data` are used to create a
        `flow_responses.Responses` object.

    Raises:
      FlowError: Method shouldn't be used in this flow (only_protos_allowed).
    """
    if self.only_protos_allowed:
      raise FlowError(
          "`CallStateInline` is not allowed for flows that only allow protos."
          " Use `CallStateInlineProtoWithResponses` or "
      )
    if responses is None:
      responses = flow_responses.FakeResponses(messages, request_data)

    getattr(self, next_state)(responses)

  def CallStateInlineProtoWithResponses(
      self,
      next_state: str = "",
      responses: Optional[flow_responses.Responses[any_pb2.Any]] = None,
  ):
    """Calls a state inline (immediately).

    The state must be annotated with `@UseProto2AnyResponses`.

    Args:
      next_state: The state to be called.
      responses: Responses to pass to the state (as is).
    """

    method = getattr(self, next_state)

    self._CheckMethodExpectsProtos(method, "CallStateInline")

    # Method expects Responses[any_pb2.Any].
    if responses is not None:
      # TODO: Remove this check once flow targets use pytype.
      for r in responses:
        if not isinstance(r, any_pb2.Any):
          raise ValueError(
              f"Expected Responses[any_pb2.Any] but got Responses[{type(r)}]"
          )
    method(responses)

  def CallStateInlineProto(
      self,
      next_state: str = "",
      messages: Optional[Sequence[pb_message.Message]] = None,
      request_data: Optional[Mapping[str, Any]] = None,
  ) -> None:
    """Calls a state inline (immediately).

    The state must be annotated with `@UseProto2AnyResponses`.

    Args:
      next_state: The state to be called.
      messages: responses to be passed to the state.
      request_data: An arbitrary dict to be passed to the called state
    """

    method = getattr(self, next_state)

    self._CheckMethodExpectsProtos(method, "CallStateInline")

    # Use `messages` and make sure they're packed into `any_pb2.Any`s.
    any_msgs: list[any_pb2.Any] = []
    if messages is not None:
      for r in messages:
        _ValidateProto(r)
        if isinstance(r, any_pb2.Any):
          raise ValueError(
              f"Expected unpacked proto message but got an any_pb2.Any: {r}"
          )

        any_msg = any_pb2.Any()
        any_msg.Pack(r)
        any_msgs.append(any_msg)
    responses = flow_responses.FakeResponses(any_msgs, request_data)
    method(responses)

  def CallRRG(
      self,
      action: rrg_pb2.Action,
      args: pb_message.Message,
      # TODO: Use more pythonic filter wrappers.
      filters: Collection[rrg_pb2.Filter] = (),
      next_state: Optional[str] = None,
      context: Optional[dict[str, str]] = None,
  ) -> None:
    """Invokes a RRG action.

    This method will send a request to invoke the specified action on the
    corresponding endpoint. The action results will be queued by the framework
    until a status response is sent back by the agent.

    Args:
      action: The action to invoke on the endpoint.
      args: Arguments to invoke the action with.
      filters: Filters to apply to action results.
      next_state: A flow state method to call with action results.
      context: Dictionary to pass extra data for the state method.

    Raises:
      RRGUnsupportedError: If the target client does not support RRG.
    """
    if not self.rrg_support:
      raise RRGUnsupportedError()

    if context is None:
      context = {}

    request_id = self.GetNextOutboundId()

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = self.rdf_flow.client_id
    flow_request.flow_id = self.rdf_flow.flow_id
    flow_request.request_id = request_id

    if next_state:
      flow_request.next_state = next_state

    for key, value in context.items():
      kv = flow_request.request_data.dat.add()
      kv.k.string = key
      kv.v.string = value

    rrg_request = rrg_pb2.Request()
    rrg_request.flow_id = int(self.rdf_flow.flow_id, 16)
    rrg_request.request_id = request_id
    rrg_request.action = action
    rrg_request.args.Pack(args)

    for rrg_filter in filters:
      rrg_request.filters.append(rrg_filter)

    # TODO: Add support for limits.

    self.proto_flow_requests.append(flow_request)
    self.rrg_requests.append(rrg_request)

  @dataclasses.dataclass
  class _ResourceLimits:
    cpu_limit_ms: Optional[int]
    network_bytes_limit: Optional[int]
    runtime_limit_us: Optional[int]

  def _GetAndCheckResourceLimits(self) -> _ResourceLimits:
    """Calculates and checks if the flow has exceeded any resource limits.

    Returns:
      A _ResourceLimits object with the calculated limits.

    Raises:
      FlowResourcesExceededError: If any resource limit has been exceeded.
    """
    cpu_limit_ms = None
    network_bytes_limit = None
    runtime_limit_us = (
        self.rdf_flow.runtime_limit_us.SerializeToWireFormat()
        if self.rdf_flow.HasField("runtime_limit_us")
        else None
    )

    if self.rdf_flow.cpu_limit:
      cpu_usage = self.rdf_flow.cpu_time_used
      cpu_limit_ms = 1000 * max(
          self.rdf_flow.cpu_limit
          - cpu_usage.user_cpu_time
          - cpu_usage.system_cpu_time,
          0,
      )

      if cpu_limit_ms == 0:
        raise flow.FlowResourcesExceededError(
            "CPU limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
            )
        )

    if self.rdf_flow.network_bytes_limit:
      network_bytes_limit = max(
          self.rdf_flow.network_bytes_limit - self.rdf_flow.network_bytes_sent,
          0,
      )
      if network_bytes_limit == 0:
        raise flow.FlowResourcesExceededError(
            "Network limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
            )
        )

    if self.rdf_flow.runtime_limit_us and self.rdf_flow.runtime_us:
      if self.rdf_flow.runtime_us < self.rdf_flow.runtime_limit_us:
        rdf_duration = self.rdf_flow.runtime_limit_us - self.rdf_flow.runtime_us
        runtime_limit_us = rdf_duration.SerializeToWireFormat()
      else:
        raise flow.FlowResourcesExceededError(
            "Runtime limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
            )
        )

    return self._ResourceLimits(
        cpu_limit_ms=cpu_limit_ms,
        network_bytes_limit=network_bytes_limit,
        runtime_limit_us=runtime_limit_us,
    )

  def CallClient(
      self,
      action_cls: Type[server_stubs.ClientActionStub],
      request: Optional[rdfvalue.RDFValue] = None,
      next_state: Optional[str] = None,
      callback_state: Optional[str] = None,
      request_data: Optional[Mapping[str, Any]] = None,
  ):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run action may
    send back many responses that will be queued by the framework until a status
    message is sent by the client. The status message will cause the entire
    transaction to be committed to the specified state.

    Args:
       action_cls: The function to call on the client.
       request: The request to send to the client. Must be of the correct type
         for the action.
       next_state: The state in this flow, that responses to this message should
         go to.
       callback_state: (optional) The state to call whenever a new response is
         arriving.
       request_data: A dict which will be available in the RequestState
         protobuf. The Responses object maintains a reference to this protobuf
         for use in the execution of the state method. (so you can access this
         data by responses.request).

    Raises:
       ValueError: The request passed to the client does not have the correct
                   type.
      FlowError: Method shouldn't be used in this flow (only_protos_allowed).
    """
    if self.only_protos_allowed:
      raise FlowError(
          "`CallClient` is not allowed for flows that only allow protos. Use"
          " `CallClientProto` instead."
      )
    try:
      action_identifier = action_registry.ID_BY_ACTION_STUB[action_cls]
    except KeyError:
      raise ValueError("Action class %s not known." % action_cls) from None

    if action_cls.in_rdfvalue is None:
      if request:
        raise ValueError("Client action %s does not expect args." % action_cls)
    else:
      # Verify that the request type matches the client action requirements.
      if not isinstance(request, action_cls.in_rdfvalue):
        raise ValueError(
            "Client action expected %s but got %s"
            % (action_cls.in_rdfvalue, type(request))
        )

    outbound_id = self.GetNextOutboundId()

    # Create a flow request.
    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=outbound_id,
        next_state=next_state,
        callback_state=callback_state,
    )

    if request_data is not None:
      flow_request.request_data = rdf_protodict.Dict().FromDict(request_data)

    limits = self._GetAndCheckResourceLimits()

    stub = action_registry.ACTION_STUB_BY_ID[action_identifier]
    client_action_request = rdf_flows.GrrMessage(
        session_id="%s/%s" % (self.rdf_flow.client_id, self.rdf_flow.flow_id),
        name=stub.__name__,
        request_id=outbound_id,
        payload=request,
        network_bytes_limit=limits.network_bytes_limit,
        runtime_limit_us=limits.runtime_limit_us,
    )
    if limits.cpu_limit_ms is not None:
      client_action_request.cpu_limit = limits.cpu_limit_ms / 1000.0

    self.flow_requests.append(flow_request)
    self.client_action_requests.append(client_action_request)

  def CallClientProto(
      self,
      action_cls: Type[server_stubs.ClientActionStub],
      action_args: Optional[pb_message.Message] = None,
      next_state: Optional[str] = None,
      callback_state: Optional[str] = None,
      request_data: Optional[dict[str, Any]] = None,
  ):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run action may
    send back many responses that will be queued by the framework until a status
    message is sent by the client. The status message will cause the entire
    transaction to be committed to the specified state.

    Args:
       action_cls: The function to call on the client.
       action_args: The arguments to send to the client. Must be of the correct
         type for the action.
       next_state: The state in this flow, that responses to this message should
         go to.
       callback_state: (optional) The state to call whenever a new response is
         arriving.
       request_data: A dict which will be available in the RequestState
         protobuf. The Responses object maintains a reference to this protobuf
         for use in the execution of the state method. (so you can access this
         data by responses.request).

    Raises:
       ValueError: The client action does not exist/is not registered.
       TypeError: The arguments passed to the client does not have the correct
                  type.
    """
    try:
      action_registry.ID_BY_ACTION_STUB[action_cls]
    except KeyError:
      raise ValueError("Action class %s not known." % action_cls) from None

    if action_cls.in_proto is None and action_args:
      raise ValueError(
          f"Client action {action_cls.__name__} does not expect args yet some"
          f" were provided: {action_args}"
      )
    elif action_cls.in_proto is not None:
      if action_args is None:
        raise ValueError(
            f"Client action {action_cls.__name__} expects args, but none were"
            " provided."
        )
      # Verify that the action_args type matches the client action requirements.
      if not isinstance(action_args, action_cls.in_proto):
        raise ValueError(
            "Client action expected %s but got %s"
            % (action_cls.in_proto, type(action_args))
        )

    outbound_id = self.GetNextOutboundId()

    # Create a flow request.
    flow_request = flows_pb2.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=outbound_id,
        next_state=next_state,
        callback_state=callback_state,
    )

    if request_data is not None:
      flow_request.request_data.CopyFrom(
          mig_protodict.FromNativeDictToProtoDict(request_data)
      )

    limits = self._GetAndCheckResourceLimits()
    client_action_request = jobs_pb2.GrrMessage(
        session_id="%s/%s" % (self.rdf_flow.client_id, self.rdf_flow.flow_id),
        name=action_cls.__name__,
        request_id=outbound_id,
        network_bytes_limit=limits.network_bytes_limit,
    )
    if limits.cpu_limit_ms is not None:
      client_action_request.cpu_limit = limits.cpu_limit_ms / 1000.0
    if limits.runtime_limit_us is not None:
      client_action_request.runtime_limit_us = limits.runtime_limit_us

    if action_args:
      # We rely on the fact that the in_proto and in_rdfvalue fields in the stub
      # represent the same type. That is:
      #     cls.in_rdfvalue.protobuf == cls.in_proto
      # We use that to manually build the proto as prescribed by the GrrMessage
      # RDF class.
      models_clients.SetGrrMessagePayload(
          client_action_request, action_cls.in_rdfvalue.__name__, action_args
      )

    self.proto_flow_requests.append(flow_request)
    self.proto_client_action_requests.append(client_action_request)

  def CallFlow(
      self,
      flow_name: Optional[str] = None,
      next_state: Optional[str] = None,
      request_data: Optional[Mapping[str, Any]] = None,
      output_plugins: Optional[
          Sequence[rdf_output_plugin.OutputPluginDescriptor]
      ] = None,
      flow_args: Optional[rdf_structs.RDFStruct] = None,
  ) -> str:
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: Any dict provided here will be available in the
         RequestState protobuf. The Responses object maintains a reference to
         this protobuf for use in the execution of the state method. (so you can
         access this data by responses.request). There is no format mandated on
         this data but it may be a serialized protobuf.
       output_plugins: A list of output plugins to use for this flow.
       flow_args: Arguments for the child flow.

    Returns:
       The flow_id of the child flow which was created.

    Raises:
      ValueError: The requested next state does not exist.
      FlowError: Method shouldn't be used in this flow (only_protos_allowed).
    """
    if self.only_protos_allowed:
      raise FlowError(
          "`CallFlow` is not allowed for flows that only allow protos. Use"
          " `CallFlowProto` instead."
      )
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=self.GetNextOutboundId(),
        next_state=next_state,
    )

    if request_data is not None:
      flow_request.request_data = rdf_protodict.Dict().FromDict(request_data)

    self.flow_requests.append(flow_request)

    flow_cls = FlowRegistry.FlowClassByName(flow_name)

    return flow.StartFlow(
        client_id=self.rdf_flow.client_id,
        flow_cls=flow_cls,
        parent=flow.FlowParent.FromFlow(self),
        output_plugins=output_plugins,
        flow_args=flow_args,
        start_at=None,  # Start immediately in this worker.
        disable_rrg_support=self.rdf_flow.disable_rrg_support,
    )

  def CallFlowProto(
      self,
      flow_name: Optional[str] = None,
      next_state: Optional[str] = None,
      request_data: Optional[dict[str, Any]] = None,
      output_plugins: Optional[
          Sequence[rdf_output_plugin.OutputPluginDescriptor]
      ] = None,
      flow_args: Optional[pb_message.Message] = None,
  ) -> str:
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: Any dict provided here will be available in the
         RequestState protobuf. The Responses object maintains a reference to
         this protobuf for use in the execution of the state method. (so you can
         access this data by responses.request). There is no format mandated on
         this data but it may be a serialized protobuf.
       output_plugins: A list of output plugins to use for this flow.
       flow_args: Arguments for the child flow.

    Returns:
       The flow_id of the child flow which was created.

    Raises:
      ValueError: The requested next state does not exist.
    """
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    flow_request = flows_pb2.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=self.GetNextOutboundId(),
        next_state=next_state,
    )

    if request_data is not None:
      flow_request.request_data.CopyFrom(
          mig_protodict.FromNativeDictToProtoDict(request_data)
      )

    self.proto_flow_requests.append(flow_request)

    flow_cls = FlowRegistry.FlowClassByName(flow_name)

    rdf_flow_args = None
    if flow_args:
      if flow_cls.args_type.protobuf != type(flow_args):
        raise ValueError(
            f"Flow {flow_name} expects args of type"
            f" {flow_cls.args_type.protobuf} but got {type(flow_args)}"
        )
      # We try on a best-effort basis to convert the flow args to RDFValue.
      rdf_flow_args = flow_cls.args_type.FromSerializedBytes(
          flow_args.SerializeToString()
      )

    # TODO: Allow `StartFlow` to take proto args in.
    return flow.StartFlow(
        client_id=self.rdf_flow.client_id,
        flow_cls=flow_cls,
        parent=flow.FlowParent.FromFlow(self),
        output_plugins=output_plugins,
        flow_args=rdf_flow_args,
        start_at=None,  # Start immediately in this worker.
        disable_rrg_support=self.rdf_flow.disable_rrg_support,
    )

  def SendReply(
      self, response: rdfvalue.RDFValue, tag: Optional[str] = None
  ) -> None:
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is saved to the database
    as flow result.

    Args:
      response: An RDFValue() instance to be sent to the parent.
      tag: If specified, tag the result with this tag.

    Raises:
      ValueError: If responses is not of the correct type.
      FlowError: Method shouldn't be used in this flow (only_protos_allowed).
    """
    if self.only_protos_allowed:
      raise FlowError(
          "`SendReply` is not allowed for flows that only allow protos. Use"
          " `SendReplyProto` instead."
      )
    if not isinstance(response, rdfvalue.RDFValue):
      raise ValueError(
          f"SendReply can only send RDFValues, got {type(response)}"
      )

    if not any(isinstance(response, t) for t in self.result_types):
      logging.warning(
          "Flow %s sends response of unexpected type %s.",
          type(self).__name__,
          type(response).__name__,
      )

    reply = rdf_flow_objects.FlowResult(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        hunt_id=self.rdf_flow.parent_hunt_id,
        payload=response,
        tag=tag,
    )
    if self.rdf_flow.parent_flow_id:

      if isinstance(response, rdf_structs.RDFProtoStruct):
        rdf_packed_payload = rdf_structs.AnyValue.Pack(response)
      else:
        # Should log for `GetMBR` flow which returns `RDFBytes`.
        # Might fail for others that we're unaware but also return primitives.
        logging.error(
            "Flow %s sends response of unexpected type %s.",
            self.__class__.__name__,
            type(response),
        )
        rdf_packed_payload = None

      flow_response = rdf_flow_objects.FlowResponse(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          payload=response,
          any_payload=rdf_packed_payload,
          flow_id=self.rdf_flow.parent_flow_id,
          tag=tag,
      )

      self.flow_responses.append(flow_response)
      # For nested flows we want the replies to be written,
      # but not to be processed by output plugins.
      self.replies_to_write.append(reply)
    else:
      self.replies_to_write.append(reply)
      self.replies_to_process.append(reply)

    self.rdf_flow.num_replies_sent += 1

    # Keeping track of result types/tags in a plain Python
    # _num_replies_per_type_tag dict. In RDFValues/proto2 we have to represent
    # dictionaries as lists of key-value pairs (i.e. there's no library
    # support for dicts as data structures). Hence, updating a key would require
    # iterating over the pairs - which might get expensive for hundreds of
    # thousands of results. To avoid the issue we keep a non-serialized Python
    # dict to be later accumulated into a serializable FlowResultCount
    # in PersistState().
    key = (type(response).__name__, tag or "")
    self._num_replies_per_type_tag[key] += 1

  def SendReplyProto(
      self,
      response: pb_message.Message,
      tag: Optional[str] = None,
  ) -> None:
    """Allows this flow to save a flow result to the database.

    In case of a child flow, results are also returned to the parent flow.

    Args:
      response: A protobuf instance to be sent to the parent.
      tag: If specified, tag the result with this tag.

    Raises:
      TypeError: If responses is not of the correct type.
    """
    if not isinstance(response, pb_message.Message):
      raise TypeError(
          f"SendReplyProto can only send Protobufs, got {type(response)}"
      )

    if not any(isinstance(response, t) for t in self.proto_result_types):
      raise TypeError(
          f"Flow {type(self).__name__} sends response of unexpected type"
          f" {type(response).__name__}. Expected one of"
          f" {self.proto_result_types}",
      )

    reply = flows_pb2.FlowResult(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        hunt_id=self.rdf_flow.parent_hunt_id,
        tag=tag,
    )
    reply.payload.Pack(response)
    self.proto_replies_to_write.append(reply)

    if self.rdf_flow.parent_flow_id:
      res = flows_pb2.FlowResponse(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          flow_id=self.rdf_flow.parent_flow_id,
          tag=tag,
      )
      res.payload.Pack(response)
      res.any_payload.Pack(response)
      self.proto_flow_responses.append(res)
    else:
      # We only want to process replies with output plugins if this is
      # a parent flow (not nested).
      self.proto_replies_to_process.append(reply)

    self.rdf_flow.num_replies_sent += 1

    # Keeping track of result types/tags in a plain Python
    # _num_replies_per_type_tag dict. In RDFValues/proto2 we have to represent
    # dictionaries as lists of key-value pairs (i.e. there's no library
    # support for dicts as data structures). Hence, updating a key would require
    # iterating over the pairs - which might get expensive for hundreds of
    # thousands of results. To avoid the issue we keep a non-serialized Python
    # dict to be later accumulated into a serializable FlowResultCount
    # in PersistState().
    key = (type(response).__name__, tag or "")
    self._num_replies_per_type_tag[key] += 1

  def SaveResourceUsage(self, status: rdf_flow_objects.FlowStatus) -> None:
    """Method to tally resources."""
    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time
    self.rdf_flow.cpu_time_used.user_cpu_time += user_cpu
    self.rdf_flow.cpu_time_used.system_cpu_time += system_cpu

    self.rdf_flow.network_bytes_sent += status.network_bytes_sent

    if not self.rdf_flow.runtime_us:
      self.rdf_flow.runtime_us = rdfvalue.Duration(0)

    if status.runtime_us:
      self.rdf_flow.runtime_us += status.runtime_us

    if self.rdf_flow.cpu_limit:
      user_cpu_total = self.rdf_flow.cpu_time_used.user_cpu_time
      system_cpu_total = self.rdf_flow.cpu_time_used.system_cpu_time
      if self.rdf_flow.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our CPU time limit, stop this flow.
        raise flow.FlowResourcesExceededError(
            "CPU limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
            )
        )

    if (
        self.rdf_flow.network_bytes_limit
        and self.rdf_flow.network_bytes_limit < self.rdf_flow.network_bytes_sent
    ):
      # We have exceeded our byte limit, stop this flow.
      raise flow.FlowResourcesExceededError(
          "Network bytes limit exceeded {} {}.".format(
              self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
          )
      )

    if (
        self.rdf_flow.runtime_limit_us
        and self.rdf_flow.runtime_limit_us < self.rdf_flow.runtime_us
    ):
      raise flow.FlowResourcesExceededError(
          "Runtime limit exceeded {} {}.".format(
              self.rdf_flow.flow_class_name, self.rdf_flow.flow_id
          )
      )

  def Error(
      self,
      error_message: Optional[str] = None,
      backtrace: Optional[str] = None,
  ) -> None:
    """Terminates this flow with an error."""
    flow_name = self.__class__.__name__
    is_child = bool(self.rdf_flow.parent_flow_id)
    exception_name = _ExtractExceptionName(
        f"{error_message or ''}{backtrace or ''}"
    )

    if (
        exception_name not in _REPORTED_EXCEPTION_NAMES
        and len(_REPORTED_EXCEPTION_NAMES) > _MAX_EXCEPTION_NAMES
    ):
      # We're already over the limit, discard the exception name.
      logging.info(
          "Skipping streamz reporting for %s (is_child=%s): %s",
          flow_name,
          is_child,
          exception_name,
      )
      FLOW_ERRORS.Increment(
          fields=[flow_name, is_child, _METRICS_DISCARDED_EXCEPTION]
      )
    else:
      # Either it's already reported or we're still within the limit.
      _REPORTED_EXCEPTION_NAMES.add(exception_name)
      FLOW_ERRORS.Increment(fields=[flow_name, is_child, exception_name])

    client_id = self.rdf_flow.client_id
    flow_id = self.rdf_flow.flow_id

    # backtrace is set for unexpected failures caught in a wildcard except
    # branch, thus these should be logged as error. backtrace is None for
    # faults that are anticipated in flows, thus should only be logged as
    # warning.
    if backtrace:
      logging.error(
          "Error in flow %s on %s: %s, %s",
          flow_id,
          client_id,
          error_message,
          backtrace,
      )
    else:
      logging.warning(
          "Error in flow %s on %s: %s:", flow_id, client_id, error_message
      )

    if self.rdf_flow.parent_flow_id or self.rdf_flow.parent_hunt_id:
      status_msg = rdf_flow_objects.FlowStatus(
          status=rdf_flow_objects.FlowStatus.Status.ERROR,
          client_id=client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          cpu_time_used=self.rdf_flow.cpu_time_used,
          network_bytes_sent=self.rdf_flow.network_bytes_sent,
          runtime_us=self.rdf_flow.runtime_us,
          error_message=error_message,
          flow_id=self.rdf_flow.parent_flow_id,
          backtrace=backtrace,
      )

      if self.rdf_flow.parent_flow_id:
        self.flow_responses.append(status_msg)
      elif self.rdf_flow.parent_hunt_id:
        hunt.StopHuntIfCPUOrNetworkLimitsExceeded(self.rdf_flow.parent_hunt_id)

    self.rdf_flow.flow_state = self.rdf_flow.FlowState.ERROR
    if backtrace is not None:
      self.rdf_flow.backtrace = backtrace
    if error_message is not None:
      self.rdf_flow.error_message = error_message

    self.NotifyCreatorOfError()

  def NotifyCreatorOfError(self) -> None:
    if self.ShouldSendNotifications():
      client_id = self.rdf_flow.client_id
      flow_id = self.rdf_flow.flow_id

      flow_ref = objects_pb2.FlowReference(client_id=client_id, flow_id=flow_id)
      notification_lib.Notify(
          self.creator,
          rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_FAILED,
          "Flow %s on %s terminated due to error" % (flow_id, client_id),
          objects_pb2.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.FLOW,
              flow=flow_ref,
          ),
      )

  def _ClearAllRequestsAndResponses(self) -> None:
    """Clears all requests and responses."""
    client_id = self.rdf_flow.client_id
    flow_id = self.rdf_flow.flow_id

    # Remove all requests queued for deletion that we delete in the call below.
    self.completed_requests = [
        r
        for r in self.completed_requests
        if r.client_id != client_id or r.flow_id != flow_id
    ]

    data_store.REL_DB.DeleteAllFlowRequestsAndResponses(client_id, flow_id)

  def NotifyAboutEnd(self) -> None:
    """Notify about the end of the flow."""
    # Sum up number of replies to write with the number of already
    # written results.
    num_results = (
        len(self.replies_to_write)
        + len(self.proto_replies_to_write)
        + data_store.REL_DB.CountFlowResults(
            self.rdf_flow.client_id, self.rdf_flow.flow_id
        )
    )
    flow_ref = objects_pb2.FlowReference(
        client_id=self.rdf_flow.client_id, flow_id=self.rdf_flow.flow_id
    )
    notification_lib.Notify(
        self.creator,
        objects_pb2.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        "Flow %s completed with %d %s"
        % (
            self.__class__.__name__,
            num_results,
            num_results == 1 and "result" or "results",
        ),
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.FLOW, flow=flow_ref
        ),
    )

  def MarkDone(self, status=None):
    """Marks this flow as done."""
    FLOW_COMPLETIONS.Increment(fields=[self.__class__.__name__])

    # Notify our parent flow or hunt that we are done (if there's a parent flow
    # or hunt).
    if self.rdf_flow.parent_flow_id or self.rdf_flow.parent_hunt_id:
      status = rdf_flow_objects.FlowStatus(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          status=rdf_flow_objects.FlowStatus.Status.OK,
          cpu_time_used=self.rdf_flow.cpu_time_used,
          network_bytes_sent=self.rdf_flow.network_bytes_sent,
          runtime_us=self.rdf_flow.runtime_us,
          flow_id=self.rdf_flow.parent_flow_id,
      )
      if self.rdf_flow.parent_flow_id:
        self.flow_responses.append(status)
      elif self.rdf_flow.parent_hunt_id:
        hunt.StopHuntIfCPUOrNetworkLimitsExceeded(self.rdf_flow.parent_hunt_id)

    self.rdf_flow.flow_state = self.rdf_flow.FlowState.FINISHED

    if self.ShouldSendNotifications():
      self.NotifyAboutEnd()

  def Log(self, format_str: str, *args: object) -> None:
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    # If there are no formatting arguments given, we do not format the message.
    # This behaviour is in-line with `logging.*` functions and allows one to log
    # messages with `%` without weird workarounds.
    if not args:
      message = format_str
    else:
      message = format_str % args

    log_entry = flows_pb2.FlowLogEntry(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        hunt_id=self.rdf_flow.parent_hunt_id,
        message=message,
    )
    data_store.REL_DB.WriteFlowLogEntry(log_entry)

  def RunStateMethod(
      self,
      method_name: str,
      request: Optional[rdf_flow_objects.FlowRequest] = None,
      responses: Optional[
          Sequence[
              Union[
                  rdf_flow_objects.FlowResponse,
                  rdf_flow_objects.FlowStatus,
                  rdf_flow_objects.FlowIterator,
              ]
          ]
      ] = None,
  ) -> None:
    """Completes the request by calling the state method.

    Args:
      method_name: The name of the state method to call.
      request: A RequestState protobuf.
      responses: A list of FlowResponses, FlowStatuses, and FlowIterators
        responding to the request.

    Raises:
      FlowError: Processing time for the flow has expired.
    """
    client_id = self.rdf_flow.client_id

    deadline = self.rdf_flow.processing_deadline
    if deadline and rdfvalue.RDFDatetime.Now() > deadline:
      raise FlowError(
          "Processing time for flow %s on %s expired."
          % (self.rdf_flow.flow_id, self.rdf_flow.client_id)
      )

    self.rdf_flow.current_state = method_name
    if request and responses:
      logging.debug(
          "Running %s for flow %s on %s, %d responses.",
          method_name,
          self.rdf_flow.flow_id,
          client_id,
          len(responses),
      )
    else:
      logging.debug(
          "Running %s for flow %s on %s",
          method_name,
          self.rdf_flow.flow_id,
          client_id,
      )

    try:
      try:
        method = getattr(self, method_name)
      except AttributeError:
        raise ValueError(
            "Flow %s has no state method %s"
            % (self.__class__.__name__, method_name)
        ) from None

      # Prepare a responses object for the state method to use:
      # If a method is annotated with both `_proto2_any_responses` and
      # `_proto2_any_responses_callback`, the latter takes precedence,
      # treating the `status` message as optional. This way, a state method can
      # be used both for incremental and non-incremental request processing.
      if responses is not None and (
          self._IsAnnotatedWithProto2AnyResponsesCallback(method)
      ):
        responses = (
            flow_responses.Responses.FromResponsesProto2AnyWithOptionalStatus(
                responses, request
            )
        )
      elif responses is not None and (
          self._IsAnnotatedWithProto2AnyResponses(method)
      ):
        responses = flow_responses.Responses.FromResponsesProto2Any(
            responses, request
        )
      else:
        responses = flow_responses.Responses.FromResponses(
            request=request, responses=responses
        )

      if responses.status is not None:
        self.SaveResourceUsage(responses.status)

      GRR_WORKER_STATES_RUN.Increment()

      if method_name == "Start":
        FLOW_STARTS.Increment(fields=[self.rdf_flow.flow_class_name])
        method()
      elif method_name == "End":
        method()
      else:
        method(responses)

      if self.proto_replies_to_process:
        self._ProcessRepliesWithOutputPluginProto(self.proto_replies_to_process)
        # TODO: Remove when no more RDF-based output plugins exist.
        rdf_replies = [
            mig_flow_objects.ToRDFFlowResult(r)
            for r in self.proto_replies_to_process
        ]
        self.replies_to_process.extend(rdf_replies)
        self.proto_replies_to_process = []

      # TODO: Remove when no more RDF-based output plugins exist.
      if self.replies_to_process:
        if self.rdf_flow.parent_hunt_id and not self.rdf_flow.parent_flow_id:
          self._ProcessRepliesWithHuntOutputPlugins(self.replies_to_process)
        else:
          self._ProcessRepliesWithFlowOutputPlugins(self.replies_to_process)

        self.replies_to_process = []

    except flow.FlowResourcesExceededError as e:
      logging.info(
          "Flow %s on %s exceeded resource limits: %s.",
          self.rdf_flow.flow_id,
          client_id,
          str(e),
      )
      self.Error(error_message=str(e))
    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except
      msg = str(e)
      self.Error(error_message=msg, backtrace=traceback.format_exc())

  def ProcessAllReadyRequests(self) -> tuple[int, int]:
    """Processes all requests that are due to run.

    Returns:
      (processed, incrementally_processed) The number of completed processed
      requests and the number of incrementally processed ones.
    """
    request_dict = data_store.REL_DB.ReadFlowRequests(
        self.rdf_flow.client_id,
        self.rdf_flow.flow_id,
    )

    completed_requests = FindCompletedRequestsToProcess(
        request_dict,
        self.rdf_flow.next_request_to_process,
    )
    incremental_requests = FindIncrementalRequestsToProcess(
        request_dict,
        self.rdf_flow.next_request_to_process,
    )
    # When dealing with a callback flow, count all incremental requests even if
    # `incremental_requests` is empty, as it's expected that messages might
    # arrive in the wrong order and therefore not always be suitable for
    # processing.
    num_incremental = sum(
        [1 for _, (req, _) in request_dict.items() if req.callback_state]
    )

    next_response_id_map = {}
    # Process incremental requests' updates first. Incremental requests have
    # the 'callback_state' attribute set and the callback state is called
    # every time new responses arrive. Note that the id of the next expected
    # response is kept in request's 'next_response_id' attribute to guarantee
    # that responses are going to be processed in the right order.
    for request, responses in incremental_requests:
      request = mig_flow_objects.ToRDFFlowRequest(request)
      if not self.IsRunning():
        break

      # Responses have to be processed in the correct order, no response
      # can be skipped.
      rdf_responses = []
      for r in responses:
        if isinstance(r, flows_pb2.FlowResponse):
          rdf_responses.append(mig_flow_objects.ToRDFFlowResponse(r))
        if isinstance(r, flows_pb2.FlowStatus):
          rdf_responses.append(mig_flow_objects.ToRDFFlowStatus(r))
        if isinstance(r, flows_pb2.FlowIterator):
          rdf_responses.append(mig_flow_objects.ToRDFFlowIterator(r))

      if rdf_responses:
        # We do not sent incremental updates for FlowStatus updates.
        # TODO: Check if the id of last message in to_process, the
        # FlowStatus, is important to keep for the next_response_id map, as the
        # flow is anyways complete then. If not we can skip adding the
        # FlowStatus to the `to_process` list instead of filtering it out here.
        flow_updates = [
            r
            for r in rdf_responses
            if not isinstance(r, rdf_flow_objects.FlowStatus)
        ]

        if flow_updates:
          self.RunStateMethod(request.callback_state, request, flow_updates)

        # If the request was processed, update the next_response_id.
        next_response_id_map[request.request_id] = (
            rdf_responses[-1].response_id + 1
        )

    if next_response_id_map:
      data_store.REL_DB.UpdateIncrementalFlowRequests(
          self.rdf_flow.client_id, self.rdf_flow.flow_id, next_response_id_map
      )

    # Process completed requests.
    #
    # If the flow gets a bunch of requests to process and processing one of
    # them leads to flow termination, other requests should be ignored.
    # Hence: self.IsRunning check in the loop's condition.
    for request, responses in completed_requests:
      if not self.IsRunning():
        break

      rdf_request = mig_flow_objects.ToRDFFlowRequest(request)
      rdf_responses = []
      for r in responses:
        if isinstance(r, flows_pb2.FlowResponse):
          rdf_responses.append(mig_flow_objects.ToRDFFlowResponse(r))
        if isinstance(r, flows_pb2.FlowStatus):
          rdf_responses.append(mig_flow_objects.ToRDFFlowStatus(r))
        if isinstance(r, flows_pb2.FlowIterator):
          rdf_responses.append(mig_flow_objects.ToRDFFlowIterator(r))
      # If there's not even a `Status` response, we send `None` as response.
      if not rdf_responses:
        rdf_responses = None
      self.RunStateMethod(request.next_state, rdf_request, rdf_responses)
      self.rdf_flow.next_request_to_process += 1
      self.completed_requests.append(request)

    if (
        completed_requests
        and self.IsRunning()
        and not self.outstanding_requests
    ):
      self.RunStateMethod("End")
      if (
          self.rdf_flow.flow_state == self.rdf_flow.FlowState.RUNNING
          and not self.outstanding_requests
      ):
        self.MarkDone()

    self.PersistState()

    if not self.IsRunning():
      # All requests and responses can now be deleted.
      self._ClearAllRequestsAndResponses()

    return len(completed_requests), num_incremental

  @property
  def outstanding_requests(self) -> int:
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return (
        self.rdf_flow.next_outbound_id - self.rdf_flow.next_request_to_process
    )

  def GetNextOutboundId(self) -> int:
    my_id = self.rdf_flow.next_outbound_id
    self.rdf_flow.next_outbound_id += 1
    return my_id

  def GetCurrentOutboundId(self) -> int:
    return self.rdf_flow.next_outbound_id - 1

  def GetNextResponseId(self) -> int:
    self.rdf_flow.response_count += 1
    return self.rdf_flow.response_count

  def FlushQueuedMessages(self) -> None:
    """Flushes queued messages."""
    # TODO(amoser): This could be done in a single db call, might be worth
    # optimizing.

    if self.flow_requests or self.proto_flow_requests:
      all_requests = [
          mig_flow_objects.ToProtoFlowRequest(r) for r in self.flow_requests
      ] + self.proto_flow_requests
      # We make a single DB call to write all requests. Contrary to what the
      # name suggests, this method does more than writing the requests to the
      # DB. It also tallies the flows that need processing and updates the
      # next request to process. Writing the requests in separate calls can
      # interfere with this process.
      data_store.REL_DB.WriteFlowRequests(all_requests)
      self.flow_requests = []
      self.proto_flow_requests = []

    if self.flow_responses:
      flow_responses_proto = []
      for r in self.flow_responses:
        if isinstance(r, rdf_flow_objects.FlowResponse):
          flow_responses_proto.append(mig_flow_objects.ToProtoFlowResponse(r))
        if isinstance(r, rdf_flow_objects.FlowStatus):
          flow_responses_proto.append(mig_flow_objects.ToProtoFlowStatus(r))
        if isinstance(r, rdf_flow_objects.FlowIterator):
          flow_responses_proto.append(mig_flow_objects.ToProtoFlowIterator(r))
      data_store.REL_DB.WriteFlowResponses(flow_responses_proto)
      self.flow_responses = []

    if self.proto_flow_responses:
      data_store.REL_DB.WriteFlowResponses(self.proto_flow_responses)
      self.proto_flow_responses = []

    if self.client_action_requests:
      client_id = self.rdf_flow.client_id
      for request in self.client_action_requests:
        fleetspeak_utils.SendGrrMessageThroughFleetspeak(
            client_id,
            request,
            self.client_labels,
        )

      self.client_action_requests = []

    if self.proto_client_action_requests:
      client_id = self.rdf_flow.client_id
      for request in self.proto_client_action_requests:
        fleetspeak_utils.SendGrrMessageProtoThroughFleetspeak(
            client_id,
            request,
            self.client_labels,
        )
      self.proto_client_action_requests = []

    for request in self.rrg_requests:
      fleetspeak_utils.SendRrgRequest(
          self.rdf_flow.client_id,
          request,
          self.client_labels,
      )

    self.rrg_requests = []

    if self.completed_requests:
      data_store.REL_DB.DeleteFlowRequests(self.completed_requests)
      self.completed_requests = []

    if self.proto_replies_to_write or self.replies_to_write:
      all_results = self.proto_replies_to_write + [
          mig_flow_objects.ToProtoFlowResult(r) for r in self.replies_to_write
      ]
      # Write flow results to REL_DB, even if the flow is a nested flow.
      data_store.REL_DB.WriteFlowResults(all_results)
      if self.rdf_flow.parent_hunt_id:
        hunt.StopHuntIfCPUOrNetworkLimitsExceeded(self.rdf_flow.parent_hunt_id)
      self.proto_replies_to_write = []
      self.replies_to_write = []

  def _ProcessRepliesWithOutputPluginProto(
      self, replies: Sequence[flows_pb2.FlowResult]
  ) -> None:
    """Processes flow replies using configured proto-based output plugins.

    This method iterates through the flow's configured output plugins. For each
    plugin that is proto-based, it instantiates the plugin and calls its
    `ProcessResults` method with the provided replies. Any logs generated by
    the plugin are written to the datastore. Exceptions during plugin
    processing are caught and logged as errors.

    Args:
      replies: A sequence of `flows_pb2.FlowResult` to be processed.
    """
    proto_plugin_descriptors = []
    for idx, p in enumerate(self.rdf_flow.output_plugins):
      try:
        output_plugin_registry.GetPluginClassByName(p.plugin_name)
        proto_plugin_descriptors.append(
            (idx, mig_output_plugin.ToProtoOutputPluginDescriptor(p))
        )
      except KeyError:
        # This is an RDF-based plugin, we'll process it separately.
        pass

    logging.info(
        "Processing %d replies with %d proto-based output plugins.",
        len(replies),
        len(proto_plugin_descriptors),
    )

    for plugin_id, plugin_descriptor in proto_plugin_descriptors:
      plugin_cls = output_plugin_registry.GetPluginClassByName(
          plugin_descriptor.plugin_name
      )
      if plugin_cls.args_type is not None:  # pytype: disable=unbound-type-param
        # `plugin_descriptor.args` is an instance of `any_pb2.Any`.
        pl_args = plugin_cls.args_type.FromString(plugin_descriptor.args.value)
      else:
        pl_args = None

      plugin = plugin_cls(source_urn=self.rdf_flow.long_flow_id, args=pl_args)

      try:
        plugin.ProcessResults(replies)
        plugin.Flush()
        self.Log(
            "Plugin <<%s>> (id: %s) successfully processed %d flow replies.",
            plugin_descriptor,
            plugin_id,
            len(replies),
        )
        # TODO: Remove once migration is complete.
        # For now this serves as compatibility with logging for RDF-based
        # plugins (the other branch adds an equivalent log entry).
        data_store.REL_DB.WriteFlowOutputPluginLogEntry(
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id=str(plugin_id),
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message=f"Processed {len(replies)} replies.",
            )
        )
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "Plugin %s failed to process %d replies.",
            plugin_descriptor,
            len(replies),
        )
        data_store.REL_DB.WriteFlowOutputPluginLogEntry(
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id=str(plugin_id),
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
                message=(
                    "Error while processing "
                    f"{len(self.proto_replies_to_process)} replies: {str(e)}"
                ),
            )
        )
        self.Log(
            "Plugin %s failed to process %d replies due to: %s",
            plugin_descriptor.plugin_name,
            len(self.proto_replies_to_process),
            e,
        )

      logs_to_write: list[flows_pb2.FlowOutputPluginLogEntry] = []
      for log_type, log_message in plugin.GetLogs():
        logs_to_write.append(
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id=str(plugin_id),
                log_entry_type=log_type,
                message=log_message,
            )
        )
      logging.info(
          "Writing %d logs for plugin %s", len(logs_to_write), plugin_id
      )
      if logs_to_write:
        data_store.REL_DB.WriteMultipleFlowOutputPluginLogEntries(logs_to_write)

  def _ProcessRepliesWithHuntOutputPlugins(
      self, replies: Sequence[rdf_flow_objects.FlowResult]
  ) -> None:
    """Applies output plugins to hunt results."""
    hunt_obj = data_store.REL_DB.ReadHuntObject(self.rdf_flow.parent_hunt_id)
    hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
    self.rdf_flow.output_plugins = hunt_obj.output_plugins
    hunt_output_plugins_states = data_store.REL_DB.ReadHuntOutputPluginsStates(
        self.rdf_flow.parent_hunt_id
    )

    hunt_output_plugins_states = [
        mig_flow_runner.ToRDFOutputPluginState(s)
        for s in hunt_output_plugins_states
    ]
    self.rdf_flow.output_plugins_states = hunt_output_plugins_states

    created_plugins = self._ProcessRepliesWithFlowOutputPlugins(replies)

    for index, (plugin, state) in enumerate(
        zip(created_plugins, hunt_output_plugins_states)
    ):
      if plugin is None:
        continue

      # Only do the REL_DB call if the plugin state has actually changed.
      s = state.plugin_state.Copy()
      plugin.UpdateState(s)
      if s != state.plugin_state:

        def UpdateFn(
            plugin_state: jobs_pb2.AttributedDict,
        ) -> jobs_pb2.AttributedDict:
          plugin_state_rdf = mig_protodict.ToRDFAttributedDict(plugin_state)
          plugin.UpdateState(plugin_state_rdf)  # pylint: disable=cell-var-from-loop
          plugin_state = mig_protodict.ToProtoAttributedDict(plugin_state_rdf)
          return plugin_state

        data_store.REL_DB.UpdateHuntOutputPluginState(
            hunt_obj.hunt_id, index, UpdateFn
        )

    for plugin_def, created_plugin in zip(
        hunt_obj.output_plugins, created_plugins
    ):
      if created_plugin is not None:
        HUNT_RESULTS_RAN_THROUGH_PLUGIN.Increment(
            len(replies), fields=[plugin_def.plugin_name]
        )
      else:
        HUNT_OUTPUT_PLUGIN_ERRORS.Increment(fields=[plugin_def.plugin_name])

  def _ProcessRepliesWithFlowOutputPlugins(
      self, replies: Sequence[rdf_flow_objects.FlowResult]
  ) -> Sequence[Optional[output_plugin_lib.OutputPlugin]]:
    """Processes replies with output plugins."""
    created_output_plugins = []
    for output_plugin_state in self.rdf_flow.output_plugins_states:  # pytype: disable=attribute-error
      plugin_descriptor = output_plugin_state.plugin_descriptor  # pytype: disable=attribute-error
      output_plugin_cls = plugin_descriptor.GetPluginClass()
      args = plugin_descriptor.args
      output_plugin = output_plugin_cls(
          source_urn=self.rdf_flow.long_flow_id, args=args
      )

      try:
        output_plugin.ProcessResponses(
            output_plugin_state.plugin_state,
            replies,
        )
        output_plugin.Flush(output_plugin_state.plugin_state)
        output_plugin.UpdateState(output_plugin_state.plugin_state)

        data_store.REL_DB.WriteFlowOutputPluginLogEntry(
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id=output_plugin_state.plugin_id,
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message="Processed %d replies." % len(replies),
            )
        )

        self.Log(
            "Plugin %s (id: %s) successfully processed %d flow replies.",
            plugin_descriptor.plugin_name,
            output_plugin_state.plugin_id,
            len(replies),
        )

        created_output_plugins.append(output_plugin)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "Plugin %s failed to process %d replies.",
            plugin_descriptor,
            len(replies),
        )
        created_output_plugins.append(None)

        data_store.REL_DB.WriteFlowOutputPluginLogEntry(
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id=output_plugin_state.plugin_id,
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
                message="Error while processing %d replies: %s"
                % (len(replies), str(e)),
            )
        )

        self.Log(
            "Plugin %s failed to process %d replies due to: %s",
            plugin_descriptor,
            len(replies),
            e,
        )

    return created_output_plugins

  def MergeQueuedMessages(self, flow_obj: "FlowBase") -> None:
    """Merges queued messages."""
    self.flow_requests.extend(flow_obj.flow_requests)
    flow_obj.flow_requests = []
    self.proto_flow_requests.extend(flow_obj.proto_flow_requests)
    flow_obj.proto_flow_requests = []
    self.flow_responses.extend(flow_obj.flow_responses)
    flow_obj.flow_responses = []
    self.proto_flow_responses.extend(flow_obj.proto_flow_responses)
    flow_obj.proto_flow_responses = []
    self.rrg_requests.extend(flow_obj.rrg_requests)
    flow_obj.rrg_requests = []
    self.client_action_requests.extend(flow_obj.client_action_requests)
    flow_obj.client_action_requests = []
    self.proto_client_action_requests.extend(
        flow_obj.proto_client_action_requests
    )
    flow_obj.proto_client_action_requests = []
    self.completed_requests.extend(flow_obj.completed_requests)
    flow_obj.completed_requests = []
    self.replies_to_write.extend(flow_obj.replies_to_write)
    flow_obj.replies_to_write = []
    self.proto_replies_to_write.extend(flow_obj.proto_replies_to_write)
    flow_obj.proto_replies_to_write = []

  def ShouldSendNotifications(self) -> bool:
    return bool(
        not self.rdf_flow.parent_flow_id
        and not self.rdf_flow.parent_hunt_id
        and self.creator
        and self.creator not in access_control.SYSTEM_USERS
    )

  def IsRunning(self) -> bool:
    return self.rdf_flow.flow_state == self.rdf_flow.FlowState.RUNNING

  def GetProgress(self) -> rdf_structs.RDFProtoStruct:
    return rdf_flow_objects.DefaultFlowProgress()

  def GetProgressProto(self) -> pb_message.Message:
    return flows_pb2.DefaultFlowProgress()

  def GetFilesArchiveMappings(
      self, flow_results: Iterator[rdf_flow_objects.FlowResult]
  ) -> Iterator[ClientPathArchiveMapping]:
    """Returns a mapping used to generate flow results archive.

    If this is implemented by a flow, then instead of generating
    a general-purpose archive with all files referenced in the
    results present, an archive would be generated with
    just the files referenced in the mappings.

    Args:
      flow_results: An iterator for flow results.

    Returns:
      An iterator of mappings from REL_DB's ClientPaths to archive paths.
    Raises:
      NotImplementedError: if not implemented by a subclass.
    """
    raise NotImplementedError("GetFilesArchiveMappings() not implemented")

  @property
  def client_id(self) -> str:
    return self.rdf_flow.client_id

  @property
  def client_urn(self) -> rdfvalue.RDFURN:
    return rdfvalue.RDFURN(self.client_id)

  @property
  def state(self) -> Any:
    if self._state is None:
      self._state = flow.AttributedDict(self.rdf_flow.persistent_data.ToDict())
    return self._state

  @property
  def progress(self) -> _ProtoProgressT:
    if self._progress is None:
      if self.rdf_flow.HasField("progress"):
        packed_any: any_pb2.Any = self.rdf_flow.progress.AsPrimitiveProto()
        unpacked = self.proto_progress_type()
        packed_any.Unpack(unpacked)
        self._progress = unpacked
      else:
        self._progress = self.proto_progress_type()
    return self._progress

  @progress.setter
  def progress(self, value: _ProtoProgressT) -> None:
    self._progress = value

  @property
  def store(self) -> _ProtoStoreT:
    if self._store is None:
      self._store = self.proto_store_type()
      if self.rdf_flow.HasField("store"):
        packed_any: any_pb2.Any = self.rdf_flow.store.AsPrimitiveProto()
        packed_any.Unpack(self._store)

    return self._store

  @store.setter
  def store(self, value: _ProtoStoreT) -> None:
    self._store = value

  def _AccountForProtoResultMetadata(self):
    """Merges `_num_replies_per_type_tag` Counter with current ResultMetadata."""
    self._result_metadata.is_metadata_set = True

    for r in self._result_metadata.num_results_per_type_tag:
      key = (r.type, r.tag)
      # This removes the item from _num_replies_per_type_tag if it's present in
      # result_metadata.
      count = self._num_replies_per_type_tag.pop(key, 0)
      r.count = r.count + count

    # Iterate over remaining items - i.e. items that were not present in
    # result_metadata.
    for (
        result_type,
        result_tag,
    ), count in self._num_replies_per_type_tag.items():
      self._result_metadata.num_results_per_type_tag.append(
          flows_pb2.FlowResultCount(
              type=result_type, tag=result_tag, count=count
          )
      )
    self._num_replies_per_type_tag = collections.Counter()

    self.rdf_flow.result_metadata = (
        rdf_flow_objects.FlowResultMetadata().FromSerializedBytes(
            self._result_metadata.SerializeToString()
        )
    )

  def PersistState(self) -> None:
    """Persists flow state."""
    self._AccountForProtoResultMetadata()
    self.rdf_flow.persistent_data = self.state
    if self._store is not None:
      self.rdf_flow.store = rdf_structs.AnyValue.PackProto2(self._store)
    if self._progress is not None:
      self.rdf_flow.progress = rdf_structs.AnyValue.PackProto2(self._progress)

  @property
  def args(self) -> Any:
    return self.rdf_flow.args

  @args.setter
  def args(self, args: rdfvalue.RDFValue) -> None:
    """Updates both rdf and proto args."""
    if not isinstance(args, self.args_type):
      raise TypeError(
          f"args must be of type {self.args_type}, got {type(args)} instead."
      )
    self.rdf_flow.args = args
    self._proto_args = self.proto_args_type()
    self._proto_args.ParseFromString(args.SerializeToBytes())

  @property
  def proto_args(self) -> _ProtoArgsT:
    """Returns the proto args."""
    if self._proto_args is not None:
      return self._proto_args

    # We use `rdf_flow.args` as source of truth for now.
    if self.rdf_flow.HasField("args"):
      # Hope serialization is compatible
      args = self.proto_args_type()
      args.ParseFromString(self.args.SerializeToBytes())
      self._proto_args = args
    else:
      self._proto_args = self.proto_args_type()
    return self._proto_args

  @proto_args.setter
  def proto_args(self, proto_args: Optional[_ProtoArgsT]) -> None:
    """Updates both rdf and proto args."""
    if not isinstance(proto_args, self.proto_args_type):
      raise TypeError(
          f"proto_args must be of type {self.proto_args_type}, got"
          f" {type(proto_args)} instead."
      )
    self._proto_args = proto_args
    self.rdf_flow.args = self.args_type.FromSerializedBytes(
        proto_args.SerializeToString()
    )

  @property
  def client_version(self) -> int:
    if self._client_version is None:
      self._client_version = data_store_utils.GetClientVersion(self.client_id)

    return self._client_version

  @property
  def client_os(self) -> str:
    if self._client_os is None:
      self._client_os = data_store_utils.GetClientOs(self.client_id)

    return self._client_os

  @property
  def client_knowledge_base(self) -> Optional[knowledge_base_pb2.KnowledgeBase]:
    if self._client_knowledge_base is None:
      self._client_knowledge_base = data_store_utils.GetClientKnowledgeBase(
          self.client_id
      )

    return self._client_knowledge_base

  @property
  def client_info(self) -> rdf_client.ClientInformation:
    if self._client_info is not None:
      return self._client_info

    client_info = data_store_utils.GetClientInformation(self.client_id)
    self._client_info = client_info

    return client_info

  @property
  def client_labels(self) -> Collection[str]:
    if self._client_labels is None:
      self._client_labels = set()
      for label in data_store.REL_DB.ReadClientLabels(self.client_id):
        self._client_labels.add(label.name)

    return self._client_labels

  @property
  def python_agent_support(self) -> bool:
    """Returns whether the endpoint supports the Python agent."""
    if self._python_agent_support is None:
      startup = data_store.REL_DB.ReadClientStartupInfo(self.client_id)
      # Unlike with RRG startup records, in case of the Python agent it is not
      # enough to verify that a record exists because we write them also when
      # writing snapshots (even if they are empty as the agent never started!).
      # Thus, we also verify that the version is set to some non-zero value.
      self._python_agent_support = (
          startup is not None and startup.client_info.client_version > 0
      )

    return self._python_agent_support

  @property
  def rrg_startup(self) -> rrg_startup_pb2.Startup:
    """Returns latest startup record of RRG running on the endpoint."""
    if self._rrg_startup is None:
      rrg_startup = data_store.REL_DB.ReadClientRRGStartup(self.client_id)

      if rrg_startup is not None:
        self._rrg_startup = rrg_startup
      else:
        # We don't want a new database roundtrip each time if it keeps returning
        # `None`, so we set it to empty value to make "initialized".
        self._rrg_startup = rrg_startup_pb2.Startup()

    return self._rrg_startup

  @property
  def rrg_version(self) -> RRGVersion:
    """Returns version of the RRG agent running on the endpoint."""
    if (
        config.CONFIG["Server.disable_rrg_support"]
        or self.rdf_flow.disable_rrg_support
    ):
      return RRGVersion(major=0, minor=0, patch=0)

    return RRGVersion(
        major=self.rrg_startup.metadata.version.major,
        minor=self.rrg_startup.metadata.version.minor,
        patch=self.rrg_startup.metadata.version.patch,
    )

  @property
  def rrg_support(self) -> bool:
    return self.rrg_version > (0, 0, 0)

  @property
  def rrg_os_type(self) -> rrg_os_pb2.Type:
    """Returns operating system type of the endpoint running the RRG agent."""
    if self.rrg_version >= (0, 0, 4):
      return self.rrg_startup.os_type

    # TODO: https://github.com/google/rrg/issues/133 - Remove once we no longer
    # support version <0.0.4.
    if self.client_os == "Linux":
      return rrg_os_pb2.LINUX
    if self.client_os == "Darwin":
      return rrg_os_pb2.MACOS
    if self.client_os == "Windows":
      return rrg_os_pb2.WINDOWS

    raise RuntimeError(f"Unexpected operating system: {self.client_os}")

  @property
  def default_exclude_labels(self) -> Collection[str]:
    hunt_config = config.CONFIG["AdminUI.hunt_config"]
    if not hunt_config:
      return []

    hunt_config = hunt_config.AsPrimitiveProto()
    return hunt_config.default_exclude_labels

  @property
  def client_has_exclude_labels(self) -> bool:
    return bool(set(self.default_exclude_labels) & set(self.client_labels))

  @property
  def creator(self) -> str:
    return self.rdf_flow.creator

  @classmethod
  def GetDefaultArgs(cls, username: Optional[str] = None) -> Any:
    del username  # Unused.
    return cls.args_type()

  @classmethod
  def CreateFlowInstance(cls, flow_object: rdf_flow_objects.Flow) -> "FlowBase":
    flow_cls = FlowRegistry.FlowClassByName(flow_object.flow_class_name)
    return flow_cls(flow_object)

  @classmethod
  def CanUseViaAPI(cls) -> bool:
    return bool(cls.category)

  def _CheckMethodExpectsProtos(
      self, method: types.MethodType, rdf_alternative: str
  ) -> None:
    """Checks if a given method expects proto responses.

    Args:
      method: A method to check.
      rdf_alternative: Name of the RDF-based alternative to suggest.

    Raises:
      ValueError: if the method is not annotated with `@UseProto2AnyResponses`.
    """
    if not self._IsAnnotatedWithProto2AnyResponses(
        method
    ) and not self._IsAnnotatedWithProto2AnyResponsesCallback(method):
      raise ValueError(
          f"Method {method.__name__} is not annotated with"
          " `@UseProto2AnyResponses` or `@UseProto2AnyResponsesCallback`."
          f" Please use `{rdf_alternative}` instead."
      )

  def _IsAnnotatedWithProto2AnyResponses(
      self, method: types.MethodType
  ) -> bool:
    return (
        hasattr(method, "_proto2_any_responses")
        and method._proto2_any_responses  # pylint: disable=protected-access
    )

  def _IsAnnotatedWithProto2AnyResponsesCallback(
      self, method: types.MethodType
  ) -> bool:
    return (
        hasattr(method, "_proto2_any_responses_callback")
        and method._proto2_any_responses_callback  # pylint: disable=protected-access
    )


def FindIncrementalRequestsToProcess(
    request_dict: Dict[
        int,
        Tuple[
            flows_pb2.FlowRequest,
            Sequence[
                Union[
                    flows_pb2.FlowResponse,
                    flows_pb2.FlowStatus,
                    flows_pb2.FlowIterator,
                ],
            ],
        ],
    ],
    next_needed_request_id: int,
) -> List[
    Tuple[
        flows_pb2.FlowRequest,
        Sequence[
            Union[
                flows_pb2.FlowResponse,
                flows_pb2.FlowStatus,
                flows_pb2.FlowIterator,
            ],
        ],
    ]
]:
  """Returns incremental flow requests that are ready to be processed.

  These are requests that have the callback state specified (via the
  "callback_state" attribute) and are not yet completed.

  Args:
    request_dict: A dict mapping flow request id to tuples (request, sorted list
      of responses for the request).
    next_needed_request_id: The id of the next request that needs to be
      processed, previous ids are omitted.

  Returns:
    A list of tuples (request, new responses only for the request (sorted))
      sorted by request id.
  """

  incremental_requests: list[
      tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ] = []
  for request_id in request_dict:
    if request_id < next_needed_request_id:
      continue

    request, responses = request_dict[request_id]
    if not request.callback_state:
      continue

    new_responses = []
    if request.HasField("next_response_id"):
      next_response_id = request.next_response_id
    else:
      next_response_id = 1

    for r in responses:
      if r.response_id < next_response_id:
        continue
      elif r.response_id == next_response_id:
        new_responses.append(r)
        next_response_id += 1
      else:
        # Next response is still missing.
        break

    if new_responses:
      incremental_requests.append((request, new_responses))

  return sorted(incremental_requests, key=lambda x: x[0].request_id)


def FindCompletedRequestsToProcess(
    request_dict: Dict[
        int,
        Tuple[
            flows_pb2.FlowRequest,
            Sequence[
                Union[
                    flows_pb2.FlowResponse,
                    flows_pb2.FlowStatus,
                    flows_pb2.FlowIterator,
                ],
            ],
        ],
    ],
    next_needed_request_id: int,
) -> List[
    Tuple[
        flows_pb2.FlowRequest,
        Sequence[
            Union[
                flows_pb2.FlowResponse,
                flows_pb2.FlowStatus,
                flows_pb2.FlowIterator,
            ],
        ],
    ],
]:
  """Returns completed flow requests that are ready to be processed.

  These are requests that received all the responses, including the status
  message, and their "needs_processing" attribute is set to True.

  Args:
    request_dict: A dict mapping flow request id to tuples (request, sorted list
      of responses for the request).
    next_needed_request_id: The id of the next request that needs to be
      processed, previous ids are omitted.

  Returns:
    A list of tuples (request, all responses for the request (sorted)) sorted by
      request id.
  """
  completed_requests: List[
      Tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ] = []
  while next_needed_request_id in request_dict:
    req, responses = request_dict[next_needed_request_id]

    if not req.needs_processing:
      break

    completed_requests.append((req, responses))
    next_needed_request_id += 1

  return sorted(completed_requests, key=lambda x: x[0].request_id)


def UseProto2AnyResponses(
    state_method: Callable[
        [FlowBase, flow_responses.Responses[any_pb2.Any]], None
    ],
) -> Callable[[FlowBase, flow_responses.Responses[any_pb2.Any]], None]:
  """Instructs flow execution not to use RDF magic for unpacking responses.

  The current default behaviour of the flow execution is to do type lookup and
  automagically unpack flow responses to "appropriate" type. This behaviour is
  problematic for many reasons and methods that do not need to rely on it should
  use this annotation.

  Args:
    state_method: A flow state method to annotate.

  Returns:
    A flow state method that will not have the problematic behaviour.
  """

  @functools.wraps(state_method)
  def Wrapper(self, responses: flow_responses.Responses) -> None:
    return state_method(self, responses)

  Wrapper._proto2_any_responses = True  # pylint: disable=protected-access

  return Wrapper


def UseProto2AnyResponsesCallback(
    callback_state_method: Callable[
        [FlowBase, flow_responses.Responses[any_pb2.Any]], None
    ],
) -> Callable[[FlowBase, flow_responses.Responses[any_pb2.Any]], None]:
  """Instructs flow execution not to use RDF magic for unpacking responses.

  Unlike `UseProto2AnyResponses`, this method allows for partial responses
  to be further processed, thus being suitable for callback states.

  Args:
    callback_state_method: A flow state method to annotate.

  Returns:
    A flow callback state method that will work with partial responses.
  """

  @functools.wraps(callback_state_method)
  def Wrapper(self, responses: flow_responses.Responses) -> None:
    return callback_state_method(self, responses)

  Wrapper._proto2_any_responses_callback = True  # pylint: disable=protected-access

  return Wrapper


def _TerminateFlow(
    proto_flow: flows_pb2.Flow,
    reason: Optional[str] = None,
    flow_state: rdf_structs.EnumNamedValue = rdf_flow_objects.Flow.FlowState.ERROR,
) -> None:
  """Does the actual termination."""
  flow_cls = FlowRegistry.FlowClassByName(proto_flow.flow_class_name)
  rdf_flow = mig_flow_objects.ToRDFFlow(proto_flow)
  flow_obj = flow_cls(rdf_flow)

  if not flow_obj.IsRunning():
    # Nothing to do.
    return

  logging.info(
      "Terminating flow %s on %s, reason: %s",
      rdf_flow.flow_id,
      rdf_flow.client_id,
      reason,
  )

  rdf_flow.flow_state = flow_state
  rdf_flow.error_message = reason
  flow_obj.NotifyCreatorOfError()
  proto_flow = mig_flow_objects.ToProtoFlow(rdf_flow)
  data_store.REL_DB.UpdateFlow(
      proto_flow.client_id,
      proto_flow.flow_id,
      flow_obj=proto_flow,
      processing_on=None,
      processing_since=None,
      processing_deadline=None,
  )
  data_store.REL_DB.DeleteAllFlowRequestsAndResponses(
      proto_flow.client_id, proto_flow.flow_id
  )


def TerminateFlow(
    client_id: str,
    flow_id: str,
    reason: Optional[str] = None,
    flow_state: rdf_structs.EnumNamedValue = rdf_flow_objects.Flow.FlowState.ERROR,
) -> None:
  """Terminates a flow and all of its children.

  Args:
    client_id: Client ID of a flow to terminate.
    flow_id: Flow ID of a flow to terminate.
    reason: String with a termination reason.
    flow_state: Flow state to be assigned to a flow after termination. Defaults
      to FlowState.ERROR.
  """

  to_terminate = [data_store.REL_DB.ReadFlowObject(client_id, flow_id)]

  while to_terminate:
    next_to_terminate = []
    for proto_flow in to_terminate:
      _TerminateFlow(proto_flow, reason=reason, flow_state=flow_state)
      next_to_terminate.extend(
          data_store.REL_DB.ReadChildFlowObjects(
              proto_flow.client_id, proto_flow.flow_id
          )
      )
    to_terminate = next_to_terminate
