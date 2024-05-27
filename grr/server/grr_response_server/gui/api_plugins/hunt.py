#!/usr/bin/env python
"""API handlers for accessing hunts."""

import collections
import math
import os
import re
from typing import Iterable
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import Union

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import analysis_pb2
from grr_response_proto import api_utils_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import output_plugin_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import instant_output_plugin
from grr_response_server import notification
from grr_response_server import output_plugin
from grr_response_server.databases import db
from grr_response_server.flows.general import export
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.models import hunts as models_hunts
from grr_response_server.models import protobuf_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects

HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")

# pyformat: disable

CANCELLED_BY_USER = "Cancelled by user"

# /grr/server/grr_response_server/hunt.py,
# //depot/@app/components/hunt/hunt_status_chip/hunt_status_chip.ts)
# pyformat: enable


class HuntNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt could not be found."""


class HuntFileNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt file could not be found."""


class Error(Exception):
  pass


class InvalidHuntStateError(Error):
  pass


class HuntNotStartableError(Error):
  pass


class HuntNotStoppableError(Error):
  pass


class HuntNotModifiableError(Error):
  pass


class HuntNotDeletableError(Error):
  pass


def ApiFlowLikeObjectReferenceFromReference(
    reference: flows_pb2.FlowLikeObjectReference,
) -> hunt_pb2.ApiFlowLikeObjectReference:
  """Converts a FlowLikeObjectReference to an ApiFlowLikeObjectReference."""
  ref = hunt_pb2.ApiFlowLikeObjectReference(
      object_type=hunt_pb2.ApiFlowLikeObjectReference.ObjectType.Name(
          reference.object_type
      )
  )
  reference_type = flows_pb2.FlowLikeObjectReference.ObjectType
  if reference.object_type == reference_type.HUNT_REFERENCE:
    ref.hunt_reference.CopyFrom(
        hunt_pb2.ApiHuntReference(hunt_id=reference.hunt_reference.hunt_id)
    )
  elif reference.object_type == reference_type.FLOW_REFERENCE:
    ref.flow_reference.CopyFrom(
        flow_pb2.ApiFlowReference(
            flow_id=reference.flow_reference.flow_id,
            client_id=reference.flow_reference.client_id,
        )
    )
  return ref


def InitApiHuntFromHuntObject(
    hunt_obj: hunts_pb2.Hunt,
    hunt_counters: Optional[db.HuntCounters] = None,
    with_full_summary: bool = False,
) -> hunt_pb2.ApiHunt:
  """Initialize API hunt object from a database hunt object.

  Args:
    hunt_obj: Hunt to read the data from.
    hunt_counters: Optional db.HuntCounters object with counters information.
    with_full_summary: if True, hunt_runner_args, completion counts and a few
      other fields will be filled in. The way to think about it is that with
      with_full_summary==True ApiHunt will have the data to render "Hunt
      Overview" page and with with_full_summary==False it will have enough data
      to be rendered as a hunts list row.

  Returns:
    A ApiHunt object.
  """
  api_hunt = hunt_pb2.ApiHunt()
  api_hunt.urn = str(rdfvalue.RDFURN("hunts").Add(str(hunt_obj.hunt_id)))
  if hunt_obj.args.hunt_type == hunts_pb2.HuntArguments.HuntType.STANDARD:
    api_hunt.name = "GenericHunt"
    api_hunt.hunt_type = hunts_pb2.HuntArguments.HuntType.STANDARD
  else:
    api_hunt.name = "VariableGenericHunt"
    api_hunt.hunt_type = hunts_pb2.HuntArguments.HuntType.VARIABLE
  api_hunt.state = _HuntStateToApiHuntState(hunt_obj.hunt_state)
  api_hunt.state_reason = _HuntStateReasonToApiHuntStateReason(
      hunt_obj.hunt_state_reason
  )
  # Set `state_comment` to empty string if unset to maintain API.
  api_hunt.state_comment = hunt_obj.hunt_state_comment
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "hunt_id")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "crash_limit")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "client_limit")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "client_rate")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "create_time", "created")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "duration")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "creator")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "init_start_time")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "last_start_time")
  protobuf_utils.CopyAttr(hunt_obj, api_hunt, "description")
  api_hunt.is_robot = hunt_obj.creator in access_control.SYSTEM_USERS

  if hunt_counters is not None:
    api_hunt.results_count = hunt_counters.num_results
    api_hunt.clients_with_results_count = hunt_counters.num_clients_with_results
    api_hunt.remaining_clients_count = hunt_counters.num_running_clients
    # TODO(user): remove this hack when AFF4 is gone. For regression tests
    # compatibility only.
    api_hunt.total_cpu_usage = hunt_counters.total_cpu_seconds or 0.0
    api_hunt.total_net_usage = hunt_counters.total_network_bytes_sent

    if with_full_summary:
      api_hunt.all_clients_count = hunt_counters.num_clients
      api_hunt.failed_clients_count = hunt_counters.num_failed_clients
      api_hunt.crashed_clients_count = hunt_counters.num_crashed_clients
      api_hunt.completed_clients_count = (
          hunt_counters.num_successful_clients
          + hunt_counters.num_failed_clients
      )
  else:
    api_hunt.results_count = 0
    api_hunt.clients_with_results_count = 0
    api_hunt.remaining_clients_count = 0
    api_hunt.total_cpu_usage = 0.0
    api_hunt.total_net_usage = 0

    if with_full_summary:
      api_hunt.all_clients_count = 0
      api_hunt.failed_clients_count = 0
      api_hunt.crashed_clients_count = 0
      api_hunt.completed_clients_count = 0

  if (
      hunt_obj.original_object.object_type
      != flows_pb2.FlowLikeObjectReference.ObjectType.UNKNOWN
  ):
    api_hunt.original_object.CopyFrom(
        ApiFlowLikeObjectReferenceFromReference(hunt_obj.original_object)
    )

  if with_full_summary:
    hra = flows_pb2.HuntRunnerArgs()
    protobuf_utils.CopyAttr(api_hunt, hra, "name", "hunt_name")
    protobuf_utils.CopyAttr(hunt_obj, hra, "description")
    protobuf_utils.CopyAttr(hunt_obj, hra, "crash_limit")
    protobuf_utils.CopyAttr(hunt_obj, hra, "client_limit")
    protobuf_utils.CopyAttr(hunt_obj, hra, "duration", "expiry_time")
    protobuf_utils.CopyAttr(hunt_obj, hra, "avg_results_per_client_limit")
    protobuf_utils.CopyAttr(hunt_obj, hra, "avg_cpu_seconds_per_client_limit")
    protobuf_utils.CopyAttr(hunt_obj, hra, "avg_network_bytes_per_client_limit")
    protobuf_utils.CopyAttr(hunt_obj, hra, "client_rate")
    protobuf_utils.CopyAttr(hunt_obj, hra, "per_client_cpu_limit")
    protobuf_utils.CopyAttr(
        hunt_obj,
        hra,
        "per_client_network_bytes_limit",
        "per_client_network_limit_bytes",
    )
    protobuf_utils.CopyAttr(
        hunt_obj, hra, "total_network_bytes_limit", "network_bytes_limit"
    )
    hra.output_plugins.extend(hunt_obj.output_plugins)
    hra.client_rule_set.CopyFrom(hunt_obj.client_rule_set)
    hra.original_object.CopyFrom(hunt_obj.original_object)

    api_hunt.hunt_runner_args.CopyFrom(hra)
    api_hunt.client_rule_set.CopyFrom(hunt_obj.client_rule_set)

    if hunt_obj.args.hunt_type == hunts_pb2.HuntArguments.HuntType.STANDARD:
      api_hunt.flow_name = hunt_obj.args.standard.flow_name
      api_hunt.flow_args.CopyFrom(hunt_obj.args.standard.flow_args)
    elif hunt_obj.args.hunt_type == hunts_pb2.HuntArguments.HuntType.VARIABLE:
      api_hunt.flow_args.Pack(hunt_obj.args.variable)

  return api_hunt


