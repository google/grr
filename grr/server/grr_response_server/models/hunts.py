#!/usr/bin/env python
"""Hunt related helpers."""

from typing import Optional

from grr_response_core import config
from grr_response_core.lib import rdfvalue
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


def CreateHunt(
    hunt_id: Optional[str] = None,
    hunt_state: hunts_pb2.Hunt.HuntState = hunts_pb2.Hunt.HuntState.PAUSED,
    duration: Optional[rdfvalue.Duration] = rdfvalue.Duration.From(
        2, rdfvalue.WEEKS
    ),
    client_rate: float = 20.5,
    client_limit: int = 100,
    num_clients_at_start_time: int = 0,
    crash_limit: Optional[int] = None,
    avg_results_per_client_limit: Optional[int] = None,
    avg_cpu_seconds_per_client_limit: Optional[int] = None,
    avg_network_bytes_per_client_limit: Optional[int] = None,
) -> hunts_pb2.Hunt:
  """Creates a new Hunt with default values."""

  if not hunt_id:
    hunt_id = RandomHuntId()

  hunt_obj = hunts_pb2.Hunt(
      hunt_id=hunt_id,
      hunt_state=hunt_state,
      duration=duration,
      client_rate=client_rate,
      client_limit=client_limit,
      num_clients_at_start_time=num_clients_at_start_time,
  )

  # TODO: We use default values only if the config has been
  # initialized and leave them blank if it has not been. Protobuf defaults
  # depending on the config initialization is a *very* questionable design
  # choice and likely should be revised.
  if config.CONFIG.initialized:
    if crash_limit is None:
      hunt_obj.crash_limit = config.CONFIG["Hunt.default_crash_limit"]

    if avg_results_per_client_limit is None:
      hunt_obj.avg_results_per_client_limit = config.CONFIG[
          "Hunt.default_avg_results_per_client_limit"
      ]

    if avg_cpu_seconds_per_client_limit is None:
      hunt_obj.avg_cpu_seconds_per_client_limit = config.CONFIG[
          "Hunt.default_avg_cpu_seconds_per_client_limit"
      ]

    if avg_network_bytes_per_client_limit is None:
      hunt_obj.avg_network_bytes_per_client_limit = config.CONFIG[
          "Hunt.default_avg_network_bytes_per_client_limit"
      ]

  return hunt_obj


def CreateHuntRunnerArgs(
    client_rate: Optional[float] = None,
    crash_limit: Optional[float] = None,
    avg_results_per_client_limit: Optional[float] = None,
    avg_cpu_seconds_per_client_limit: Optional[float] = None,
    avg_network_bytes_per_client_limit: Optional[float] = None,
) -> flows_pb2.HuntRunnerArgs:
  """Creates a HuntRunnerArgs proto with default values."""

  hunt_runner_args = flows_pb2.HuntRunnerArgs()

  if client_rate is None:
    hunt_runner_args.client_rate = config.CONFIG["Hunt.default_client_rate"]

  if crash_limit is None:
    hunt_runner_args.crash_limit = config.CONFIG["Hunt.default_crash_limit"]

  if avg_results_per_client_limit is None:
    hunt_runner_args.avg_results_per_client_limit = config.CONFIG[
        "Hunt.default_avg_results_per_client_limit"
    ]
  if avg_cpu_seconds_per_client_limit is None:
    hunt_runner_args.avg_cpu_seconds_per_client_limit = config.CONFIG[
        "Hunt.default_avg_cpu_seconds_per_client_limit"
    ]
  if avg_network_bytes_per_client_limit is None:
    hunt_runner_args.avg_network_bytes_per_client_limit = config.CONFIG[
        "Hunt.default_avg_network_bytes_per_client_limit"
    ]

  return hunt_runner_args
