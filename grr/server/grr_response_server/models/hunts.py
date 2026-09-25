#!/usr/bin/env python
"""Hunt related helpers."""

from google.protobuf import message as pb_message
from grr_response_core import config
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2


def IsHuntSuitableForFlowProcessing(hunt_state: int) -> bool:
  return hunt_state in [
      hunts_pb2.Hunt.HuntState.PAUSED,
      hunts_pb2.Hunt.HuntState.STARTED,
  ]


# Hunt CPU stats are aggregated using the following bins.
CPU_STATS_BINS = [
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.75,
    1,
    1.5,
    2,
    2.5,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    15,
    20,
]

# Hunt network stats are aggregated using the following bins.
NETWORK_STATS_BINS = [
    16,
    32,
    64,
    128,
    256,
    512,
    1024,
    2048,
    4096,
    8192,
    16384,
    32768,
    65536,
    131072,
    262144,
    524288,
    1048576,
    2097152,
]

# Number of worst performers to query when fetching hunt stats.
NUM_WORST_PERFORMERS = 10


def RandomHuntId() -> str:
  """Returns a random hunt id encoded as a hex string."""
  return "{:016X}".format(random.Id64())


def CreateDefaultHunt() -> hunts_pb2.Hunt:
  """Creates a new Hunt with default values."""
  hunt_obj = hunts_pb2.Hunt()
  hunt_obj.hunt_id = RandomHuntId()

  # Even if for this method we're not setting any flow arguments,
  # foreman rules rely on this enum being set. So we already set
  # it always by default (variable hunts are no longer supported)
  hunt_obj.args.hunt_type = hunts_pb2.HuntArguments.HuntType.STANDARD

  hunt_obj.hunt_state = hunts_pb2.Hunt.HuntState.PAUSED
  hunt_obj.duration = 2 * 7 * 24 * 60 * 60  # 2 weeks

  # This value is here for backward compatibility reasons. New hunts should use
  # the default value from the config instead.
  hunt_obj.client_rate = 20.5

  hunt_obj.client_limit = 100

  # TODO - We use default values only if the config has been
  # initialized and leave them blank if it has not been. Protobuf defaults
  # depending on the config initialization is a *very* questionable design
  # choice and likely should be revised.
  if config.CONFIG.initialized:
    hunt_obj.client_rate = config.CONFIG["Hunt.default_client_rate"]
    hunt_obj.crash_limit = config.CONFIG["Hunt.default_crash_limit"]
    hunt_obj.avg_results_per_client_limit = config.CONFIG[
        "Hunt.default_avg_results_per_client_limit"
    ]
    hunt_obj.avg_cpu_seconds_per_client_limit = config.CONFIG[
        "Hunt.default_avg_cpu_seconds_per_client_limit"
    ]
    hunt_obj.avg_network_bytes_per_client_limit = config.CONFIG[
        "Hunt.default_avg_network_bytes_per_client_limit"
    ]

  return hunt_obj


def CreateDefaultHuntForFlow(
    flow_name: str, flow_args: pb_message.Message, creator: str
) -> hunts_pb2.Hunt:
  """Creates a new Hunt with default values."""
  hunt_obj = CreateDefaultHunt()

  hunt_obj.args.hunt_type = hunts_pb2.HuntArguments.HuntType.STANDARD
  hunt_obj.args.standard.flow_name = flow_name
  hunt_obj.args.standard.flow_args.Pack(flow_args)
  hunt_obj.creator = creator

  return hunt_obj


def CreateHuntFromHuntRunnerArgs(
    hra: flows_pb2.HuntRunnerArgs,
) -> hunts_pb2.Hunt:
  """Creates a new Hunt from HuntRunnerArgs, sets default values if fields are unset."""
  hunt_obj = CreateDefaultHunt()

  if hra.HasField("expiry_time"):
    hunt_obj.duration = hra.expiry_time
  if hra.HasField("client_rate"):
    hunt_obj.client_rate = hra.client_rate
  if hra.HasField("client_limit"):
    hunt_obj.client_limit = hra.client_limit

  if hra.HasField("crash_limit"):
    hunt_obj.crash_limit = hra.crash_limit
  if hra.HasField("avg_results_per_client_limit"):
    hunt_obj.avg_results_per_client_limit = hra.avg_results_per_client_limit
  if hra.HasField("avg_cpu_seconds_per_client_limit"):
    hunt_obj.avg_cpu_seconds_per_client_limit = (
        hra.avg_cpu_seconds_per_client_limit
    )
  if hra.HasField("avg_network_bytes_per_client_limit"):
    hunt_obj.avg_network_bytes_per_client_limit = (
        hra.avg_network_bytes_per_client_limit
    )

  if hra.HasField("description"):
    hunt_obj.description = hra.description
  if hra.HasField("per_client_cpu_limit"):
    hunt_obj.per_client_cpu_limit = hra.per_client_cpu_limit
  if hra.HasField("per_client_network_limit_bytes"):
    hunt_obj.per_client_network_bytes_limit = hra.per_client_network_limit_bytes
  if hra.HasField("network_bytes_limit"):
    hunt_obj.total_network_bytes_limit = hra.network_bytes_limit

  hunt_obj.output_plugins.extend(hra.output_plugins)

  return hunt_obj


def CreateDefaultHuntRunnerArgs() -> flows_pb2.HuntRunnerArgs:
  """Creates a HuntRunnerArgs proto with default values."""

  hunt_runner_args = flows_pb2.HuntRunnerArgs()
  hunt_runner_args.client_rate = config.CONFIG["Hunt.default_client_rate"]
  hunt_runner_args.crash_limit = config.CONFIG["Hunt.default_crash_limit"]
  hunt_runner_args.avg_results_per_client_limit = config.CONFIG[
      "Hunt.default_avg_results_per_client_limit"
  ]
  hunt_runner_args.avg_cpu_seconds_per_client_limit = config.CONFIG[
      "Hunt.default_avg_cpu_seconds_per_client_limit"
  ]
  hunt_runner_args.avg_network_bytes_per_client_limit = config.CONFIG[
      "Hunt.default_avg_network_bytes_per_client_limit"
  ]

  return hunt_runner_args


def InitHuntMetadataFromHunt(hunt: hunts_pb2.Hunt) -> hunts_pb2.HuntMetadata:
  """Creates a HuntMetadata proto from a Hunt proto."""
  res = hunts_pb2.HuntMetadata(
      hunt_id=hunt.hunt_id,
      create_time=hunt.create_time,
      creator=hunt.creator,
      duration=hunt.duration,
      client_rate=hunt.client_rate,
      client_limit=hunt.client_limit,
      hunt_state=hunt.hunt_state,
      last_update_time=hunt.last_update_time,
  )
  if hunt.description:
    res.description = hunt.description
  if hunt.hunt_state_comment:
    res.hunt_state_comment = hunt.hunt_state_comment
  if hunt.init_start_time:
    res.init_start_time = hunt.init_start_time
  if hunt.last_start_time:
    res.last_start_time = hunt.last_start_time

  return res