def InitApiHuntFromHuntMetadata(
    hunt_metadata: hunts_pb2.HuntMetadata,
) -> hunt_pb2.ApiHunt:
  """Initialize API hunt object from a hunt metadata object.

  Args:
    hunt_metadata: HuntMetadata to read the data from.

  Returns:
    A ApiHunt object.
  """
  api_hunt = hunt_pb2.ApiHunt(
      urn=str(rdfvalue.RDFURN("hunts").Add(str(hunt_metadata.hunt_id))),
      state=_HuntStateToApiHuntState(hunt_metadata.hunt_state),
      is_robot=hunt_metadata.creator in access_control.SYSTEM_USERS,
  )

  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "hunt_id")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "client_limit")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "client_rate")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "create_time", "created")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "init_start_time")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "last_start_time")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "duration")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "creator")
  protobuf_utils.CopyAttr(hunt_metadata, api_hunt, "description")
  return api_hunt


def ApiCreatePerClientFileCollectionHuntArgToHuntArgs(
    args: hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs,
) -> hunts_pb2.HuntArguments:
  """Converts ApiCreatePerClientFileCollectionHuntArgs to HuntArguments."""
  hunt_arguments = hunts_pb2.HuntArguments()
  hunt_arguments.hunt_type = hunts_pb2.HuntArguments.HuntType.VARIABLE

  for client_arg in args.per_client_args:
    if client_arg.HasField("path_type"):
      pathtype = client_arg.path_type
    else:
      pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_args = flows_pb2.MultiGetFileArgs()
    for path in client_arg.paths:
      flow_args.pathspecs.add(path=path, pathtype=pathtype)

    flow_group = hunt_arguments.variable.flow_groups.add()
    flow_group.flow_args.Pack(flow_args)
    flow_group.client_ids.append(str(client_arg.client_id))
    flow_group.flow_name = transfer.MultiGetFile.__name__

  return hunt_arguments


def InitApiHuntLogFromFlowLogEntry(
    fle: flows_pb2.FlowLogEntry,
) -> hunt_pb2.ApiHuntLog:
  """Init ApiHuntLog from FlowLogEntry."""

  hunt_log = hunt_pb2.ApiHuntLog()

  # TODO(user): putting this stub value for backwards compatibility.
  # Remove as soon as AFF4 is gone.
  hunt_log.flow_name = "GenericHunt"

  protobuf_utils.CopyAttr(fle, hunt_log, "client_id")
  protobuf_utils.CopyAttr(fle, hunt_log, "flow_id")
  protobuf_utils.CopyAttr(fle, hunt_log, "timestamp")
  protobuf_utils.CopyAttr(fle, hunt_log, "message", "log_message")

  return hunt_log


def InitApiHuntErrorFromFlowErrorInfo(
    client_id: str,
    info: db.FlowErrorInfo,
) -> hunt_pb2.ApiHuntError:
  """Init ApiHuntError from FlowErrorInfo."""

  hunt_error = hunt_pb2.ApiHuntError()
  hunt_error.client_id = client_id
  hunt_error.log_message = info.message
  hunt_error.timestamp = info.time.AsMicrosecondsSinceEpoch()

  if info.backtrace is not None:
    hunt_error.backtrace = info.backtrace

  return hunt_error


class Bucket:
  """A bucket for counts of timestamps."""

  lower_boundary_ts: float
  count: int

  def __init__(self, lower_boundary_ts: float, count: int = 0):
    self.lower_boundary_ts = lower_boundary_ts
    self.count = count


class Histogram:
  """A histogram of timestamps."""

  min_timestamp: int
  num_buckets: int
  bucket_size: float
  buckets: list[Bucket]

  def __init__(
      self,
      min_timestamp: int,
      max_timestamp: int,
      num_buckets: int,
  ):
    self.min_timestamp = min_timestamp
    self.num_buckets = num_buckets
    self.bucket_size = (max_timestamp - min_timestamp) / num_buckets

    self.buckets = []
    for i in range(num_buckets):
      lower = min_timestamp + i * self.bucket_size
      self.buckets.append(Bucket(lower_boundary_ts=lower))

  def _GetBucketIndex(self, timestamp: int) -> int:
    if self.bucket_size == 0:
      return 0
    index = math.floor((timestamp - self.min_timestamp) / self.bucket_size)
    if index < 0:
      raise ValueError(
          f"Timestamp `{timestamp}` must be larger than `{self.min_timestamp}`"
      )
    if index >= self.num_buckets:
      index = self.num_buckets - 1

    return index

  def Insert(self, timestamp: int) -> None:
    self.buckets[self._GetBucketIndex(timestamp)].count += 1


def InitApiGetHuntClientCompletionStatsResultFromHistograms(
    flow_creation_time_histogram: Histogram,
    flow_completion_time_histogram: Histogram,
) -> hunt_pb2.ApiGetHuntClientCompletionStatsResult:
  """Initializes ApiGetHuntClientCompletionStatsResult from given histograms."""
  creation_time_samples = []
  completion_time_samples = []

  accumulative_start_count = 0
  for index, bucket in enumerate(flow_creation_time_histogram.buckets):
    if bucket.count == 0 and index > 0:
      continue
    accumulative_start_count += bucket.count
    creation_time_samples.append(
        analysis_pb2.SampleFloat(
            x_value=bucket.lower_boundary_ts,
            y_value=accumulative_start_count,
        )
    )

  accumulative_complete_count = 0
  for index, bucket in enumerate(flow_completion_time_histogram.buckets):
    if bucket.count == 0 and index > 0:
      continue
    accumulative_complete_count += bucket.count
    completion_time_samples.append(
        analysis_pb2.SampleFloat(
            x_value=bucket.lower_boundary_ts,
            y_value=accumulative_complete_count,
        )
    )

  return hunt_pb2.ApiGetHuntClientCompletionStatsResult(
      start_points=creation_time_samples,
      complete_points=completion_time_samples,
  )


