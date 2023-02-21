#!/usr/bin/env python
"""Tests for the ThreadPool class."""

import logging
import queue
import threading
import time
from unittest import mock

from absl import app

from grr_response_core.lib import utils
from grr_response_server import threadpool
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class ThreadPoolTest(stats_test_lib.StatsTestMixin, test_lib.GRRBaseTest):
  """Tests for the ThreadPool class."""
  NUMBER_OF_THREADS = 1
  MAXIMUM_THREADS = 20
  NUMBER_OF_TASKS = 1500
  sleep_time = 0.1

  def setUp(self):
    super().setUp()
    self.base_thread_count = threading.active_count()

    prefix = "pool-%s" % self._testMethodName
    self.test_pool = threadpool.ThreadPool.Factory(
        prefix, self.NUMBER_OF_THREADS, max_threads=self.MAXIMUM_THREADS)
    self.test_pool.Start()
    self.addCleanup(self.test_pool.Stop)

  def WaitUntil(self, condition_cb, timeout=5):
    """Wait a fixed time until the condition is true."""
    for _ in range(int(timeout / self.sleep_time)):
      res = condition_cb()
      if res:
        return res

      time.sleep(self.sleep_time)

    raise RuntimeError("Timeout exceeded. Condition not true")

  def Count(self, thread_name):
    worker_threads = [
        thread for thread in threading.enumerate() if thread_name in thread.name
    ]
    return len(worker_threads)

  def testThreadCreation(self):
    """Ensure the thread pool started the minimum number of threads."""
    self.assertEqual(
        self.Count("pool-testThreadCreation"), self.NUMBER_OF_THREADS)

  def testStopping(self):
    """Tests if all worker threads terminate if the thread pool is stopped."""
    self.assertEqual(self.Count("pool-testStopping"), self.NUMBER_OF_THREADS)
    self.test_pool.Stop()

    self.assertEqual(self.Count("pool-testStopping"), 0)
    self.test_pool.Start()

    self.assertEqual(self.Count("pool-testStopping"), self.NUMBER_OF_THREADS)
    self.test_pool.Stop()
    self.assertEqual(self.Count("pool-testStopping"), 0)

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

    test_list = []
    for i in range(self.NUMBER_OF_TASKS):
      self.test_pool.AddTask(Insert, (test_list, i))

    self.test_pool.Join()
    test_list.sort()
    self.assertEqual(list(range(self.NUMBER_OF_TASKS)), test_list)

  def testAdditionalWorkersAreAllocatedWhenSingleTaskTakesLong(self):
    wait_event_1, wait_event_2 = threading.Event(), threading.Event()
    signal_event_1, signal_event_2 = threading.Event(), threading.Event()

    try:
      sample = []

      def RunFn(signal_event, wait_event, num):
        sample.append(num)
        signal_event.set()
        wait_event.wait()

      self.test_pool.AddTask(
          RunFn, (wait_event_1, signal_event_1, 0),
          blocking=False,
          inline=False)
      wait_event_1.wait(10)
      self.assertEqual(sample, [0])
      # Now task 1 is running, schedule task 2 and make sure it runs and
      # completes.
      self.test_pool.AddTask(
          RunFn, (wait_event_2, signal_event_2, 1),
          blocking=False,
          inline=False)
      wait_event_2.wait(10)
      self.assertEqual(sample, [0, 1])
    finally:
      signal_event_1.set()
      signal_event_2.set()

  def testAddingTaskToNonStartedThreadPoolRaises(self):
    pool = threadpool.ThreadPool.Factory("t", 10)
    with self.assertRaises(threadpool.ThreadPoolNotStartedError):
      pool.AddTask(lambda: None, ())

  def testRunRaisingTask(self):
    """Tests the behavior of the pool if a task throws an exception."""

    self.lock = threading.Lock()

    def IRaise(some_obj):
      """This method just raises an exception."""
      with self.lock:
        # This simulates an error by calling a non-existent function.
        some_obj.process()

    self.exception_args = []

    def MockException(*args):
      self.exception_args = args

    with self.assertStatsCounterDelta(
        2, threadpool.THREADPOOL_TASK_EXCEPTIONS, fields=[self.test_pool.name]):
      with mock.patch.object(logging, "exception", MockException):
        self.test_pool.AddTask(IRaise, (None,), "Raising")
        self.test_pool.AddTask(IRaise, (None,), "Raising")
        self.test_pool.Join()

    # Check that an exception is raised.
    self.assertIn("exception in worker thread", self.exception_args[0])
    self.assertEqual(self.exception_args[1], "Raising")

  def testFailToCreateThread(self):
    """Test that we handle thread creation problems ok."""
    # The pool starts off with the minimum number of threads.
    self.assertLen(self.test_pool, self.NUMBER_OF_THREADS)

    done_event = threading.Event()

    def Block(done):
      done.wait()

    def RaisingStart(_):
      raise threading.ThreadError()

    # Now simulate failure of creating threads.
    with mock.patch.object(threadpool._WorkerThread, "start", RaisingStart):
      # Fill all the existing threads and wait for them to become busy.
      self.test_pool.AddTask(Block, (done_event,))
      self.WaitUntil(lambda: self.test_pool.busy_threads == self.
                     NUMBER_OF_THREADS)

      # Now fill the queue completely..
      for _ in range(self.MAXIMUM_THREADS):
        self.test_pool.AddTask(Block, (done_event,))

      # Trying to push this task will overflow the queue, and would normally
      # cause a new thread to start. We use non blocking mode to receive the
      # exception.
      self.assertRaises(
          threadpool.Full,
          self.test_pool.AddTask,
          Block, (done_event,),
          blocking=False,
          inline=False)

      # Release the blocking tasks.
      done_event.set()
      self.test_pool.Join()

  def testBlockingTasks(self):
    # The pool starts off with the minimum number of threads.
    self.assertLen(self.test_pool, self.NUMBER_OF_THREADS)

    done_event = threading.Event()
    self.lock = threading.Lock()
    res = []

    def Block(done):
      done.wait()

    def Insert(list_obj, element):
      with self.lock:
        list_obj.append(element)

    # Schedule the maximum number of threads of blocking tasks and the same of
    # insert tasks. The threads are now all blocked, and the inserts are
    # waiting in the queue.
    for _ in range(self.MAXIMUM_THREADS):
      self.test_pool.AddTask(Block, (done_event,), "Blocking")

    # Wait until the threadpool picks up tasks.
    self.WaitUntil(lambda: self.test_pool.busy_threads == self.MAXIMUM_THREADS)

    # Now there's maximum number of threads active and the queue is empty.
    self.assertEqual(self.test_pool.pending_tasks, 0)

    # Now we push these tasks on the queue, but they're not going to be
    # processed, since all threads are busy.
    for i in range(self.MAXIMUM_THREADS):
      self.test_pool.AddTask(
          Insert, (res, i), "Insert", blocking=True, inline=False)

    # There should be 20 workers created and they should consume all the
    # blocking tasks.
    self.WaitUntil(lambda: self.test_pool.busy_threads == self.MAXIMUM_THREADS)

    # No Insert tasks are running yet.
    self.assertEqual(res, [])

    # There are 20 tasks waiting on the queue.
    self.assertEqual(self.test_pool.pending_tasks, self.MAXIMUM_THREADS)

    # Inserting more tasks than the queue can hold should lead to processing
    # the tasks inline. This effectively causes these tasks to skip over the
    # tasks which are waiting in the queue.
    for i in range(10, 20):
      self.test_pool.AddTask(Insert, (res, i), "Insert", inline=True)

    res.sort()
    self.assertEqual(res, list(range(10, 20)))

    # This should release all the busy tasks. It will also cause the workers
    # to process all the Insert tasks in the queue.
    done_event.set()

    self.test_pool.Join()

    # Now the rest of the tasks should have been processed as well.
    self.assertCountEqual(res[10:], list(range(20)))

  def testThreadsReaped(self):
    """Check that threads are reaped when too old."""
    self.now = 0
    with utils.MultiStubber((time, "time", lambda: self.now),
                            (threading, "_time", lambda: self.now),
                            (queue, "_time", lambda: self.now),
                            (self.test_pool, "CPUUsage", lambda: 0)):
      done_event = threading.Event()

      res = []

      def Block(done, count):
        done.wait()
        res.append(count)

      for i in range(2 * self.MAXIMUM_THREADS):
        self.test_pool.AddTask(Block, (done_event, i), "Blocking", inline=False)

      self.assertLen(self.test_pool, self.MAXIMUM_THREADS)

      # Release the threads. All threads are now idle.
      done_event.set()

      # Fast forward the time
      self.now = 1000

      # Threads will now kill themselves off and the threadpool will be reduced
      # to the minimum number of threads..
      self.WaitUntil(lambda: len(self.test_pool) == self.NUMBER_OF_THREADS)

      # Ensure we have the minimum number of threads left now.
      self.assertLen(self.test_pool, self.NUMBER_OF_THREADS)

  def testExportedFunctions(self):
    """Tests if the outstanding tasks variable is exported correctly."""
    signal_event, wait_event = threading.Event(), threading.Event()

    def RunFn():
      signal_event.set()
      wait_event.wait()

    pool_name = "test_pool3"
    pool = threadpool.ThreadPool.Factory(pool_name, 10)
    pool.Start()
    try:
      # First 10 tasks should be scheduled immediately, as we have max_threads
      # set to 10.
      for _ in range(10):
        signal_event.clear()
        pool.AddTask(RunFn, ())
        signal_event.wait(10)

      # Next 5 tasks should sit in the queue.
      for _ in range(5):
        with self.assertStatsCounterDelta(
            1, threadpool.THREADPOOL_OUTSTANDING_TASKS, fields=[pool_name]):
          pool.AddTask(RunFn, ())

    finally:
      wait_event.set()
      pool.Stop()

  def testDuplicateNameError(self):
    """Tests that creating two pools with the same name fails."""

    prefix = self.test_pool.name
    self.assertRaises(threadpool.DuplicateThreadpoolError,
                      threadpool.ThreadPool, prefix, 10)

  def testDuplicateName(self):
    """Tests that we can get the same pool again through the factory."""

    prefix = "duplicate_name"
    pool = threadpool.ThreadPool.Factory(prefix, 10)
    try:
      self.assertEqual(pool.started, False)
      pool.Start()
      self.assertEqual(pool.started, True)

      # This should return the same pool as before.
      pool2 = threadpool.ThreadPool.Factory(prefix, 10)
      self.assertEqual(pool2.started, True)
    finally:
      pool.Stop()

  def testAnonymousThreadpool(self):
    """Tests that we can't starts anonymous threadpools."""
    prefix = None
    with self.assertRaises(ValueError):
      threadpool.ThreadPool.Factory(prefix, 10)


