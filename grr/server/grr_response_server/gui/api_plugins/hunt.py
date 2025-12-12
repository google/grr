#!/usr/bin/env python
"""API handlers for accessing hunts."""

import collections
from collections.abc import Iterable, Iterator, Sequence
import math
import os
import re
from typing import Optional, Union

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import analysis_pb2
from grr_response_proto import api_utils_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_proto.api import output_plugin_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import instant_output_plugin
from grr_response_server import instant_output_plugin_registry
from grr_response_server import notification
from grr_response_server.databases import db
from grr_response_server.flows.general import export
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.models import hunts as models_hunts
from grr_response_server.models import protobuf_utils as models_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects


HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")

# fmt: off

CANCELLED_BY_USER = "Cancelled by user"

# /grr/server/grr_response_server/hunt.py,
# fmt: on


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


class InstantOutputPluginNotFoundError(
    api_call_handler_base.ResourceNotFoundError
):
  """Raised when an instant output plugin is not found."""


def ApiFlowLikeObjectReferenceFromReference(
    reference: flows_pb2.FlowLikeObjectReference,
) -> api_hunt_pb2.ApiFlowLikeObjectReference:
  """Converts a FlowLikeObjectReference to an ApiFlowLikeObjectReference."""
  ref = api_hunt_pb2.ApiFlowLikeObjectReference(
      object_type=api_hunt_pb2.ApiFlowLikeObjectReference.ObjectType.Name(
          reference.object_type
      )
  )
  reference_type = flows_pb2.FlowLikeObjectReference.ObjectType
  if reference.object_type == reference_type.HUNT_REFERENCE:
    ref.hunt_reference.CopyFrom(
        api_hunt_pb2.ApiHuntReference(hunt_id=reference.hunt_reference.hunt_id)
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
) -> api_hunt_pb2.ApiHunt:
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
  api_hunt = api_hunt_pb2.ApiHunt()
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
  models_utils.CopyAttr(hunt_obj, api_hunt, "hunt_id")
  models_utils.CopyAttr(hunt_obj, api_hunt, "crash_limit")
  models_utils.CopyAttr(hunt_obj, api_hunt, "client_limit")
  models_utils.CopyAttr(hunt_obj, api_hunt, "client_rate")
  models_utils.CopyAttr(hunt_obj, api_hunt, "create_time", "created")
  models_utils.CopyAttr(hunt_obj, api_hunt, "duration")
  models_utils.CopyAttr(hunt_obj, api_hunt, "creator")
  models_utils.CopyAttr(hunt_obj, api_hunt, "init_start_time")
  models_utils.CopyAttr(hunt_obj, api_hunt, "last_start_time")
  models_utils.CopyAttr(hunt_obj, api_hunt, "description")
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
          + hunt_counters.num_crashed_clients
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
    models_utils.CopyAttr(api_hunt, hra, "name", "hunt_name")
    models_utils.CopyAttr(hunt_obj, hra, "description")
    models_utils.CopyAttr(hunt_obj, hra, "crash_limit")
    models_utils.CopyAttr(hunt_obj, hra, "client_limit")
    models_utils.CopyAttr(hunt_obj, hra, "duration", "expiry_time")
    models_utils.CopyAttr(hunt_obj, hra, "avg_results_per_client_limit")
    models_utils.CopyAttr(hunt_obj, hra, "avg_cpu_seconds_per_client_limit")
    models_utils.CopyAttr(hunt_obj, hra, "avg_network_bytes_per_client_limit")
    models_utils.CopyAttr(hunt_obj, hra, "client_rate")
    models_utils.CopyAttr(hunt_obj, hra, "per_client_cpu_limit")
    models_utils.CopyAttr(
        hunt_obj,
        hra,
        "per_client_network_bytes_limit",
        "per_client_network_limit_bytes",
    )
    models_utils.CopyAttr(
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
) -> api_hunt_pb2.ApiHunt:
  """Initialize API hunt object from a hunt metadata object.

  Args:
    hunt_metadata: HuntMetadata to read the data from.

  Returns:
    A ApiHunt object.
  """
  api_hunt = api_hunt_pb2.ApiHunt(
      urn=str(rdfvalue.RDFURN("hunts").Add(str(hunt_metadata.hunt_id))),
      state=_HuntStateToApiHuntState(hunt_metadata.hunt_state),
      is_robot=hunt_metadata.creator in access_control.SYSTEM_USERS,
  )

  models_utils.CopyAttr(hunt_metadata, api_hunt, "hunt_id")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "client_limit")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "client_rate")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "create_time", "created")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "init_start_time")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "last_start_time")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "duration")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "creator")
  models_utils.CopyAttr(hunt_metadata, api_hunt, "description")
  return api_hunt


