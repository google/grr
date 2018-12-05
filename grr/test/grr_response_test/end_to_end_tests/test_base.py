#!/usr/bin/env python
"""Base classes and routines used by all end to end tests."""
from __future__ import absolute_import
from __future__ import division

import abc
import io
import logging
import time


from absl.testing import absltest
from future.utils import with_metaclass

from grr_api_client import errors
from grr_response_core.lib import flags

flags.DEFINE_integer("flow_timeout_secs", 650,
                     "How long to wait for flows to finish.")

flags.DEFINE_integer(
    "flow_results_sla_secs", 60,
    "How long to wait for flow results to be available after a flow completes.")


class Error(Exception):
  """Base class for end-to-end tests exceptions."""


def GetClientTestTargets(grr_api=None,
                         client_ids=None,
                         hostnames=None,
                         checkin_duration_threshold=3600):
  """Get client urns for end-to-end tests.

  Args:
    grr_api: GRR API object.
    client_ids: list of client id URN strings or rdf_client.ClientURNs.
    hostnames: list of hostnames to search for.
    checkin_duration_threshold: clients that haven't checked in for this long
                                will be excluded. Value is specified in seconds.
                                Default is 1 hour.
  Returns:
    client_id_set: list of api_client.Client objects corresponding to every
                   client found.
  """

  if client_ids:
    client_ids = set(client_ids)
  else:
    client_ids = set()

  clients = []
  if hostnames:
    hostnames = set(hostnames)
    logging.info("Seaching for clients corresponding to %d hostnames: %s.",
                 len(hostnames), ",".join(hostnames))

    for hostname in hostnames:
      clients_for_host = list(grr_api.SearchClients(query="host:" + hostname))
      clients.extend(clients_for_host)

  for client_id in client_ids:
    client_obj = grr_api.Client(client_id).Get()
    clients.append(client_obj)

  results = []
  for client_obj in clients:
    time_since_last_seen = time.time() - client_obj.data.last_seen_at * 1e-6
    if time_since_last_seen <= checkin_duration_threshold:
      results.append(client_obj)

  logging.info("Filtered out %d inactive clients.", len(clients) - len(results))

  return results


REGISTRY = {}


class EndToEndTestMetaclass(abc.ABCMeta):
  """Metaclass that registers all non-abstract tests in REGISTRY."""

  def __init__(cls, name, bases, env_dict):
    abc.ABCMeta.__init__(cls, name, bases, env_dict)

    if (name.startswith("Abstract") or name.startswith("FakeE2ETest") or
        name == "EndToEndTest"):
      return

    REGISTRY[name] = cls


class WaitForNewFileContextManager(object):
  """A context manager class that waits for a new file."""

  CHECK_TYPE_IS_PRESENT = 0
  CHECK_TYPE_LAST_COLLECTED = 1
  CHECK_TYPE_AGE = 2

  def __init__(self, client, file_path, check_type):
    self.client = client
    self.file_path = file_path
    self.check_type = check_type

  def __enter__(self):
    try:
      self.prev_file = self.client.File(self.file_path).Get()
    except errors.ResourceNotFoundError:
      self.prev_file = None

    return self

  def __exit__(self, t, value, tb):
    start_time = time.time()
    while True:
      try:
        new_file = self.client.File(self.file_path).Get()
      except errors.ResourceNotFoundError:
        new_file = None

      if new_file:
        if (self.check_type == self.__class__.CHECK_TYPE_IS_PRESENT or
            not self.prev_file):
          return

        if (self.check_type == self.__class__.CHECK_TYPE_LAST_COLLECTED and
            new_file.data.last_collected > self.prev_file.data.last_collected):
          return

        if (self.check_type == self.__class__.CHECK_TYPE_AGE and
            new_file.data.age > self.prev_file.data.age):
          return

      if time.time() - start_time > flags.FLAGS.flow_results_sla_secs:
        raise RuntimeError("File couldn't be found after %d seconds of trying."
                           % flags.FLAGS.flow_results_sla_secs)

      time.sleep(EndToEndTest.RETRY_DELAY)


