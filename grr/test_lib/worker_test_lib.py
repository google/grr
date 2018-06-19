#!/usr/bin/env python
"""Worker-related test classes."""

import itertools

import logging

from grr.lib import queues as queue_config
from grr.lib.rdfvalues import flows as rdf_flows
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import queue_manager

from grr.server.grr_response_server import worker_lib


class MockThreadPool(object):
  """A mock thread pool which runs all jobs serially."""

  def __init__(self, *_):
    pass

  def AddTask(self, target, args, name="Unnamed task"):
    _ = name
    try:
      target(*args)
      # The real threadpool can not raise from a task. We emulate this here.
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Thread worker raised %s", e)

  def Join(self):
    pass


class MockWorker(worker_lib.GRRWorker):
  """Mock the worker."""

  # Resource accounting off by default, set these arrays to emulate CPU and
  # network usage.
  USER_CPU = [0]
  SYSTEM_CPU = [0]
  NETWORK_BYTES = [0]

  def __init__(self,
               queues=queue_config.WORKER_LIST,
               check_flow_errors=True,
               token=None):
    self.queues = queues
    self.check_flow_errors = check_flow_errors
    self.token = token

    self.pool = MockThreadPool("MockWorker_pool", 25)

    # Collect all the well known flows.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

    # Simple generators to emulate CPU and network usage
    self.cpu_user = itertools.cycle(self.USER_CPU)
    self.cpu_system = itertools.cycle(self.SYSTEM_CPU)
    self.network_bytes = itertools.cycle(self.NETWORK_BYTES)

  def Simulate(self):
    while self.Next():
      pass

    self.pool.Join()

  def Next(self):
    """Very simple emulator of the worker.

    We wake each flow in turn and run it.

    Returns:
      total number of flows still alive.

    Raises:
      RuntimeError: if the flow terminates with an error.
    """
    with queue_manager.QueueManager(token=self.token) as manager:
      run_sessions = []
      for queue in self.queues:
        notifications_available = manager.GetNotificationsForAllShards(queue)
        # Run all the flows until they are finished

        # Only sample one session at the time to force serialization of flows
        # after each state run.
        for notification in notifications_available[:1]:
          session_id = notification.session_id
          manager.DeleteNotification(session_id, end=notification.timestamp)
          run_sessions.append(session_id)

          # Handle well known flows here.
          flow_name = session_id.FlowName()
          if flow_name in self.well_known_flows:
            well_known_flow = self.well_known_flows[flow_name]
            with well_known_flow:
              responses = well_known_flow.FetchAndRemoveRequestsAndResponses(
                  well_known_flow.well_known_session_id)
            well_known_flow.ProcessResponses(responses, self.pool)
            continue

          with aff4.FACTORY.OpenWithLock(
              session_id, token=self.token, blocking=False) as flow_obj:

            # Run it
            runner = flow_obj.GetRunner()
            cpu_used = runner.context.client_resources.cpu_usage
            user_cpu = self.cpu_user.next()
            system_cpu = self.cpu_system.next()
            network_bytes = self.network_bytes.next()
            cpu_used.user_cpu_time += user_cpu
            cpu_used.system_cpu_time += system_cpu
            runner.context.network_bytes_sent += network_bytes
            runner.ProcessCompletedRequests(notification, self.pool)

            if (self.check_flow_errors and
                isinstance(flow_obj, flow.GRRFlow) and
                runner.context.state == rdf_flows.FlowContext.State.ERROR):
              logging.exception("Flow terminated in state %s with an error: %s",
                                runner.context.current_state,
                                runner.context.backtrace)
              raise RuntimeError(runner.context.backtrace)

    return run_sessions