def InitApiHuntLogFromFlowLogEntry(
    fle: flows_pb2.FlowLogEntry,
) -> api_hunt_pb2.ApiHuntLog:
  """Init ApiHuntLog from FlowLogEntry."""

  hunt_log = api_hunt_pb2.ApiHuntLog()

  # TODO(user): putting this stub value for backwards compatibility.
  # Remove as soon as AFF4 is gone.
  hunt_log.flow_name = "GenericHunt"

  models_utils.CopyAttr(fle, hunt_log, "client_id")
  models_utils.CopyAttr(fle, hunt_log, "flow_id")
  models_utils.CopyAttr(fle, hunt_log, "timestamp")
  models_utils.CopyAttr(fle, hunt_log, "message", "log_message")

  return hunt_log


def InitApiHuntErrorFromFlowErrorInfo(
    client_id: str,
    info: db.FlowErrorInfo,
) -> api_hunt_pb2.ApiHuntError:
  """Init ApiHuntError from FlowErrorInfo."""

  hunt_error = api_hunt_pb2.ApiHuntError()
  hunt_error.client_id = client_id
  hunt_error.log_message = info.message
  hunt_error.timestamp = info.time.AsMicrosecondsSinceEpoch()

  if info.backtrace is not None:
    hunt_error.backtrace = info.backtrace

  return hunt_error


def InitApiHuntResultFromFlowResult(
    flow_result: flows_pb2.FlowResult,
) -> api_hunt_pb2.ApiHuntResult:
  """Init ApiFlowResult from FlowResult."""
  api_flow_result = api_hunt_pb2.ApiHuntResult()
  api_flow_result.payload.CopyFrom(flow_result.payload)
  models_utils.CopyAttr(flow_result, api_flow_result, "client_id")
  models_utils.CopyAttr(flow_result, api_flow_result, "timestamp")

  return api_flow_result


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
  max_timestamp: int
  num_buckets: int
  bucket_size: float
  buckets: list[Bucket]

  def __init__(
      self,
      min_timestamp: int,
      max_timestamp: int,
      num_buckets: int,
      values: list[int],
  ):
    self.min_timestamp = min_timestamp
    self.max_timestamp = max_timestamp
    self.num_buckets = num_buckets
    self.bucket_size = (max_timestamp - min_timestamp) / num_buckets

    self.buckets = []
    for i in range(num_buckets):
      lower = min_timestamp + i * self.bucket_size
      self.buckets.append(Bucket(lower_boundary_ts=lower))

    for value in values:
      self._Insert(value)

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

  def _Insert(self, timestamp: int) -> None:
    self.buckets[self._GetBucketIndex(timestamp)].count += 1

  def GetCumulativeHistogram(self) -> "Histogram":
    """Returns the cumulative histogram."""
    cumulative_histogram = Histogram(
        min_timestamp=self.min_timestamp,
        max_timestamp=self.max_timestamp,
        num_buckets=self.num_buckets,
        values=[],
    )
    cumulative_count = 0
    for index, bucket in enumerate(self.buckets):
      cumulative_count += bucket.count
      cumulative_histogram.buckets[index].count = cumulative_count

    return cumulative_histogram


