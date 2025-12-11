#!/usr/bin/env python
"""Mixin class to be used in tests for DB implementations."""

from collections.abc import Callable, Iterable
import itertools
import random
import string
from typing import Any, Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class QueryTestHelpersMixin(object):
  """Mixin containing helper methods for list/query methods tests."""

  # Pytype does not work well with mixins.
  # pytype: disable=attribute-error

  def DoOffsetAndCountTest(
      self,
      fetch_all_fn: Callable[[], Iterable[Any]],
      fetch_range_fn: Callable[[int, int], Iterable[Any]],
      error_desc: Optional[str] = None,
  ):
    """Tests a DB API method with different offset/count combinations.

    This helper method works by first fetching all available objects with
    fetch_all_fn and then fetching all possible ranges using fetch_fn. The test
    passes if subranges returned by fetch_fn match subranges of values in
    the list returned by fetch_all_fn.

    Args:
      fetch_all_fn: Function without arguments that fetches all available
        objects using the API method that's being tested.
      fetch_range_fn: Function that calls an API method that's being tested
        passing 2 positional arguments: offset and count. It should return a
        list of objects.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    all_objects = list(fetch_all_fn())
    self.assertNotEmpty(
        all_objects, "Fetched objects can't be empty (%s)." % error_desc
    )

    for i in range(len(all_objects)):
      for l in range(1, len(all_objects) + 1):
        results = list(fetch_range_fn(i, l))
        expected = list(all_objects[i : i + l])

        self.assertListEqual(
            results,
            expected,
            "Results differ from expected (offset %d, count %d%s): %s vs %s"
            % (
                i,
                l,
                (", " + error_desc) if error_desc else "",
                results,
                expected,
            ),
        )

  def DoFilterCombinationsTest(
      self,
      fetch_fn: Callable[..., Iterable[Any]],
      conditions: dict[str, Any],
      error_desc: Optional[str] = None,
  ):
    """Tests a DB API method with different keyword arguments combinations.

    This test method works by fetching sets of objects for each individual
    condition and then checking that combinations of conditions produce
    expected sets of objects.

    Args:
      fetch_fn: Function accepting keyword "query filter" arguments and
        returning a list of fetched objects. When called without arguments,
        fetch_fn is expected to return all available objects.
      conditions: A dictionary of key -> value, where key is a string
        identifying a keyword argument to be passed to fetch_fn and value is a
        value to be passed. All possible permutations of conditions will be
        tried on fetch_fn.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    perms = list(
        itertools.chain.from_iterable([
            itertools.combinations(sorted(conditions.keys()), i)
            for i in range(1, len(conditions) + 1)
        ])
    )
    self.assertNotEmpty(perms)

    all_objects = fetch_fn()
    expected_objects = {}
    for k, v in conditions.items():
      expected_objects[k] = fetch_fn(**{k: v})

    for condition_perm in perms:
      expected = all_objects
      kw_args = {}
      for k in condition_perm:
        expected = [e for e in expected if e in expected_objects[k]]
        kw_args[k] = conditions[k]

      got = fetch_fn(**kw_args)

      # Make sure that the order of keys->values is stable in the error message.
      kw_args_str = ", ".join(
          "%r: %r" % (k, kw_args[k]) for k in sorted(kw_args)
      )
      self.assertListEqual(
          got,
          expected,
          "Results differ from expected ({%s}%s): %s vs %s"
          % (
              kw_args_str,
              (", " + error_desc) if error_desc else "",
              got,
              expected,
          ),
      )

  def DoFilterCombinationsAndOffsetCountTest(
      self,
      fetch_fn: Callable[..., Iterable[Any]],
      conditions: dict[str, Any],
      error_desc: Optional[str] = None,
  ):
    """Tests a DB API methods with combinations of offset/count args and kwargs.

    This test methods works in 2 steps:
    1. It tests that different conditions combinations work fine when offset
    and count are 0 and abstract_db.MAX_COUNT respectively.
    2. For every condition combination it tests all possible offset and count
    combinations to make sure correct subsets of results are returned.

    Args:
      fetch_fn: Function accepting positional offset and count arguments and
        keyword "query filter" arguments and returning a list of fetched
        objects.
      conditions: A dictionary of key -> value, where key is a string
        identifying a keyword argument to be passed to fetch_fn and value is a
        value to be passed. All possible permutations of conditions will be
        tried on fetch_fn.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    self.DoFilterCombinationsTest(
        lambda **kw_args: fetch_fn(0, abstract_db.MAX_COUNT, **kw_args),
        conditions,
        error_desc=error_desc,
    )

    perms = list(
        itertools.chain.from_iterable([
            itertools.combinations(sorted(conditions.keys()), i)
            for i in range(1, len(conditions) + 1)
        ])
    )
    self.assertNotEmpty(perms)

    for condition_perm in perms:
      kw_args = {}
      for k in condition_perm:
        kw_args[k] = conditions[k]

      # Make sure that the order of keys->values is stable in the error message.
      kw_args_str = ", ".join(
          "%r: %r" % (k, kw_args[k]) for k in sorted(kw_args)
      )
      self.DoOffsetAndCountTest(
          lambda: fetch_fn(0, abstract_db.MAX_COUNT, **kw_args),  # pylint: disable=cell-var-from-loop
          lambda offset, count: fetch_fn(offset, count, **kw_args),  # pylint: disable=cell-var-from-loop
          error_desc=f"{{{kw_args_str}}}, {error_desc}" if error_desc else "",
      )

  # pytype: enable=attribute-error


def InitializeClient(
    db: abstract_db.Database,
    client_id: Optional[str] = None,
) -> str:
  """Initializes a test client.

  Args:
    db: A database object.
    client_id: A specific client id to use for initialized client. If none is
      provided a randomly generated one is used.

  Returns:
    A client id for initialized client.
  """
  if client_id is None:
    client_id = "C."
    for _ in range(16):
      client_id += random.choice("0123456789abcdef")

  db.WriteClientMetadata(client_id)
  return client_id


def InitializeRRGClient(
    db: abstract_db.Database,
    client_id: Optional[str] = None,
    os_type: Optional["rrg_os_pb2.Type"] = None,
) -> str:
  """Initialize a test client that supports RRG.

  Args:
    db: A database object.
    client_id: A specific client id to use for initialized client. If none is
      provided a randomly generated one is used.
    os_type: Operating system type of the initialized client. If none is
      provided, it is picked randomly out of the supported systems.

  Returns:
    A client id for the initialized client.
  """
  client_id = InitializeClient(db, client_id)

  startup = rrg_startup_pb2.Startup()
  startup.metadata.version.major = 1
  startup.metadata.version.minor = 2
  startup.metadata.version.patch = 3

  if os_type is not None:
    startup.os_type = os_type
  else:
    startup.os_type = random.choice([
        rrg_os_pb2.LINUX,
        rrg_os_pb2.MACOS,
        rrg_os_pb2.WINDOWS,
    ])

  db.WriteClientRRGStartup(client_id, startup)

  return client_id


def InitializeUser(
    db: abstract_db.Database,
    username: Optional[str] = None,
) -> str:
  """Initializes a test user.

  Args:
    db: A database object.
    username: A specific username to use for the initialized user. If none is
      provided a randomly generated one is used.

  Returns:
    A username of the initialized user.
  """
  if username is None:
    username = "".join(random.choice(string.ascii_lowercase) for _ in range(16))

  db.WriteGRRUser(username)
  return username


def InitializeFlow(
    db: abstract_db.Database,
    client_id: str,
    flow_id: Optional[str] = None,
    flow_state: Optional[rdf_structs.EnumNamedValue] = None,
    parent_flow_id: Optional[str] = None,
    parent_hunt_id: Optional[str] = None,
    next_request_to_process: Optional[int] = None,
    cpu_time_used: Optional[float] = None,
    network_bytes_sent: Optional[int] = None,
    creator: Optional[str] = None,
) -> str:
  """Initializes a test flow.

  Args:
    db: A database object.
    client_id: A client id of the client to run the flow on.
    flow_id: A specific flow id to use for initialized flow. If none is provided
      a randomly generated one is used.
    flow_state: A flow state (optional).
    parent_flow_id: Identifier of the parent flow (optional).
    parent_hunt_id: Identifier of the parent hunt (optional).
    next_request_to_process: The next request to process (optional).
    cpu_time_used: The used CPU time (optional).
    network_bytes_sent: The number of bytes sent (optional).
    creator: The creator of the flow (optional).

  Returns:
    A flow id of the initialized flow.
  """
  if flow_id is None:
    random_digit = lambda: random.choice(string.hexdigits).upper()
    flow_id = "".join(random_digit() for _ in range(16))

  flow_obj = rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id)

  if flow_state is not None:
    flow_obj.flow_state = flow_state

  if parent_flow_id is not None:
    flow_obj.parent_flow_id = parent_flow_id

  if parent_hunt_id is not None:
    flow_obj.parent_hunt_id = parent_hunt_id

  if cpu_time_used is not None:
    flow_obj.cpu_time_used = cpu_time_used

  if network_bytes_sent is not None:
    flow_obj.network_bytes_sent = network_bytes_sent

  if next_request_to_process is not None:
    flow_obj.next_request_to_process = next_request_to_process

  if creator is not None:
    flow_obj.creator = creator

  db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj))

  return flow_id


def InitializeHunt(
    db: abstract_db.Database,
    hunt_id: Optional[str] = None,
    creator: Optional[str] = None,
    description: Optional[str] = None,
    client_rate: Optional[float] = None,
) -> str:
  """Initializes a test user.

  Args:
    db: A database object.
    hunt_id: A specific hunt id to use for initialized hunt. If none is provided
      a randomly generated one is used.
    creator: A username of the hunt creator. If none is provided a randomly
      generated one is used (and initialized).
    description: A hunt description.
    client_rate: The client rate

  Returns:
    A hunt id of the initialized hunt.
  """
  if hunt_id is None:
    random_digit = lambda: random.choice(string.hexdigits).upper()
    hunt_id = "".join(random_digit() for _ in range(8))
  if creator is None:
    creator = InitializeUser(db)

  hunt_obj = hunts_pb2.Hunt(
      hunt_id=hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
      creator=creator,
  )
  if description is not None:
    hunt_obj.description = description
  if client_rate is not None:
    hunt_obj.client_rate = client_rate
  db.WriteHuntObject(hunt_obj)

  return hunt_id


def InitializeCronJob(
    db: abstract_db.Database,
    cron_job_id: Optional[str] = None,
) -> str:
  """Initializes a test cron job.

  Args:
    db: A database object.
    cron_job_id: A specific job id to use for initialized job. If none is
      provided a randomly generated one is used.

  Returns:
    A cron job id of the initialized cron job.
  """
  if cron_job_id is None:
    random_char = lambda: random.choice(string.ascii_uppercase)
    cron_job_id = "".join(random_char() for _ in range(8))

  job = flows_pb2.CronJob(
      cron_job_id=cron_job_id,
      created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
  )
  db.WriteCronJob(job)

  return cron_job_id