class DummyConverter(threadpool.BatchConverter):

  def __init__(self, **kwargs):
    self.sleep_time = kwargs.pop("sleep_time")

    super().__init__(**kwargs)

    self.batches = []
    self.threads = []
    self.results = []

  def ConvertBatch(self, batch):
    time.sleep(self.sleep_time)

    self.batches.append(batch)
    self.threads.append(threading.current_thread().ident)
    self.results.extend([s + "*" for s in batch])


class BatchConverterTest(test_lib.GRRBaseTest):
  """BatchConverter tests."""

  def testMultiThreadedConverter(self):
    converter = DummyConverter(
        threadpool_size=10,
        batch_size=2,
        sleep_time=0.1,
        threadpool_prefix="multi_threaded")
    test_data = [str(i) for i in range(10)]

    converter.Convert(test_data)

    self.assertLen(set(converter.threads), 5)

    self.assertLen(converter.batches, 5)
    for batch in converter.batches:
      self.assertLen(batch, 2)

    self.assertLen(converter.results, 10)
    for i, r in enumerate(sorted(converter.results)):
      self.assertEqual(r, str(i) + "*")

  def testSingleThreadedConverter(self):
    converter = DummyConverter(
        threadpool_size=0,
        batch_size=2,
        sleep_time=0,
        threadpool_prefix="single_threaded")
    test_data = [str(i) for i in range(10)]

    converter.Convert(test_data)

    self.assertLen(set(converter.threads), 1)

    self.assertLen(converter.batches, 5)
    for batch in converter.batches:
      self.assertLen(batch, 2)

    self.assertLen(converter.results, 10)
    for i, r in enumerate(sorted(converter.results)):
      self.assertEqual(r, str(i) + "*")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
