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
from grr.lib import queue_manager
from grr.lib import rdfvalue
# pylint: disable=unused-import
from grr.lib import server_stubs
# pylint: enable=unused-import
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
    self.manager = queue_manager.QueueManager(token=self.token)

    # Well known flows are just instantiated.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

  def Run(self):
    """Event loop."""
    try:
      while 1:
        processed = self.RunOnce()

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
    sessions_available = self.manager.GetSessionsFromQueue(self.queue)

    time_to_fetch_messages = time.time() - now

    # Filter out session ids we already tried to lock but failed.
    sessions_available = [session for session in sessions_available
                          if session not in self.queued_flows]

    try:
      # If we spent too much time processing what we have so far, the
      # active_sessions list might not be current. We therefore break here so we
      # can re-fetch a more up to date version of the list, and try again
      # later. The risk with running with an old active_sessions list is that
      # another worker could have already processed this message, and when we
      # try to process it, there is nothing to do - costing us a lot of
      # processing time. This is a tradeoff between checking the data store for
      # current information and processing out of date information.
      processed = self.ProcessMessages(
          sessions_available, min(time_to_fetch_messages * 100, 300))
    # We need to keep going no matter what.
    except Exception as e:    # pylint: disable=broad-except
      logging.error("Error processing message %s. %s.", e,
                    traceback.format_exc())

      if flags.FLAGS.debug:
        pdb.post_mortem()

    return processed

  def ProcessMessages(self, active_sessions, time_limit=0):
    """Processes all the flows in the messages.

    Precondition: All tasks come from the same queue (self.queue).

    Note that the server actually completes the requests in the
    flow when receiving the messages from the client. We do not really
    look at the messages here at all any more - we just work from the
    completed messages in the flow RDFValue.

    Args:
        active_sessions: The list of sessions which had messages received.
        time_limit: If set return as soon as possible after this many seconds.

    Returns:
        The number of processed flows.
    """
    now = time.time()
    processed = 0
    for session_id in active_sessions:
      if session_id not in self.queued_flows:
        if time_limit and time.time() - now > time_limit:
          break

        processed += 1
        self.queued_flows.Put(session_id, 1)
        self.thread_pool.AddTask(target=self._ProcessMessages,
                                 args=(rdfvalue.SessionID(session_id),),
                                 name=self.__class__.__name__)

    return processed

  def _ProcessMessages(self, session_id):
    """Does the real work with a single flow."""
    flow_obj = None

    # Take a lease on the flow:
    try:
      with aff4.FACTORY.OpenWithLock(
          session_id, lease_time=config_lib.CONFIG["Worker.flow_lease_time"],
          blocking=False, token=self.token) as flow_obj:

        now = time.time()
        logging.info("Got lock on %s", session_id)

        # If we get here, we now own the flow, so we can remove the notification
        # for it from the worker queue.
        self.manager.DeleteNotification(session_id)

        # We still need to take a lock on the well known flow in the datastore,
        # but we can run a local instance.
        if session_id in self.well_known_flows:
          self.well_known_flows[session_id].ProcessRequests(
              self.thread_pool)

        else:
          if not isinstance(flow_obj, flow.GRRFlow):
            logging.info("%s is not a proper flow object (got %s)", session_id,
                         type(flow_obj))
            return

          with flow_obj.GetRunner() as runner:
            try:
              runner.ProcessCompletedRequests(self.thread_pool)

            # Something went wrong - log it in the flow.
            except Exception as e:  # pylint: disable=broad-except
              runner.context.state = rdfvalue.Flow.State.ERROR
              runner.context.backtrace = traceback.format_exc()

              logging.error("Flow %s: %s", flow_obj, e)
              return

            # NOTE: Flow object must be flushed _before_ the runner is
            # flushed. The flow object must exist in the data store before any
            # messages are queued to go out, otherwise responses might arrive
            # with no associated flow.
            flow_obj.Flush(sync=True)

        logging.info("Done processing %s: %s sec", session_id,
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
      self.manager.DeleteNotification(session_id)


class GRREnroler(GRRWorker):
  """A GRR enroler.

  Subclassed here so that log messages arrive from the right class.
  """