def InitApiGetHuntClientCompletionStatsResultFromHistograms(
    flow_creation_histogram: Histogram,
    flow_completion_histogram: Histogram,
) -> api_hunt_pb2.ApiGetHuntClientCompletionStatsResult:
  """Initializes ApiGetHuntClientCompletionStatsResult from given histograms."""

  creation_time_samples = [
      analysis_pb2.SampleFloat(
          x_value=bucket.lower_boundary_ts,
          y_value=bucket.count,
      )
      for bucket in flow_creation_histogram.GetCumulativeHistogram().buckets
  ]

  completion_time_samples = [
      analysis_pb2.SampleFloat(
          x_value=bucket.lower_boundary_ts,
          y_value=bucket.count,
      )
      for bucket in flow_completion_histogram.GetCumulativeHistogram().buckets
  ]

  return api_hunt_pb2.ApiGetHuntClientCompletionStatsResult(
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
  protobuf = api_hunt_pb2.ApiHuntReference
  rdf_deps = [
      ApiHuntId,
  ]

  def FromHuntReference(self, reference):
    self.hunt_id = reference.hunt_id
    return self


class ApiFlowLikeObjectReference(rdf_structs.RDFProtoStruct):
  protobuf = api_hunt_pb2.ApiFlowLikeObjectReference
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

  protobuf = api_hunt_pb2.ApiHunt
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


def _ApiToObjectHuntStateProto(
    state: api_hunt_pb2.ApiHunt.State,
) -> hunts_pb2.Hunt.HuntState:
  """Converts api_hunt_pb2.ApiHunt.State to hunts_pb2.Hunt.HuntState."""
  if state == api_hunt_pb2.ApiHunt.State.PAUSED:
    return hunts_pb2.Hunt.HuntState.PAUSED
  elif state == api_hunt_pb2.ApiHunt.State.STARTED:
    return hunts_pb2.Hunt.HuntState.STARTED
  elif state == api_hunt_pb2.ApiHunt.State.STOPPED:
    return hunts_pb2.Hunt.HuntState.STOPPED
  elif state == api_hunt_pb2.ApiHunt.State.COMPLETED:
    return hunts_pb2.Hunt.HuntState.COMPLETED
  else:
    return hunts_pb2.Hunt.HuntState.UNKNOWN


def _HuntStateToApiHuntState(
    state: hunts_pb2.Hunt.HuntState,
) -> api_hunt_pb2.ApiHunt.State:
  """Converts hunts_pb2.Hunt.HuntState to ApiHunt.State."""
  if state == hunts_pb2.Hunt.HuntState.PAUSED:
    return api_hunt_pb2.ApiHunt.State.PAUSED
  elif state == hunts_pb2.Hunt.HuntState.STARTED:
    return api_hunt_pb2.ApiHunt.State.STARTED
  elif state == hunts_pb2.Hunt.HuntState.STOPPED:
    return api_hunt_pb2.ApiHunt.State.STOPPED
  elif state == hunts_pb2.Hunt.HuntState.COMPLETED:
    return api_hunt_pb2.ApiHunt.State.COMPLETED

  raise ValueError(f"Unknown hunt state: {state}")


def _HuntStateReasonToApiHuntStateReason(
    reason: hunts_pb2.Hunt.HuntStateReason,
) -> api_hunt_pb2.ApiHunt.StateReason:
  """Converts a hunts_pb2.Hunt.HuntStateReason to an api_hunt_pb2.ApiHunt.StateReason."""
  if reason == hunts_pb2.Hunt.HuntStateReason.UNKNOWN:
    return api_hunt_pb2.ApiHunt.StateReason.UNKNOWN
  elif reason == hunts_pb2.Hunt.HuntStateReason.DEADLINE_REACHED:
    return api_hunt_pb2.ApiHunt.StateReason.DEADLINE_REACHED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_CLIENTS_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.TOTAL_CLIENTS_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_CRASHES_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.TOTAL_CRASHES_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TOTAL_NETWORK_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.TOTAL_NETWORK_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_RESULTS_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.AVG_RESULTS_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.AVG_NETWORK_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.AVG_CPU_EXCEEDED:
    return api_hunt_pb2.ApiHunt.StateReason.AVG_CPU_EXCEEDED
  elif reason == hunts_pb2.Hunt.HuntStateReason.TRIGGERED_BY_USER:
    return api_hunt_pb2.ApiHunt.StateReason.TRIGGERED_BY_USER

  raise ValueError(f"Unknown hunt state reason: {reason}")


class ApiListHuntsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of available hunts."""

  proto_args_type = api_hunt_pb2.ApiListHuntsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntsResult

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
      args: api_hunt_pb2.ApiListHuntsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntsResult:
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
    if args.HasField("with_state"):
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
    return api_hunt_pb2.ApiListHuntsResult(items=items)


class ApiVerifyHuntAccessHandler(api_call_handler_base.ApiCallHandler):
  """Dummy handler that renders empty message."""

  proto_args_type = api_hunt_pb2.ApiVerifyHuntAccessArgs
  proto_result_type = api_hunt_pb2.ApiVerifyHuntAccessResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiVerifyHuntAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiVerifyHuntAccessResult:
    return api_hunt_pb2.ApiVerifyHuntAccessResult()


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  proto_args_type = api_hunt_pb2.ApiGetHuntArgs
  proto_result_type = api_hunt_pb2.ApiHunt

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiHunt:
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


class ApiCountHuntResultsByTypeHandler(api_call_handler_base.ApiCallHandler):
  """Counts all hunt results by type."""

  proto_args_type = api_hunt_pb2.ApiCountHuntResultsByTypeArgs
  proto_result_type = api_hunt_pb2.ApiCountHuntResultsByTypeResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiCountHuntResultsByTypeArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiCountHuntResultsByTypeResult:
    counts = data_store.REL_DB.CountHuntResultsByType(str(args.hunt_id))
    return api_hunt_pb2.ApiCountHuntResultsByTypeResult(
        items=[
            api_hunt_pb2.ApiTypeCount(type=type, count=count)
            for (type, count) in counts.items()
        ]
    )


class ApiListHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt results."""

  proto_args_type = api_hunt_pb2.ApiListHuntResultsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntResultsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntResultsResult:
    results = data_store.REL_DB.ReadHuntResults(
        args.hunt_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
        with_type=args.with_type or None,
    )

    total_count = data_store.REL_DB.CountHuntResults(
        args.hunt_id, with_type=args.with_type or None
    )

    return api_hunt_pb2.ApiListHuntResultsResult(
        items=[InitApiHuntResultFromFlowResult(r) for r in results],
        total_count=total_count,
    )


class ApiListHuntCrashesHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of client crashes for the given hunt."""

  proto_args_type = api_hunt_pb2.ApiListHuntCrashesArgs
  proto_result_type = api_hunt_pb2.ApiListHuntCrashesResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntCrashesResult:
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
    return api_hunt_pb2.ApiListHuntCrashesResult(
        items=crash_infos, total_count=total_count
    )


class ApiGetHuntResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders GRR export tool command line that exports hunt results."""

  proto_args_type = api_hunt_pb2.ApiGetHuntResultsExportCommandArgs
  proto_result_type = api_hunt_pb2.ApiGetHuntResultsExportCommandResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetHuntResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiGetHuntResultsExportCommandResult:
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

    return api_hunt_pb2.ApiGetHuntResultsExportCommandResult(
        command=export_command_str
    )


class ApiListHuntOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's output plugins states."""

  proto_args_type = api_hunt_pb2.ApiListHuntOutputPluginsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntOutputPluginsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntOutputPluginsResult:

    try:
      output_plugin_states = data_store.REL_DB.ReadHuntOutputPluginsStates(
          args.hunt_id
      )
    except db.UnknownHuntError as ex:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % str(args.hunt_id)
      ) from ex

    result = []
    used_names = collections.Counter()
    for output_plugin_state in output_plugin_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor

      name = plugin_descriptor.plugin_name
      plugin_id = f"{name}_{used_names[name]}"
      used_names[name] += 1

      api_plugin = output_plugin_pb2.ApiOutputPlugin()
      api_plugin.id = plugin_id
      api_plugin.plugin_descriptor.CopyFrom(plugin_descriptor)
      api_plugin.state.Pack(output_plugin_state.plugin_state)

      result.append(api_plugin)

    return api_hunt_pb2.ApiListHuntOutputPluginsResult(
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
          api_hunt_pb2.ApiListHuntOutputPluginLogsArgs,
          api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
      ],
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> Union[
      api_hunt_pb2.ApiListHuntOutputPluginLogsResult,
      api_hunt_pb2.ApiListHuntOutputPluginErrorsResult,
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


class ApiListHuntOutputPluginLogsHandler(
    ApiListHuntOutputPluginLogsHandlerBase
):
  """Renders hunt's output plugin's log."""

  proto_args_type = api_hunt_pb2.ApiListHuntOutputPluginLogsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntOutputPluginLogsResult

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG

  collection_type = "logs"
  collection_counter = "success_count"


class ApiListHuntOutputPluginErrorsHandler(
    ApiListHuntOutputPluginLogsHandlerBase
):
  """Renders hunt's output plugin's errors."""

  proto_args_type = api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntOutputPluginErrorsResult

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR

  collection_type = "errors"
  collection_counter = "error_count"


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of log elements for the given hunt."""

  proto_args_type = api_hunt_pb2.ApiListHuntLogsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntLogsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntLogsResult:
    results = data_store.REL_DB.ReadHuntLogEntries(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
    )

    total_count = data_store.REL_DB.CountHuntLogEntries(str(args.hunt_id))

    return api_hunt_pb2.ApiListHuntLogsResult(
        items=[InitApiHuntLogFromFlowLogEntry(r) for r in results],
        total_count=total_count,
    )


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of errors for the given hunt."""

  proto_args_type = api_hunt_pb2.ApiListHuntErrorsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntErrorsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntErrorsResult:
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

    return api_hunt_pb2.ApiListHuntErrorsResult(
        items=[
            InitApiHuntErrorFromFlowErrorInfo(client_id, info)
            for client_id, info in errors.items()
        ],
        total_count=total_count,
    )


class ApiGetHuntClientCompletionStatsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Calculates hunt's client completion stats."""

  proto_args_type = api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs
  proto_result_type = api_hunt_pb2.ApiGetHuntClientCompletionStatsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiGetHuntClientCompletionStatsResult:

    states_and_timestamps = data_store.REL_DB.ReadHuntFlowsStatesAndTimestamps(
        str(args.hunt_id)
    )
    num_buckets = max(100, args.size)
    flow_creation_times, flow_completion_times = [], []

    for stat in states_and_timestamps:
      flow_creation_times.append(stat.create_time.AsSecondsSinceEpoch())
      if stat.flow_state != flows_pb2.Flow.FlowState.RUNNING:
        flow_completion_times.append(
            stat.last_update_time.AsSecondsSinceEpoch()
        )

    if not flow_creation_times:
      return api_hunt_pb2.ApiGetHuntClientCompletionStatsResult()

    min_timestamp = min(flow_creation_times)
    max_timestamp = max(flow_creation_times + flow_completion_times)

    started_histogram = Histogram(
        min_timestamp, max_timestamp, num_buckets, values=flow_creation_times
    )

    completed_histogram = Histogram(
        min_timestamp, max_timestamp, num_buckets, values=flow_completion_times
    )

    return InitApiGetHuntClientCompletionStatsResultFromHistograms(
        started_histogram, completed_histogram
    )


class ApiGetHuntFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  proto_args_type = api_hunt_pb2.ApiGetHuntFilesArchiveArgs

  def _WrapContentGenerator(
      self,
      generator: archive_generator.CollectionArchiveGenerator,
      collection: Iterable[flows_pb2.FlowResult],
      args: api_hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: api_call_context.ApiCallContext,
  ) -> Iterator[bytes]:
    try:

      for item in generator.Generate(collection):
        yield item

      notification.Notify(
          context.username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
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
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for hunt %s: %s" % (args.hunt_id, e),
          None,
      )

      raise

  def _LoadData(
      self,
      hunt_id: str,
  ) -> tuple[Iterable[flows_pb2.FlowResult], str]:
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
      args: api_hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    assert context is not None
    collection, description = self._LoadData(args.hunt_id)
    target_file_prefix = "hunt_" + str(args.hunt_id).replace(":", "_")

    if (
        args.archive_format
        == api_hunt_pb2.ApiGetHuntFilesArchiveArgs.ArchiveFormat.ZIP
    ):
      archive_format = archive_generator.ArchiveFormat.ZIP
      file_extension = ".zip"
    elif (
        args.archive_format
        == api_hunt_pb2.ApiGetHuntFilesArchiveArgs.ArchiveFormat.TAR_GZ
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


class ApiGetHuntFileHandler(api_call_handler_base.ApiCallHandler):
  """Downloads a file referenced in the hunt results."""

  proto_args_type = api_hunt_pb2.ApiGetHuntFileArgs

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
      args: api_hunt_pb2.ApiGetHuntFileArgs,
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


class ApiGetHuntStatsHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt stats request."""

  proto_args_type = api_hunt_pb2.ApiGetHuntStatsArgs
  proto_result_type = api_hunt_pb2.ApiGetHuntStatsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetHuntStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiGetHuntStatsResult:
    del context  # Unused.
    stats = data_store.REL_DB.ReadHuntClientResourcesStats(str(args.hunt_id))
    return api_hunt_pb2.ApiGetHuntStatsResult(stats=stats)


class ApiListHuntClientsHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt clients."""

  proto_args_type = api_hunt_pb2.ApiListHuntClientsArgs
  proto_result_type = api_hunt_pb2.ApiListHuntClientsResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiListHuntClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiListHuntClientsResult:

    filter_condition = db.HuntFlowsCondition.UNSET
    status = args.client_status
    if status == api_hunt_pb2.ApiListHuntClientsArgs.ClientStatus.OUTSTANDING:
      filter_condition = db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY
    elif status == api_hunt_pb2.ApiListHuntClientsArgs.ClientStatus.COMPLETED:
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
        api_hunt_pb2.ApiHuntClient(client_id=hf.client_id, flow_id=hf.flow_id)
        for hf in hunt_flows
    ]

    return api_hunt_pb2.ApiListHuntClientsResult(
        items=results, total_count=total_count
    )


class ApiGetHuntContextHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt contexts."""

  proto_args_type = api_hunt_pb2.ApiGetHuntContextArgs
  proto_result_type = api_hunt_pb2.ApiGetHuntContextResult

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetHuntContextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiGetHuntContextResult:
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
    return api_hunt_pb2.ApiGetHuntContextResult(
        context=context, state=api_utils_pb2.ApiDataObject()
    )


class HuntPresubmitError(Error):
  """Raised when there is a hunt presubmit error."""


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  proto_args_type = api_hunt_pb2.ApiCreateHuntArgs
  proto_result_type = api_hunt_pb2.ApiHunt

  def _HuntPresubmitCheck(
      self,
      client_rule_set: jobs_pb2.ForemanClientRuleSet,
      expected_labels: Sequence[str],
  ) -> bool:
    """Very simple presubmit check for exclude labels rule.

    Requires that the rule set has `MATCH_ALL` mode and it has the
    `exclude_labels` list as a LABEL rule within the set.

    This could be extended to be a more generic/complex check, but for now this
    simple version should be enough for our needs.

    Args:
      client_rule_set: The rule set to check.
      expected_labels: The labels that should be excluded.

    Returns:
      True if the presubmit check passes, False otherwise.
    """
    if (
        client_rule_set.match_mode
        != jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL
    ):
      return False

    for rule in client_rule_set.rules:
      if rule.rule_type != jobs_pb2.ForemanClientRule.Type.LABEL:
        continue
      if not rule.label:
        continue
      if (
          rule.label.match_mode
          != jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY
      ):
        continue
      if len(rule.label.label_names) < len(expected_labels):
        continue

      found = set(expected_labels).issubset(set(rule.label.label_names))
      if found:
        return True

    return False

  def Handle(
      self,
      args: api_hunt_pb2.ApiCreateHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiHunt:
    assert context is not None

    flow_cls = registry.FlowRegistry.FlowClassByName(args.flow_name)
    if flow_cls.block_hunt_creation:
      raise ValueError(f"Flow '{args.flow_name}' cannot run as hunt")

    hunt_obj = models_hunts.CreateHuntFromHuntRunnerArgs(args.hunt_runner_args)

    hunt_obj.num_clients_at_start_time = 0

    # We don't support `VARIABLE` hunt creation anymore.
    hunt_obj.args.hunt_type = hunts_pb2.HuntArguments.HuntType.STANDARD
    hunt_obj.args.standard.flow_name = args.flow_name
    if args.HasField("flow_args"):
      hunt_obj.args.standard.flow_args.CopyFrom(args.flow_args)
    hunt_obj.creator = context.username

    hunt_cfg = config.CONFIG["AdminUI.hunt_config"]
    skip_tag = ""
    if hunt_cfg and hunt_cfg.presubmit_check_with_skip_tag:
      skip_tag = hunt_cfg.presubmit_check_with_skip_tag
    if skip_tag not in args.hunt_runner_args.description:
      passes = self._HuntPresubmitCheck(
          args.hunt_runner_args.client_rule_set, hunt_cfg.default_exclude_labels
      )
      if not passes:
        message = hunt_cfg.presubmit_warning_message + (
            "\nHunt creation failed because the presubmit check failed. You"
            " MUST exclude the following labels from your fleet collection:"
            f" {hunt_cfg.default_exclude_labels} or add a"
            f" '{skip_tag}=<reason>' tag to the description."
        )
        raise HuntPresubmitError(message)

    # At this point, either the presubmit is off, the skip tag is set,
    # or the presubmit passed, so we can set the client_rule_set.
    if args.hunt_runner_args.HasField("client_rule_set"):
      hunt_obj.client_rule_set.CopyFrom(args.hunt_runner_args.client_rule_set)

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

    # Effectively writes the hunt to the DB.
    hunt.CreateHunt(hunt_obj)

    return InitApiHuntFromHuntObject(hunt_obj, with_full_summary=True)


class ApiModifyHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt modifys (this includes starting/stopping the hunt)."""

  proto_args_type = api_hunt_pb2.ApiModifyHuntArgs
  proto_result_type = api_hunt_pb2.ApiHunt

  def Handle(
      self,
      args: api_hunt_pb2.ApiModifyHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt_pb2.ApiHunt:
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
      if args.state == api_hunt_pb2.ApiHunt.State.STARTED:
        if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
          raise HuntNotStartableError(
              "Hunt can only be started from PAUSED state."
          )
        hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
        hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
      elif args.state == api_hunt_pb2.ApiHunt.State.STOPPED:
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


class ApiDeleteHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt deletions."""

  proto_args_type = api_hunt_pb2.ApiDeleteHuntArgs

  def Handle(
      self,
      args: api_hunt_pb2.ApiDeleteHuntArgs,
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


class ApiGetExportedHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given hunt with an instant output plugin."""

  proto_args_type = api_hunt_pb2.ApiGetExportedHuntResultsArgs

  _RESULTS_PAGE_SIZE = 1000

  def Handle(
      self,
      args: api_hunt_pb2.ApiGetExportedHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    try:
      plugin_cls = instant_output_plugin_registry.GetPluginClassByNameProto(
          args.plugin_name
      )
    except KeyError as e:
      raise InstantOutputPluginNotFoundError(
          f"Plugin {args.plugin_name} was not found."
      ) from e

    hunt_id = args.hunt_id
    hunt_urn = rdfvalue.RDFURN("hunts").Add(hunt_id)
    plugin = plugin_cls(source_urn=hunt_urn)
    type_url_counts = data_store.REL_DB.CountHuntResultsByProtoTypeUrl(hunt_id)

    def FetchHuntResultsByTypeUrl(
        type_url: str,
    ) -> Iterator[flows_pb2.FlowResult]:
      """Fetches all hunt results of a given type."""
      offset = 0
      while True:
        results = data_store.REL_DB.ReadHuntResults(
            hunt_id,
            offset=offset,
            count=self._RESULTS_PAGE_SIZE,
            with_proto_type_url=type_url,
        )

        if not results:
          break

        yield from results

        offset += self._RESULTS_PAGE_SIZE

    content_generator = instant_output_plugin.GetExportedFlowResults(
        plugin, list(type_url_counts.keys()), FetchHuntResultsByTypeUrl
    )

    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator
    )