class ApiHuntId(rdfvalue.RDFString):
  """Class encapsulating hunt ids."""

  def __init__(self, initializer=None):
    super().__init__(initializer=initializer)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      try:
        rdfvalue.SessionID.ValidateID(self._value)
      except ValueError as e:
        raise ValueError("Invalid hunt id: %s (%s)" % (self._value, e))

  def ToString(self):
    if not self._value:
      raise ValueError("can't call ToString() on an empty hunt id.")

    return self._value


class ApiHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntReference
  rdf_deps = [
      ApiHuntId,
  ]

  def FromHuntReference(self, reference):
    self.hunt_id = reference.hunt_id
    return self


class ApiFlowLikeObjectReference(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiFlowLikeObjectReference
  rdf_deps = [
      ApiHuntReference,
      api_flow.ApiFlowReference,
  ]


class ApiHunt(rdf_structs.RDFProtoStruct):
  """ApiHunt is used when rendering responses.

  ApiHunt is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and to not expose implementation defails.
  """

  protobuf = hunt_pb2.ApiHunt
  rdf_deps = [
      ApiHuntId,
      ApiFlowLikeObjectReference,
      foreman_rules.ForemanClientRuleSet,
      rdf_hunts.HuntRunnerArgs,
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def GetFlowArgsClass(self):
    if self.hunt_type == ApiHunt.HuntType.STANDARD and self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type
    elif self.hunt_type == ApiHunt.HuntType.VARIABLE:
      return rdf_hunt_objects.HuntArgumentsVariable

  def ObjectReference(self):
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.HUNT,
        hunt=rdf_objects.HuntReference(hunt_id=str(self.hunt_id)),
    )


class ApiHuntResult(rdf_structs.RDFProtoStruct):
  """API hunt results object."""

  protobuf = hunt_pb2.ApiHuntResult
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromFlowResult(self, flow_result):
    """Init from rdf_flow_objects.FlowResult."""

    self.payload_type = flow_result.payload.__class__.__name__
    self.payload = flow_result.payload
    self.client_id = flow_result.client_id
    self.timestamp = flow_result.timestamp

    return self


class ApiHuntClient(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntClient
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiHuntLog(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntLog
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromFlowLog(self, fl):
    if fl.HasField("client_id"):
      self.client_id = fl.client_id.Basename()
      if fl.HasField("urn"):
        self.flow_id = fl.urn.RelativeName(fl.client_id)

    self.timestamp = fl.age
    self.log_message = fl.log_message
    self.flow_name = fl.flow_name

    return self


class ApiHuntError(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntError
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiListHuntsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntsArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
  ]


class ApiListHuntsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntsResult
  rdf_deps = [
      ApiHunt,
  ]


def _ApiToObjectHuntStateProto(
    state: ApiHunt.State,
) -> hunts_pb2.Hunt.HuntState:
  """Converts ApiHunt.State to hunts_pb2.Hunt.HuntState."""
  if state == ApiHunt.State.PAUSED:
    return hunts_pb2.Hunt.HuntState.PAUSED
  elif state == ApiHunt.State.STARTED:
    return hunts_pb2.Hunt.HuntState.STARTED
  elif state == ApiHunt.State.STOPPED:
    return hunts_pb2.Hunt.HuntState.STOPPED
  elif state == ApiHunt.State.COMPLETED:
    return hunts_pb2.Hunt.HuntState.COMPLETED
  else:
    return hunts_pb2.Hunt.HuntState.UNKNOWN


def _HuntStateToApiHuntState(
    state: hunts_pb2.Hunt.HuntState,
) -> hunt_pb2.ApiHunt.State:
  """Converts hunts_pb2.Hunt.HuntState to ApiHunt.State."""
  if state == hunts_pb2.Hunt.HuntState.PAUSED:
    return hunt_pb2.ApiHunt.State.PAUSED
  elif state == hunts_pb2.Hunt.HuntState.STARTED:
    return hunt_pb2.ApiHunt.State.STARTED
  elif state == hunts_pb2.Hunt.HuntState.STOPPED:
    return hunt_pb2.ApiHunt.State.STOPPED
  elif state == hunts_pb2.Hunt.HuntState.COMPLETED:
    return hunt_pb2.ApiHunt.State.COMPLETED

  raise ValueError(f"Unknown hunt state: {state}")


def _HuntStateReasonToApiHuntStateReason(
    reason: hunts_pb2.Hunt.HuntStateReason,
) -> hunt_pb2.ApiHunt.StateReason:
  """Converts a hunts_pb2.Hunt.HuntStateReason to an hunt_pb2.ApiHunt.StateReason."""
  if reason == hunts_pb2.Hunt.HuntStateReason.UNKNOWN:
    return hunt_pb2.ApiHunt.StateReason.UNKNOWN
  elif reason == hunts_pb2.Hunt.HuntStateReason.DEADLINE_REACHED:
    return hunt_pb2.ApiHunt.StateReason.DEADLINE_REACHED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_CLIENTS_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.TOTAL_CLIENTS_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_CRASHES_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.TOTAL_CRASHES_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_NETWORK_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.TOTAL_NETWORK_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_RESULTS_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.AVG_RESULTS_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.AVG_NETWORK_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_CPU_EXCEEDED:
    return hunt_pb2.ApiHunt.StateReason.AVG_CPU_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TRIGGERED_BY_USER:
    return hunt_pb2.ApiHunt.StateReason.TRIGGERED_BY_USER

  raise ValueError(f"Unknown hunt state reason: {reason}")


class ApiListHuntsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of available hunts."""

  args_type = ApiListHuntsArgs
  result_type = ApiListHuntsResult
  proto_args_type = hunt_pb2.ApiListHuntsArgs
  proto_result_type = hunt_pb2.ApiListHuntsResult

  def _CreatedByFilterRelational(
      self,
      username: str,
      hunt_obj: rdf_hunt_objects.Hunt,
  ):
    return hunt_obj.creator == username

  def _IsRobotFilterRelational(self, hunt_obj: rdf_hunt_objects.Hunt):
    return hunt_obj.is_robot

  def _IsHumanFilterRelational(self, hunt_obj: rdf_hunt_objects.Hunt):
    return not hunt_obj.is_robot

  def _DescriptionContainsFilterRelational(
      self,
      substring: str,
      hunt_obj: rdf_hunt_objects.Hunt,
  ):
    return substring in hunt_obj.description

  def _Username(self, username: str, context: api_call_context.ApiCallContext):
    if username == "me":
      return context.username
    else:
      return username

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntsResult:
    if args.description_contains and not args.active_within:
      raise ValueError(
          "description_contains filter has to be "
          "used together with active_within filter"
      )

    kw_args = {}
    if args.created_by:
      kw_args["with_creator"] = self._Username(args.created_by, context)
    if args.HasField("robot_filter"):
      if args.robot_filter == args.RobotFilter.ONLY_ROBOTS:
        kw_args["created_by"] = access_control.SYSTEM_USERS
      elif args.robot_filter == args.RobotFilter.NO_ROBOTS:
        kw_args["not_created_by"] = access_control.SYSTEM_USERS
    if args.description_contains:
      kw_args["with_description_match"] = args.description_contains
    if args.active_within:
      kw_args["created_after"] = rdfvalue.RDFDatetime.Now() - args.active_within
    if args.with_state:
      kw_args["with_states"] = [_ApiToObjectHuntStateProto(args.with_state)]

    # TODO(user): total_count is not returned by the current implementation.
    # It's not clear, if it's needed - GRR UI doesn't show total number of
    # available hunts anywhere. Adding it would require implementing
    # an additional data_store.REL_DB.CountHuntObjects method.

    if args.with_full_summary:
      hunt_objects = data_store.REL_DB.ReadHuntObjects(
          args.offset, args.count or db.MAX_COUNT, **kw_args
      )
      hunt_ids = [h.hunt_id for h in hunt_objects]
      hunt_counters = data_store.REL_DB.ReadHuntsCounters(hunt_ids)

      items = []
      for hunt_obj in hunt_objects:
        items.append(
            InitApiHuntFromHuntObject(
                hunt_obj,
                hunt_counters=hunt_counters[hunt_obj.hunt_id],
                with_full_summary=True,
            )
        )

    else:
      hunt_objects = data_store.REL_DB.ListHuntObjects(
          args.offset, args.count or db.MAX_COUNT, **kw_args
      )
      items = [InitApiHuntFromHuntMetadata(h) for h in hunt_objects]
    return hunt_pb2.ApiListHuntsResult(items=items)


class ApiVerifyHuntAccessArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiVerifyHuntAccessArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiVerifyHuntAccessResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiVerifyHuntAccessResult
  rdf_deps = []


class ApiVerifyHuntAccessHandler(api_call_handler_base.ApiCallHandler):
  """Dummy handler that renders empty message."""

  args_type = ApiVerifyHuntAccessArgs
  result_type = ApiVerifyHuntAccessResult
  proto_args_type = hunt_pb2.ApiVerifyHuntAccessArgs
  proto_result_type = hunt_pb2.ApiVerifyHuntAccessResult

  def Handle(
      self,
      args: hunt_pb2.ApiVerifyHuntAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiVerifyHuntAccessResult:
    return hunt_pb2.ApiVerifyHuntAccessResult()


class ApiGetHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  args_type = ApiGetHuntArgs
  result_type = ApiHunt
  proto_args_type = hunt_pb2.ApiGetHuntArgs
  proto_result_type = hunt_pb2.ApiHunt

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiHunt:
    try:
      hunt_id = str(args.hunt_id)
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
      return InitApiHuntFromHuntObject(
          hunt_obj, hunt_counters=hunt_counters, with_full_summary=True
      )
    except db.UnknownHuntError as ex:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id
      ) from ex


class ApiCountHuntResultsByTypeArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiCountHuntResultsByTypeArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiTypeCount(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiTypeCount
  rdf_deps = []


class ApiCountHuntResultsByTypeResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiCountHuntResultsByTypeResult
  rdf_deps = [
      ApiTypeCount,
  ]


class ApiCountHuntResultsByTypeHandler(api_call_handler_base.ApiCallHandler):
  """Counts all hunt results by type."""

  args_type = ApiCountHuntResultsByTypeArgs
  result_type = ApiCountHuntResultsByTypeResult
  proto_args_type = hunt_pb2.ApiCountHuntResultsByTypeArgs
  proto_result_type = hunt_pb2.ApiCountHuntResultsByTypeResult

  def Handle(
      self,
      args: hunt_pb2.ApiCountHuntResultsByTypeArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiCountHuntResultsByTypeResult:
    counts = data_store.REL_DB.CountHuntResultsByType(str(args.hunt_id))
    return hunt_pb2.ApiCountHuntResultsByTypeResult(
        items=[
            hunt_pb2.ApiTypeCount(type=type, count=count)
            for (type, count) in counts.items()
        ]
    )


class ApiListHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntResultsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntResultsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntResultsResult
  rdf_deps = [
      ApiHuntResult,
  ]


class ApiListHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt results."""

  args_type = ApiListHuntResultsArgs
  result_type = ApiListHuntResultsResult

  def Handle(self, args, context=None):
    results = data_store.REL_DB.ReadHuntResults(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
        with_type=args.with_type or None,
    )

    total_count = data_store.REL_DB.CountHuntResults(
        str(args.hunt_id), with_type=args.with_type or None
    )

    results = [mig_flow_objects.ToRDFFlowResult(r) for r in results]
    return ApiListHuntResultsResult(
        items=[ApiHuntResult().InitFromFlowResult(r) for r in results],
        total_count=total_count,
    )


class ApiListHuntCrashesArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntCrashesArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntCrashesResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntCrashesResult
  rdf_deps = [
      rdf_client.ClientCrash,
  ]


class ApiListHuntCrashesHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of client crashes for the given hunt."""

  args_type = ApiListHuntCrashesArgs
  result_type = ApiListHuntCrashesResult
  proto_args_type = hunt_pb2.ApiListHuntCrashesArgs
  proto_result_type = hunt_pb2.ApiListHuntCrashesResult

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntCrashesResult:
    flows = data_store.REL_DB.ReadHuntFlows(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY,
    )
    total_count = data_store.REL_DB.CountHuntFlows(
        str(args.hunt_id),
        filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY,
    )
    crash_infos = [f.client_crash_info for f in flows]
    return hunt_pb2.ApiListHuntCrashesResult(
        items=crash_infos, total_count=total_count
    )


class ApiGetHuntResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandResult


class ApiGetHuntResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders GRR export tool command line that exports hunt results."""

  args_type = ApiGetHuntResultsExportCommandArgs
  result_type = ApiGetHuntResultsExportCommandResult
  proto_args_type = hunt_pb2.ApiGetHuntResultsExportCommandArgs
  proto_result_type = hunt_pb2.ApiGetHuntResultsExportCommandResult

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiGetHuntResultsExportCommandResult:
    output_fname = re.sub("[^0-9a-zA-Z]+", "_", str(args.hunt_id))
    code_to_execute = (
        """grrapi.Hunt("%s").GetFilesArchive()."""
        """WriteToFile("./hunt_results_%s.zip")"""
    ) % (args.hunt_id, output_fname)

    export_command_str = " ".join([
        config.CONFIG["AdminUI.export_command"],
        "--exec_code",
        utils.ShellQuote(code_to_execute),
    ])

    return hunt_pb2.ApiGetHuntResultsExportCommandResult(
        command=export_command_str
    )


class ApiListHuntOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginsResult
  rdf_deps = [
      api_output_plugin.ApiOutputPlugin,
  ]


class ApiListHuntOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's output plugins states."""

  args_type = ApiListHuntOutputPluginsArgs
  result_type = ApiListHuntOutputPluginsResult
  proto_args_type = hunt_pb2.ApiListHuntOutputPluginsArgs
  proto_result_type = hunt_pb2.ApiListHuntOutputPluginsResult

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntOutputPluginsResult:

    try:
      output_plugin_states = data_store.REL_DB.ReadHuntOutputPluginsStates(
          args.hunt_id
      )
    except db.UnknownHuntError as ex:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % str(args.hunt_id)
      ) from ex

    def GetValue(
        attributed_dict: jobs_pb2.AttributedDict, key: str
    ) -> Optional[jobs_pb2.DataBlob]:
      for entry in attributed_dict.dat:
        if entry.k.string == key:
          return entry.v

    def RemoveKey(attributed_dict: jobs_pb2.AttributedDict, key: str):
      for entry in attributed_dict.dat:
        if entry.k.string == key:
          attributed_dict.dat.remove(entry)

    result = []
    used_names = collections.Counter()
    for output_plugin_state in output_plugin_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor

      name = plugin_descriptor.plugin_name
      plugin_id = f"{name}_{used_names[name]}"
      used_names[name] += 1

      state = jobs_pb2.AttributedDict()
      state.CopyFrom(output_plugin_state.plugin_state)

      if GetValue(state, "source_urn"):
        RemoveKey(state, "source_urn")
      if GetValue(state, "token"):
        RemoveKey(state, "token")
      if errors := GetValue(state, "errors"):
        if not errors.list.content:
          RemoveKey(state, "errors")
      if logs := GetValue(state, "logs"):
        if not logs.list.content:
          RemoveKey(state, "logs")
      if error_count := GetValue(state, "error_count"):
        if not error_count.integer:
          RemoveKey(state, "error_count")
      if success_count := GetValue(state, "success_count"):
        if not success_count.integer:
          RemoveKey(state, "success_count")

      api_plugin = output_plugin_pb2.ApiOutputPlugin()
      api_plugin.id = plugin_id
      api_plugin.plugin_descriptor.CopyFrom(plugin_descriptor)
      api_plugin.state.Pack(state)

      result.append(api_plugin)

    return hunt_pb2.ApiListHuntOutputPluginsResult(
        items=result, total_count=len(result)
    )


class ApiListHuntOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler
):
  """Base class used to define log and status messages handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  log_entry_type = None
  collection_type = None
  collection_counter = None

  def Handle(
      self,
      args: Union[
          hunt_pb2.ApiListHuntOutputPluginLogsArgs,
          hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
      ],
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> Union[
      hunt_pb2.ApiListHuntOutputPluginLogsResult,
      hunt_pb2.ApiListHuntOutputPluginErrorsResult,
  ]:
    h = data_store.REL_DB.ReadHuntObject(str(args.hunt_id))

    if self.__class__.log_entry_type is None:
      raise ValueError(
          "log_entry_type has to be overridden and set to a meaningful value."
      )

    index = api_flow.GetOutputPluginIndex(h.output_plugins, args.plugin_id)
    output_plugin_id = "%d" % index

    logs = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        str(args.hunt_id),
        output_plugin_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_type=self.__class__.log_entry_type,
    )
    total_count = data_store.REL_DB.CountHuntOutputPluginLogEntries(
        str(args.hunt_id),
        output_plugin_id,
        with_type=self.__class__.log_entry_type,
    )

    return self.proto_result_type(
        total_count=total_count,
        items=[
            rdf_flow_objects.ToOutputPluginBatchProcessingStatus(l)
            for l in logs
        ],
    )


class ApiListHuntOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginLogsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginLogsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListHuntOutputPluginLogsHandler(
    ApiListHuntOutputPluginLogsHandlerBase
):
  """Renders hunt's output plugin's log."""

  args_type = ApiListHuntOutputPluginLogsArgs
  result_type = ApiListHuntOutputPluginLogsResult
  proto_args_type = hunt_pb2.ApiListHuntOutputPluginLogsArgs
  proto_result_type = hunt_pb2.ApiListHuntOutputPluginLogsResult

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG

  collection_type = "logs"
  collection_counter = "success_count"


class ApiListHuntOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginErrorsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginErrorsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListHuntOutputPluginErrorsHandler(
    ApiListHuntOutputPluginLogsHandlerBase
):
  """Renders hunt's output plugin's errors."""

  args_type = ApiListHuntOutputPluginErrorsArgs
  result_type = ApiListHuntOutputPluginErrorsResult
  proto_args_type = hunt_pb2.ApiListHuntOutputPluginErrorsArgs
  proto_result_type = hunt_pb2.ApiListHuntOutputPluginErrorsResult

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR

  collection_type = "errors"
  collection_counter = "error_count"


class ApiListHuntLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsResult
  rdf_deps = [ApiHuntLog]


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of log elements for the given hunt."""

  args_type = ApiListHuntLogsArgs
  result_type = ApiListHuntLogsResult
  proto_args_type = hunt_pb2.ApiListHuntLogsArgs
  proto_result_type = hunt_pb2.ApiListHuntLogsResult

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntLogsResult:
    results = data_store.REL_DB.ReadHuntLogEntries(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
    )

    total_count = data_store.REL_DB.CountHuntLogEntries(str(args.hunt_id))

    return hunt_pb2.ApiListHuntLogsResult(
        items=[InitApiHuntLogFromFlowLogEntry(r) for r in results],
        total_count=total_count,
    )


class ApiListHuntErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsResult
  rdf_deps = [
      ApiHuntError,
  ]


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of errors for the given hunt."""

  args_type = ApiListHuntErrorsArgs
  result_type = ApiListHuntErrorsResult
  proto_args_type = hunt_pb2.ApiListHuntErrorsArgs
  proto_result_type = hunt_pb2.ApiListHuntErrorsResult

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntErrorsResult:
    total_count = data_store.REL_DB.CountHuntFlows(
        str(args.hunt_id),
        filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY,
    )

    errors = data_store.REL_DB.ReadHuntFlowErrors(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
    )

    if args.filter:

      def MatchesFilter(
          client_id: str,
          info: db.FlowErrorInfo,
      ) -> bool:
        if args.filter in client_id:
          return True
        if args.filter in info.message:
          return True
        if info.backtrace is not None and args.filter in info.backtrace:
          return True

        return False

      errors = {
          client_id: info
          for client_id, info in errors.items()
          if MatchesFilter(client_id, info)
      }

    return hunt_pb2.ApiListHuntErrorsResult(
        items=[
            InitApiHuntErrorFromFlowErrorInfo(client_id, info)
            for client_id, info in errors.items()
        ],
        total_count=total_count,
    )


class ApiGetHuntClientCompletionStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntClientCompletionStatsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntClientCompletionStatsResult(rdf_structs.RDFProtoStruct):
  """Result for getting the client completions of a hunt."""

  protobuf = hunt_pb2.ApiGetHuntClientCompletionStatsResult
  rdf_deps = [
      rdf_stats.SampleFloat,
  ]


class ApiGetHuntClientCompletionStatsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Calculates hunt's client completion stats."""

  args_type = ApiGetHuntClientCompletionStatsArgs
  result_type = ApiGetHuntClientCompletionStatsResult
  proto_args_type = hunt_pb2.ApiGetHuntClientCompletionStatsArgs
  proto_result_type = hunt_pb2.ApiGetHuntClientCompletionStatsResult

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiGetHuntClientCompletionStatsResult:

    states_and_timestamps = data_store.REL_DB.ReadHuntFlowsStatesAndTimestamps(
        str(args.hunt_id)
    )
    num_buckets = max(1000, args.size)
    flow_creation_times, flow_completion_times = [], []

    for stat in states_and_timestamps:
      flow_creation_times.append(stat.create_time.AsSecondsSinceEpoch())
      if stat.flow_state != flows_pb2.Flow.FlowState.RUNNING:
        flow_completion_times.append(
            stat.last_update_time.AsSecondsSinceEpoch()
        )

    if not flow_creation_times:
      return hunt_pb2.ApiGetHuntClientCompletionStatsResult()

    min_timestamp = min(flow_creation_times)
    max_timestamp = max(flow_creation_times + flow_completion_times)

    started_histogram = Histogram(min_timestamp, max_timestamp, num_buckets)
    for timestamp in flow_creation_times:
      started_histogram.Insert(timestamp)

    completed_histogram = Histogram(min_timestamp, max_timestamp, num_buckets)
    for timestamp in flow_completion_times:
      completed_histogram.Insert(timestamp)

    return InitApiGetHuntClientCompletionStatsResultFromHistograms(
        started_histogram, completed_histogram
    )


class ApiGetHuntFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntFilesArchiveArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  args_type = ApiGetHuntFilesArchiveArgs
  proto_args_type = hunt_pb2.ApiGetHuntFilesArchiveArgs

  def _WrapContentGenerator(
      self,
      generator: archive_generator.CollectionArchiveGenerator,
      collection: Iterable[flows_pb2.FlowResult],
      args: hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: api_call_context.ApiCallContext,
  ) -> Iterator[bytes]:
    try:

      for item in generator.Generate(collection):
        yield item

      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of hunt %s results (archived %d "
          "out of %d items, archive size is %d)"
          % (
              args.hunt_id,
              len(generator.archived_files),
              generator.total_files,
              generator.output_size,
          ),
          None,
      )
    except Exception as e:
      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for hunt %s: %s" % (args.hunt_id, e),
          None,
      )

      raise

  def _LoadData(
      self,
      hunt_id: str,
  ) -> Tuple[Iterable[flows_pb2.FlowResult], str]:
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    hunt_api_object = InitApiHuntFromHuntObject(hunt_obj)
    description = (
        "Files downloaded by hunt %s (%s, '%s') created by user %s on %s"
        % (
            hunt_api_object.name,
            hunt_api_object.hunt_id,
            hunt_api_object.description,
            hunt_api_object.creator,
            hunt_api_object.created,
        )
    )
    # TODO(user): write general-purpose batcher for such cases.
    results = data_store.REL_DB.ReadHuntResults(
        hunt_id, offset=0, count=db.MAX_COUNT
    )
    return results, description

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    assert context is not None
    collection, description = self._LoadData(args.hunt_id)
    target_file_prefix = "hunt_" + str(args.hunt_id).replace(":", "_")

    if (
        args.archive_format
        == hunt_pb2.ApiGetHuntFilesArchiveArgs.ArchiveFormat.ZIP
    ):
      archive_format = archive_generator.ArchiveFormat.ZIP
      file_extension = ".zip"
    elif (
        args.archive_format
        == hunt_pb2.ApiGetHuntFilesArchiveArgs.ArchiveFormat.TAR_GZ
    ):
      archive_format = archive_generator.ArchiveFormat.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    generator = archive_generator.CollectionArchiveGenerator(
        prefix=target_file_prefix,
        description=description,
        archive_format=archive_format,
    )
    content_generator = self._WrapContentGenerator(
        generator, collection, args, context=context
    )
    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension, content_generator=content_generator
    )


class ApiGetHuntFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntFileArgs
  rdf_deps = [
      api_client.ApiClientId,
      ApiHuntId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetHuntFileHandler(api_call_handler_base.ApiCallHandler):
  """Downloads a file referenced in the hunt results."""

  args_type = ApiGetHuntFileArgs
  proto_args_type = hunt_pb2.ApiGetHuntFileArgs

  MAX_RECORDS_TO_CHECK = 1024
  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateFile(self, fd):
    while True:
      chunk = fd.read(self.CHUNK_SIZE)
      if chunk:
        yield chunk
      else:
        break

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntFileArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    if not args.hunt_id:
      raise ValueError("ApiGetHuntFileArgs.hunt_id can't be unset")

    if not args.client_id:
      raise ValueError("ApiGetHuntFileArgs.client_id can't be unset")

    if not args.vfs_path:
      raise ValueError("ApiGetHuntFileArgs.vfs_path can't be unset")

    if not args.timestamp:
      raise ValueError("ApiGetHuntFileArgs.timestamp can't be unset")

    api_vfs.ValidateVfsPath(args.vfs_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.vfs_path)
    expected_client_path = db.ClientPath(
        str(args.client_id), path_type, components
    )

    results = data_store.REL_DB.ReadHuntResults(
        str(args.hunt_id),
        offset=0,
        count=self.MAX_RECORDS_TO_CHECK,
        with_timestamp=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            args.timestamp
        ),
    )
    for item in results:
      try:
        client_path = export.FlowResultToClientPath(item)
      except export.ItemNotExportableError:
        continue

      if client_path != expected_client_path:
        continue

      try:
        # TODO(user): this effectively downloads the latest version of
        # the file and always disregards the timestamp. Reconsider this logic
        # after AFF4 implementation is gone. We also most likely don't need
        # the MAX_RECORDS_TO_CHECK logic in the new implementation.
        file_obj = file_store.OpenFile(client_path)
        return api_call_handler_base.ApiBinaryStream(
            "%s_%s" % (args.client_id, os.path.basename(file_obj.Path())),
            content_generator=self._GenerateFile(file_obj),
            content_length=file_obj.size,
        )
      except (file_store.FileHasNoContentError, file_store.FileNotFoundError):
        break

    raise HuntFileNotFoundError(
        "File %s with timestamp %s and client %s "
        "wasn't found among the results of hunt %s"
        % (args.vfs_path, args.timestamp, args.client_id, args.hunt_id)
    )


class ApiGetHuntStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntStatsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntStatsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntStatsResult
  rdf_deps = [
      rdf_stats.ClientResourcesStats,
  ]


class ApiGetHuntStatsHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt stats request."""

  args_type = ApiGetHuntStatsArgs
  result_type = ApiGetHuntStatsResult
  proto_args_type = hunt_pb2.ApiGetHuntStatsArgs
  proto_result_type = hunt_pb2.ApiGetHuntStatsResult

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiGetHuntStatsResult:
    del context  # Unused.
    stats = data_store.REL_DB.ReadHuntClientResourcesStats(str(args.hunt_id))
    return hunt_pb2.ApiGetHuntStatsResult(stats=stats)


class ApiListHuntClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntClientsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntClientsResult
  rdf_deps = [
      ApiHuntClient,
  ]


class ApiListHuntClientsHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt clients."""

  args_type = ApiListHuntClientsArgs
  result_type = ApiListHuntClientsResult
  proto_args_type = hunt_pb2.ApiListHuntClientsArgs
  proto_result_type = hunt_pb2.ApiListHuntClientsResult

  def Handle(
      self,
      args: hunt_pb2.ApiListHuntClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiListHuntClientsResult:

    filter_condition = db.HuntFlowsCondition.UNSET
    status = args.client_status
    if status == hunt_pb2.ApiListHuntClientsArgs.ClientStatus.OUTSTANDING:
      filter_condition = db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY
    elif status == hunt_pb2.ApiListHuntClientsArgs.ClientStatus.COMPLETED:
      filter_condition = db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY

    total_count = data_store.REL_DB.CountHuntFlows(
        args.hunt_id, filter_condition=filter_condition
    )
    hunt_flows = data_store.REL_DB.ReadHuntFlows(
        args.hunt_id,
        args.offset,
        args.count or db.MAX_COUNT,
        filter_condition=filter_condition,
    )
    results = [
        hunt_pb2.ApiHuntClient(client_id=hf.client_id, flow_id=hf.flow_id)
        for hf in hunt_flows
    ]

    return hunt_pb2.ApiListHuntClientsResult(
        items=results, total_count=total_count
    )


class ApiGetHuntContextArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntContextArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntContextResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntContextResult
  rdf_deps = [
      api_call_handler_utils.ApiDataObject,
      rdf_hunts.HuntContext,
  ]


class ApiGetHuntContextHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt contexts."""

  args_type = ApiGetHuntContextArgs
  result_type = ApiGetHuntContextResult
  proto_args_type = hunt_pb2.ApiGetHuntContextArgs
  proto_result_type = hunt_pb2.ApiGetHuntContextResult

  def Handle(
      self,
      args: hunt_pb2.ApiGetHuntContextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiGetHuntContextResult:
    h = data_store.REL_DB.ReadHuntObject(args.hunt_id)
    h_counters = data_store.REL_DB.ReadHuntCounters(args.hunt_id)
    context = flows_pb2.HuntContext(
        session_id=str(rdfvalue.RDFURN("hunts").Add(h.hunt_id)),
        create_time=h.create_time,
        creator=h.creator,
        duration=h.duration,
        network_bytes_sent=h_counters.total_network_bytes_sent,
        next_client_due=h.last_start_time,
        start_time=h.last_start_time,
        # TODO(user): implement proper hunt client resources starts support
        # for REL_DB hunts.
        # usage_stats=h.client_resources_stats
    )
    return hunt_pb2.ApiGetHuntContextResult(
        context=context, state=api_utils_pb2.ApiDataObject()
    )


class ApiCreateHuntArgs(rdf_structs.RDFProtoStruct):
  """Args for the ApiCreateHuntHandler."""

  protobuf = hunt_pb2.ApiCreateHuntArgs
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
      ApiHuntReference,
      api_flow.ApiFlowReference,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  args_type = ApiCreateHuntArgs
  result_type = ApiHunt
  proto_args_type = hunt_pb2.ApiCreateHuntArgs
  proto_result_type = hunt_pb2.ApiHunt

  def Handle(
      self,
      args: hunt_pb2.ApiCreateHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiHunt:
    hra = args.hunt_runner_args

    flow_cls = registry.FlowRegistry.FlowClassByName(args.flow_name)
    if flow_cls.block_hunt_creation:
      raise ValueError(f"Flow '{args.flow_name}' cannot run as hunt")

    hunt_obj = models_hunts.CreateHunt(
        duration=hra.expiry_time,
        client_rate=hra.client_rate,
        client_limit=hra.client_limit,
        crash_limit=hra.crash_limit,
        avg_results_per_client_limit=hra.avg_results_per_client_limit,
        avg_cpu_seconds_per_client_limit=hra.avg_cpu_seconds_per_client_limit,
        avg_network_bytes_per_client_limit=hra.avg_network_bytes_per_client_limit,
    )

    hunt_obj.args.standard.flow_name = args.flow_name
    if args.HasField("flow_args"):
      hunt_obj.args.hunt_type = hunts_pb2.HuntArguments.HuntType.STANDARD
      hunt_obj.args.standard.flow_args.CopyFrom(args.flow_args)
    hunt_obj.creator = context.username

    if hra.HasField("client_rule_set"):
      hunt_obj.client_rule_set.CopyFrom(hra.client_rule_set)

    protobuf_utils.CopyAttr(hra, hunt_obj, "description")
    protobuf_utils.CopyAttr(hra, hunt_obj, "per_client_cpu_limit")
    protobuf_utils.CopyAttr(
        hra,
        hunt_obj,
        "per_client_network_limit_bytes",
        "per_client_network_bytes_limit",
    )
    protobuf_utils.CopyAttr(
        hra, hunt_obj, "network_bytes_limit", "total_network_bytes_limit"
    )

    if args.HasField("original_hunt") and args.HasField("original_flow"):
      raise ValueError(
          "A hunt can't be a copy of a flow and a hunt at the same time."
      )

    if args.HasField("original_hunt"):
      hunt_obj.original_object.object_type = (
          flows_pb2.FlowLikeObjectReference.ObjectType.HUNT_REFERENCE
      )
      hunt_obj.original_object.hunt_reference.hunt_id = (
          args.original_hunt.hunt_id
      )
    elif args.HasField("original_flow"):
      hunt_obj.original_object.object_type = (
          flows_pb2.FlowLikeObjectReference.ObjectType.FLOW_REFERENCE
      )
      hunt_obj.original_object.flow_reference.flow_id = (
          args.original_flow.flow_id
      )
      hunt_obj.original_object.flow_reference.client_id = (
          args.original_flow.client_id
      )

    hunt_obj.output_plugins.extend(hra.output_plugins)

    hunt.CreateHunt(hunt_obj)

    return InitApiHuntFromHuntObject(hunt_obj, with_full_summary=True)


class ApiModifyHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiModifyHuntArgs
  rdf_deps = [
      ApiHuntId,
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
  ]


class ApiModifyHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt modifys (this includes starting/stopping the hunt)."""

  args_type = ApiModifyHuntArgs
  result_type = ApiHunt
  proto_args_type = hunt_pb2.ApiModifyHuntArgs
  proto_result_type = hunt_pb2.ApiHunt

  def Handle(
      self,
      args: hunt_pb2.ApiModifyHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> hunt_pb2.ApiHunt:
    hunt_id = str(args.hunt_id)

    has_change = False
    for field_name in ["client_limit", "client_rate", "duration"]:
      if args.HasField(field_name):
        has_change = True
        break

    try:
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      if has_change:
        kw_args = {}
        if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
          raise HuntNotModifiableError(
              "Hunt's client limit/client rate/expiry time attributes "
              "can only be changed if hunt's current state is "
              "PAUSED"
          )

        if args.HasField("client_limit"):
          kw_args["client_limit"] = args.client_limit

        if args.HasField("client_rate"):
          kw_args["client_rate"] = args.client_rate
        if args.HasField("duration"):
          kw_args["duration"] = rdfvalue.DurationSeconds(args.duration)

        data_store.REL_DB.UpdateHuntObject(hunt_id, **kw_args)
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    except db.UnknownHuntError:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id
      ) from None

    if args.HasField("state"):
      if args.state == ApiHunt.State.STARTED:
        if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
          raise HuntNotStartableError(
              "Hunt can only be started from PAUSED state."
          )
        hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
        hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
      elif args.state == ApiHunt.State.STOPPED:
        if hunt_obj.hunt_state not in [
            hunts_pb2.Hunt.HuntState.PAUSED,
            hunts_pb2.Hunt.HuntState.STARTED,
        ]:
          raise HuntNotStoppableError(
              "Hunt can only be stopped from STARTED or PAUSED states."
          )
        hunt_obj = hunt.StopHunt(
            hunt_obj.hunt_id,
            hunt_state_reason=hunts_pb2.Hunt.HuntStateReason.TRIGGERED_BY_USER,
            reason_comment=CANCELLED_BY_USER,
        )
        hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)

      else:
        raise InvalidHuntStateError(
            "Hunt's state can only be updated to STARTED or STOPPED"
        )

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_obj.hunt_id)
    return InitApiHuntFromHuntObject(
        hunt_obj, hunt_counters=hunt_counters, with_full_summary=True
    )


class ApiDeleteHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiDeleteHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiDeleteHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt deletions."""

  args_type = ApiDeleteHuntArgs
  proto_args_type = hunt_pb2.ApiDeleteHuntArgs

  def Handle(
      self,
      args: hunt_pb2.ApiDeleteHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    try:
      h = data_store.REL_DB.ReadHuntObject(str(args.hunt_id))
      h_flows_count = data_store.REL_DB.CountHuntFlows(h.hunt_id)

      if h.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED or h_flows_count > 0:
        raise HuntNotDeletableError(
            "Can only delete a paused hunt without scheduled clients."
        )

      data_store.REL_DB.DeleteHuntObject(h.hunt_id)
    except db.UnknownHuntError as ex:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id
      ) from ex


class ApiGetExportedHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetExportedHuntResultsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetExportedHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given hunt with an instant output plugin."""

  args_type = ApiGetExportedHuntResultsArgs
  proto_args_type = hunt_pb2.ApiGetExportedHuntResultsArgs

  _RESULTS_PAGE_SIZE = 1000

  def Handle(
      self,
      args: hunt_pb2.ApiGetExportedHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    source_urn = rdfvalue.RDFURN("hunts").Add(args.hunt_id)

    iop_cls = instant_output_plugin.InstantOutputPlugin
    plugin_cls = iop_cls.GetPluginClassByPluginName(args.plugin_name)
    # TODO(user): Instant output plugins shouldn't depend on URNs.
    plugin = plugin_cls(source_urn=source_urn)

    types = data_store.REL_DB.CountHuntResultsByType(args.hunt_id)

    def FetchFn(type_name):
      """Fetches all hunt results of a given type."""
      offset = 0
      while True:
        results = data_store.REL_DB.ReadHuntResults(
            args.hunt_id,
            offset=offset,
            count=self._RESULTS_PAGE_SIZE,
            with_type=type_name,
        )

        if not results:
          break

        for r in results:
          r = mig_flow_objects.ToRDFFlowResult(r)
          msg = r.AsLegacyGrrMessage()
          msg.source_urn = source_urn
          yield msg

        offset += self._RESULTS_PAGE_SIZE

    content_generator = instant_output_plugin.ApplyPluginToTypedCollection(
        plugin, types, FetchFn
    )

    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator
    )


class PerClientFileCollectionArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.PerClientFileCollectionArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiCreatePerClientFileCollectionHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
      PerClientFileCollectionArgs,
  ]


class ApiCreatePerClientFileCollectionHuntHandler(
    api_call_handler_base.ApiCallHandler
):
  """Creates a variable hunt to collect files across multiple clients."""

  args_type = ApiCreatePerClientFileCollectionHuntArgs
  result_type = ApiHunt
  proto_args_type = hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs
  proto_result_type = hunt_pb2.ApiHunt

  MAX_CLIENTS = 250
  MAX_FILES = 1000

  def Handle(
      self,
      args: hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs,  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
      context: api_call_context.ApiCallContext,
  ) -> hunt_pb2.ApiHunt:
    if len(args.per_client_args) > self.MAX_CLIENTS:
      raise ValueError(
          f"At most {self.MAX_CLIENTS} clients can be specified "
          "in a per-client file collection hunt."
      )

    if sum(len(pca.paths) for pca in args.per_client_args) > self.MAX_FILES:
      raise ValueError(
          f"At most {self.MAX_FILES} file paths can be specified "
          "in a per-client file collection hunt."
      )
    hunt_args = ApiCreatePerClientFileCollectionHuntArgToHuntArgs(args)

    hunt_args = mig_hunt_objects.ToRDFHuntArguments(hunt_args)
    hunt_obj = rdf_hunt_objects.Hunt(
        args=hunt_args,
        description=args.description,
        creator=context.username,
        client_rate=0.0,
    )
    if args.HasField("duration_secs"):
      hunt_obj.duration = rdfvalue.DurationSeconds(args.duration_secs)
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    hunt.CreateHunt(hunt_obj)

    return InitApiHuntFromHuntObject(hunt_obj, with_full_summary=True)


# TODO: Temporary copy of migration function due to cyclic
# dependency.
def ToRDFApiHunt(proto: hunt_pb2.ApiHunt) -> ApiHunt:
  return ApiHunt.FromSerializedBytes(proto.SerializeToString())
