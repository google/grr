#!/usr/bin/env python
"""Module with GRRWorker/GRREnroller implementation."""


import pdb
import time
import traceback


import logging

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import master
from grr.lib import queue_manager as queue_manager_lib
from grr.lib import rdfvalue
from grr.lib import registry
# pylint: disable=unused-import
from grr.lib import server_stubs
# pylint: enable=unused-import
from grr.lib import stats
from grr.lib import threadpool
from grr.lib import utils


DEFAULT_WORKER_QUEUE = rdfvalue.RDFURN("W")
DEFAULT_ENROLLER_QUEUE = rdfvalue.RDFURN("CA")


class GRRWorker(object):
  """A GRR worker."""

  # time to wait before polling when no jobs are currently in the
  # task scheduler (sec)
  POLLING_INTERVAL = 2
  SHORT_POLLING_INTERVAL = 0.3
  SHORT_POLL_TIME = 30

  # A class global threadpool to be used for all workers.
  thread_pool = None

  # This is a timed cache of locked flows. If this worker encounters a lock
  # failure on a flow, it will not attempt to grab this flow until the timeout.
  queued_flows = None

  def __init__(self, queue=None, threadpool_prefix="grr_threadpool",
               threadpool_size=None, token=None):
    """Constructor.

    Args:
      queue: The queue we use to fetch new messages from.
      threadpool_prefix: A name for the thread pool used by this worker.
      threadpool_size: The number of workers to start in this thread pool.
      token: The token to use for the worker.

    Raises:
      RuntimeError: If the token is not provided.
    """
    self.queue = queue
    self.queued_flows = utils.TimeBasedCache(max_size=10, max_age=60)

    if token is None:
      raise RuntimeError("A valid ACLToken is required.")

    # Make the thread pool a global so it can be reused for all workers.
    if GRRWorker.thread_pool is None:
      if threadpool_size is None:
        threadpool_size = config_lib.CONFIG["Threadpool.size"]

      GRRWorker.thread_pool = threadpool.ThreadPool.Factory(
          threadpool_prefix, min_threads=2, max_threads=threadpool_size)

      GRRWorker.thread_pool.Start()

    self.token = token
    self.last_active = 0

    # Well known flows are just instantiated.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)
    self.lease_time = config_lib.CONFIG["Worker.flow_lease_time"]

  def Run(self):
    """Event loop."""
    try:
      while 1:
        if master.MASTER_WATCHER.IsMaster():
          processed = self.RunOnce()
        else:
          processed = 0

        if processed == 0:

          if time.time() - self.last_active > self.SHORT_POLL_TIME:
            interval = self.POLLING_INTERVAL
          else:
            interval = self.SHORT_POLLING_INTERVAL

          time.sleep(interval)
        else:
          self.last_active = time.time()

    except KeyboardInterrupt:
      logging.info("Caught interrupt, exiting.")
      self.thread_pool.Join()

  def RunOnce(self):
    """Processes one set of messages from Task Scheduler.

    The worker processes new jobs from the task master. For each job
    we retrieve the session from the Task Scheduler.

    Returns:
        Total number of messages processed by this call.
    """
    now = time.time()

    queue_manager = queue_manager_lib.QueueManager(token=self.token)
    # Freezeing the timestamp used by queue manager to query/delete
    # notifications to avoid possible race conditions.
    queue_manager.FreezeTimestamp()

    notifications_by_priority = queue_manager.GetNotificationsByPriority(
        self.queue)
    time_to_fetch_messages = time.time() - now

    # Process stuck flows first
    stuck_flows = notifications_by_priority.pop(
        queue_manager.STUCK_PRIORITY, [])

    if stuck_flows:
      self.ProcessStuckFlows(stuck_flows, queue_manager)

    notifications_available = []
    for priority in sorted(notifications_by_priority, reverse=True):
      for notification in notifications_by_priority[priority]:
        # Filter out session ids we already tried to lock but failed.
        if notification.session_id not in self.queued_flows:
          notifications_available.append(notification)

    try:
      # If we spent too much time processing what we have so far, the
      # active_sessions list might not be current. We therefore break here so
      # we can re-fetch a more up to date version of the list, and try again
      # later. The risk with running with an old active_sessions list is that
      # another worker could have already processed this message, and when we
      # try to process it, there is nothing to do - costing us a lot of
      # processing time. This is a tradeoff between checking the data store
      # for current information and processing out of date information.
      processed = self.ProcessMessages(
          notifications_available, queue_manager,
          min(time_to_fetch_messages * 100, 300))
      return processed

    # We need to keep going no matter what.
    except Exception as e:    # pylint: disable=broad-except
      logging.error("Error processing message %s. %s.", e,
                    traceback.format_exc())

      if flags.FLAGS.debug:
        pdb.post_mortem()

      return 0

  def ProcessStuckFlows(self, stuck_flows, queue_manager):
    stats.STATS.IncrementCounter("grr_flows_stuck", len(stuck_flows))

    for stuck_flow in stuck_flows:
      try:
        flow.GRRFlow.TerminateFlow(
            stuck_flow.session_id, reason="Stuck in the worker",
            status=rdfvalue.GrrStatus.ReturnedStatus.WORKER_STUCK,
            force=True, token=self.token)
      except Exception:   # pylint: disable=broad-except
        logging.exception("Error terminating stuck flow: %s", stuck_flow)
      finally:
        # Remove notifications for this flow. This will also remove the
        # "stuck flow" notification itself.
        queue_manager.DeleteNotification(stuck_flow.session_id)

  def ProcessMessages(self, active_notifications, queue_manager, time_limit=0):
    """Processes all the flows in the messages.

    Precondition: All tasks come from the same queue (self.queue).

    Note that the server actually completes the requests in the
    flow when receiving the messages from the client. We do not really
    look at the messages here at all any more - we just work from the
    completed messages in the flow RDFValue.

    Args:
        active_notifications: The list of notifications.
        queue_manager: QueueManager object used to manage notifications,
                       requests and responses.
        time_limit: If set return as soon as possible after this many seconds.

    Returns:
        The number of processed flows.
    """
    now = time.time()
    processed = 0
    for notification in active_notifications:
      if notification.session_id not in self.queued_flows:
        if time_limit and time.time() - now > time_limit:
          break

        processed += 1
        self.queued_flows.Put(notification.session_id, 1)
        self.thread_pool.AddTask(target=self._ProcessMessages,
                                 args=(notification,
                                       queue_manager.Copy()),
                                 name=self.__class__.__name__)

    return processed

  def _ProcessMessages(self, notification, queue_manager):
    """Does the real work with a single flow."""
    flow_obj = None
    session_id = notification.session_id

    try:
      # Take a lease on the flow:
      if session_id in self.well_known_flows:
        # Well known flows are not necessarily present in the data store so
        # we need to create them instead of opening.
        expected_flow = self.well_known_flows[session_id].__class__.__name__
        flow_obj = aff4.FACTORY.CreateWithLock(
            session_id, expected_flow, lease_time=self.lease_time,
            blocking=False, token=self.token)
      else:
        flow_obj = aff4.FACTORY.OpenWithLock(
            session_id, lease_time=self.lease_time,
            blocking=False, token=self.token)

      with flow_obj:

        now = time.time()
        logging.debug("Got lock on %s", session_id)

        # If we get here, we now own the flow. We can delete the notifications
        # we just retrieved but we need to make sure we don't delete any that
        # came in later.
        queue_manager.DeleteNotification(session_id, end=notification.timestamp)

        # We still need to take a lock on the well known flow in the datastore,
        # but we can run a local instance.
        if session_id in self.well_known_flows:
          stats.STATS.IncrementCounter("well_known_flow_requests",
                                       fields=[str(session_id)])
          flow_obj.ProcessRequests(self.thread_pool)

        else:
          if not isinstance(flow_obj, flow.GRRFlow):
            logging.warn("%s is not a proper flow object (got %s)", session_id,
                         type(flow_obj))
            return

          runner = flow_obj.GetRunner()
          if runner.schedule_kill_notifications:
            # Create a notification for the flow in the future that
            # indicates that this flow is in progess. We'll delete this
            # notification when we're done with processing completed
            # requests. If we're stuck for some reason, the notification
            # will be delivered later and the stuck flow will get
            # terminated.
            stuck_flows_timeout = rdfvalue.Duration(
                config_lib.CONFIG["Worker.stuck_flows_timeout"])
            kill_timestamp = (rdfvalue.RDFDatetime().Now() +
                              stuck_flows_timeout)
            with queue_manager_lib.QueueManager(token=self.token) as manager:
              manager.QueueNotification(session_id=session_id,
                                        in_progress=True,
                                        timestamp=kill_timestamp)

            # kill_timestamp may get updated via flow.HeartBeat() calls, so we
            # have to store it in the runner context.
            runner.context.kill_timestamp = kill_timestamp

          try:
            runner.ProcessCompletedRequests(notification, self.thread_pool)

          # Something went wrong - log it in the flow.
          except Exception as e:  # pylint: disable=broad-except
            runner.context.state = rdfvalue.Flow.State.ERROR
            runner.context.backtrace = traceback.format_exc()

            logging.error("Flow %s: %s", flow_obj, e)
            return

          finally:
            # Delete kill notification as the flow got processed and is not
            # stuck.
            with queue_manager_lib.QueueManager(token=self.token) as manager:
              if runner.schedule_kill_notifications:
                manager.DeleteNotification(
                    session_id, start=runner.context.kill_timestamp,
                    end=runner.context.kill_timestamp)
                runner.context.kill_timestamp = None

              if (runner.process_requests_in_order and
                  notification.last_status and
                  (runner.context.next_processed_request <=
                   notification.last_status)):
                # We are processing requests in order and have received a
                # notification for a specific request but could not process
                # that request. This might be a race condition in the data
                # store so we reschedule the notification in the future.
                delay = config_lib.CONFIG[
                    "Worker.notification_retry_interval"]
                manager.QueueNotification(
                    notification, timestamp=notification.timestamp + delay)

        logging.debug("Done processing %s: %s sec", session_id,
                      time.time() - now)

      # Everything went well -> session can be run again.
      self.queued_flows.ExpireObject(session_id)

    except aff4.LockError:
      # Another worker is dealing with this flow right now, we just skip it.
      return

    except Exception as e:    # pylint: disable=broad-except
      # Something went wrong when processing this session. In order not to spin
      # here, we just remove the notification.
      logging.exception("Error processing session %s: %s", session_id, e)
      queue_manager.DeleteNotification(session_id)


class GRREnroler(GRRWorker):
  """A GRR enroler.

  Subclassed here so that log messages arrive from the right class.
  """


class WorkerInit(registry.InitHook):
  """Registers worker stats variables."""

  pre = ["StatsInit"]

  def RunOnce(self):
    """Exports the vars.."""
    stats.STATS.RegisterCounterMetric("grr_flows_stuck")