class RunFlowAndWaitError(Error):
  """Error thrown by RunFlowAndWait."""

  def __init__(self, message, flow):
    super(RunFlowAndWaitError, self).__init__(message)
    self.flow = flow


# Zero-argument function that initializes the GRR API and the client to
# run tests against, then returns them. This should be overridden in the test
# runner code.
init_fn = lambda: (None, None)


class EndToEndTest(with_metaclass(EndToEndTestMetaclass, absltest.TestCase)):
  """This is a end-to-end test base class."""

  class Platform(object):
    LINUX = "Linux"
    WINDOWS = "Windows"
    DARWIN = "Darwin"

    ALL = [LINUX, WINDOWS, DARWIN]

  RETRY_DELAY = 1

  platforms = []

  def __init__(self, *args, **kwargs):
    super(EndToEndTest, self).__init__(*args, **kwargs)
    self.grr_api, self.client = init_fn()
    if not self.grr_api:
      raise Exception("GRR API not set.")
    if not self.client:
      raise Exception("Client not set.")

  @property
  def platform(self):
    return self.client.data.os_info.system

  def RunFlowAndWait(self, flow_name, args=None, runner_args=None):
    if runner_args is None:
      runner_args = self.grr_api.types.CreateFlowRunnerArgs()
    runner_args.notify_to_user = False

    flow = self.client.CreateFlow(
        name=flow_name, args=args, runner_args=runner_args)
    logging.info("Started flow %s with id %s.", flow_name, flow.flow_id)

    total_time = 0
    while flow.data.state == flow.data.State.Value("RUNNING"):
      flow = self.client.Flow(flow.flow_id).Get()

      time.sleep(self.RETRY_DELAY)
      total_time += self.RETRY_DELAY
      if total_time >= flags.FLAGS.flow_timeout_secs:
        raise RunFlowAndWaitError(
            "Flow hasn't finished in %d seconds." %
            (flags.FLAGS.flow_timeout_secs,), flow)

    if flow.data.state == flow.data.State.Value("ERROR"):
      raise RunFlowAndWaitError(
          "Flow failed with an error: %s" % flow.data.context.backtrace, flow)
    elif flow.data.state == flow.data.State.Value("CLIENT_CRASHED"):
      raise RunFlowAndWaitError("Flow failed due to a client crash.", flow)

    return flow

  def WaitForFileCollection(self, file_path):
    # TODO(user): we should compare last_collected instead of the age.
    # But last_collected doesn't get updated when the file gets re-collected.
    # Switch to comparing last_collected when the issue is resolved.
    return WaitForNewFileContextManager(
        self.client, file_path, WaitForNewFileContextManager.CHECK_TYPE_AGE)

  def WaitForFileRefresh(self, file_path):
    return WaitForNewFileContextManager(
        self.client, file_path, WaitForNewFileContextManager.CHECK_TYPE_AGE)


class AbstractFileTransferTest(EndToEndTest):
  """An abstract class for file transfer tests."""

  def ReadFromFile(self, path, num_bytes):
    s = io.BytesIO()
    self.client.File(path).GetBlob().WriteToStream(s)
    return s.getvalue()[:num_bytes]

  def TSKPathspecToVFSPath(self, pathspec):
    path = "fs/tsk/"
    while pathspec.path:
      path += pathspec.path
      pathspec = pathspec.nested_path

    return path

  def CheckMacMagic(self, path):
    data = self.ReadFromFile(path, 10)

    magic_values = ["cafebabe", "cefaedfe", "cffaedfe"]
    magic_values = [x.decode("hex") for x in magic_values]
    self.assertIn(
        data[:4],
        magic_values,
        msg="Data %s not one of %s" % (data[:4], magic_values))

  def CheckELFMagic(self, path):
    data = self.ReadFromFile(path, 10)
    self.assertEqual(data[1:4], "ELF")

  def CheckPEMagic(self, path):
    data = self.ReadFromFile(path, 10)
    self.assertEqual(data[:2], "MZ")
