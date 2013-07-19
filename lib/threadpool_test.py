#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the ThreadPool class."""



import threading

import mox

import logging
from grr.lib import flags
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import threadpool


class ThreadPoolTest(test_lib.GRRBaseTest):
  """Tests for the ThreadPool class."""
  NUMBER_OF_THREADS = 250
  NUMBER_OF_TASKS = 1500

  def setUp(self):
    super(ThreadPoolTest, self).setUp()
    self.mox = mox.Mox()
    self.base_thread_count = threading.active_count()

    prefix = "pool-%s" % self._testMethodName
    self.test_pool = threadpool.ThreadPool.Factory(
        prefix, self.NUMBER_OF_THREADS)
    self.test_pool.Start()

  def tearDown(self):
    self.test_pool.Stop()
    self.mox.UnsetStubs()
    self.mox.VerifyAll()
    super(ThreadPoolTest, self).tearDown()

  def Count(self, thread_name):
    worker_threads = [thread for thread in threading.enumerate()
                      if thread_name in thread.name]
    return len(worker_threads)

  def testThreadCreation(self):
    """Checks if at least 100 workers can be created.

    The standard size for the thread pool is 500 workers. It could be
    that there are fewer threads generated (for example due to memory
    constraints) but we demand at least 100 workers in the default
    settings here.
    """

    self.assertEqual(
        self.Count("pool-testThreadCreation_worker"), self.NUMBER_OF_THREADS)

  def testStopping(self):
    """Tests if all worker threads terminate if the thread pool is stopped."""

    self.assertEqual(
        self.Count("pool-testStopping_worker"), self.NUMBER_OF_THREADS)
    self.test_pool.Stop()
    self.assertEqual(self.Count("pool-testStopping_worker"), 0)
    self.test_pool.Start()
    self.assertEqual(
        self.Count("pool-testStopping_worker"), self.NUMBER_OF_THREADS)
    self.test_pool.Stop()
    self.assertEqual(self.Count("pool-testStopping_worker"), 0)

    # This test leaves the test pool in stopped state. tearDown will try to
    # Stop() it again but this should work and just log a warning.

  def testRunTasks(self):
    """Test for running jobs on the thread pool.

    This runs 1500 tasks on the ThreadPool and waits for them to
    complete.
    """

    # Tests if calling Join on an empty ThreadPool works.
    self.test_pool.Join()

    self.lock = threading.Lock()

    def Insert(list_obj, element):
      with self.lock:
        list_obj.append(element)

    # We want to schedule more than 500 tasks here so we can see if
    # reusing threads is actually working and more than 1000 to see if
    # we can schedule more tasks than fit into the queue.

    test_list = []
    for i in range(self.NUMBER_OF_TASKS):
      self.test_pool.AddTask(Insert, (test_list, i,))

    self.test_pool.Join()
    test_list.sort()
    self.assertEqual(range(self.NUMBER_OF_TASKS), test_list)

  def testRunRaisingTask(self):
    """Tests the behavior of the pool if a task throws an exception."""

    self.lock = threading.Lock()

    def IRaise(some_obj):
      """This method just raises an exception."""
      with self.lock:
        # This simulates an error by calling a non-existent function.
        some_obj.process()

    self.mox.StubOutWithMock(logging, "exception")
    logging.exception(mox.StrContains("exception in worker thread"),
                      "Raising", mox.IgnoreArg())
    logging.exception(mox.StrContains("exception in worker thread"),
                      "Raising", mox.IgnoreArg())
    self.mox.ReplayAll()

    self.test_pool.AddTask(IRaise, (None,), "Raising")
    self.test_pool.AddTask(IRaise, (None,), "Raising")
    self.test_pool.Join()

    # Make sure that both exceptions have been counted.
    self.assertEqual(
        stats.STATS.GetMetricValue(self.test_pool.name + "_task_exceptions"),
        2)

  def testBlockingTasks(self):
    self.test_pool.Join()
    done_event = threading.Event()
    ready_events = []
    self.lock = threading.Lock()
    res = []

    def Block(ready, done):
      ready.set()
      done.wait()

    def Insert(list_obj, element):
      with self.lock:
        list_obj.append(element)

    # Schedule blocking tasks on all the workers.
    for _ in self.test_pool.workers:
      ready_event = threading.Event()
      ready_events.append(ready_event)
      self.test_pool.AddTask(Block, (ready_event, done_event), "Blocking")

    for ev in ready_events:
      ev.wait()

    try:
      self.assertEqual(stats.STATS.GetMetricValue(self.test_pool.name +
                                                  "_idle_threads"), 0)

      i = 0
      n = 10
      while self.test_pool._queue.qsize() < self.test_pool._queue.maxsize:
        self.test_pool.AddTask(Insert, (res, i), "Insert")
        i += 1

      # Inserting more tasks than the queue can hold should lead to processing
      # of some the earlier tasks.
      for _ in range(n):
        self.test_pool.AddTask(Insert, (res, i), "Insert")
        i += 1

      self.assertEqual(sorted(res), range(n))

      done_event.set()
      self.test_pool.Join()

      # Now the rest of the tasks should have been processed as well.
      self.assertEqual(sorted(res), range(n + self.test_pool._queue.maxsize))

    finally:
      done_event.set()

  def testThreadSpawningProblemsNoWorker(self):
    """Tests behavior when spawning threads fails."""

    self.mox.StubOutWithMock(logging, "error")
    worker = threadpool._WorkerThread
    self.mox.StubOutWithMock(worker, "start")

    worker.start().AndRaise(threading.ThreadError)
    # Could not start worker threads.
    logging.error(mox.StrContains("Could not spawn"))

    self.mox.ReplayAll()

    pool = threadpool.ThreadPool.Factory("test_pool1", 10)
    # This should raise.
    self.assertRaises(threading.ThreadError, pool.Start)

  def testThreadSpawningProblemsOneWorker(self):
    """Tests behavior when spawning threads fails."""

    self.mox.StubOutWithMock(logging, "warning")
    worker = threadpool._WorkerThread
    self.mox.StubOutWithMock(worker, "start")

    worker.start()
    worker.start().AndRaise(threading.ThreadError)

    # Could only start one worker thread.
    logging.warning(mox.StrContains("Could only start"), 1)

    self.mox.ReplayAll()

    # This should only write the log entry.
    pool = threadpool.ThreadPool.Factory("test_pool2", 10)
    pool.Start()

    # Even though the pool thinks it is running, there is only the fake
    # worker which does not process any jobs. Therefore, stopping the pool would
    # block.
    pool.Stop = lambda: None

  def testExportedFunctions(self):
    """Tests if the outstanding tasks variable is exported correctly."""

    pool = threadpool.ThreadPool.Factory("test_pool3", 10)
    # Do not start but push some tasks on the pool.
    for i in range(10):
      pool.AddTask(lambda: None, ())
      self.assertEqual(
          stats.STATS.GetMetricValue("test_pool3_outstanding_tasks"),
          i + 1)

  def testDuplicateNameError(self):
    """Tests that creating two pools with the same name fails."""

    prefix = self.test_pool.name
    self.assertRaises(threadpool.DuplicateThreadpoolError,
                      threadpool.ThreadPool, prefix, 10)

  def testDuplicateName(self):
    """Tests that we can get the same pool again through the factory."""

    prefix = "duplicate_name"

    pool = threadpool.ThreadPool.Factory(prefix, 10)
    self.assertEqual(pool.started, False)
    pool.Start()
    self.assertEqual(pool.started, True)

    # This should return the same pool as before.
    pool2 = threadpool.ThreadPool.Factory(prefix, 10)
    self.assertEqual(pool2.started, True)

  def testAnonymousThreadpool(self):
    """Tests that we can starts anonymous threadpools."""
    prefix = None
    pool = threadpool.ThreadPool.Factory(prefix, 10)
    self.assertEqual(pool.started, False)
    pool.Start()
    self.assertEqual(pool.started, True)
    pool.Stop()


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
