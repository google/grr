#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the ThreadPool class."""



import threading

import mox

from grr.client import conf
import logging
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import threadpool


class ThreadPoolTest(mox.MoxTestBase):
  """Tests for the ThreadPool class."""

  def setUp(self):
    super(ThreadPoolTest, self).setUp()

    self.base_thread_count = threading.active_count()

    prefix = "pool-%s" % self._testMethodName
    self.test_pool = threadpool.ThreadPool.Factory(prefix, 500)
    self.test_pool.Start()

  def tearDown(self):
    self.test_pool.Stop()

  def testThreadCreation(self):
    """Checks if at least 100 workers can be created.

    The standard size for the thread pool is 500 workers. It could be
    that there are fewer threads generated (for example due to memory
    constraints) but we demand at least 100 workers in the default
    settings here.
    """
    self.assertTrue(threading.active_count() > 100)

  def testStopping(self):
    """Tests if all worker threads terminate if the thread pool is stopped."""

    self.test_pool.Stop()
    self.assertTrue(threading.active_count() < self.base_thread_count + 5)
    self.test_pool.Start()
    self.assertTrue(threading.active_count() > self.base_thread_count + 100)
    self.test_pool.Stop()
    # Make sure there are not significantly more threads running than before.
    self.assertTrue(threading.active_count() < self.base_thread_count + 5)

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
      self.lock.acquire()
      try:
        list_obj.append(element)
      finally:
        self.lock.release()

    # We want to schedule more than 500 tasks here so we can see if
    # reusing threads is actually working and more than 1000 to see if
    # we can schedule more tasks than fit into the queue.

    test_list = []
    for i in range(1500):
      self.test_pool.AddTask(Insert, (test_list, i,))

    self.test_pool.Join()
    test_list.sort()
    self.assertEqual(range(1500), test_list)

  def testRunRaisingTask(self):
    """Tests the behavior of the pool if a task throws an exception."""

    self.lock = threading.Lock()

    def IRaise(some_obj):
      """This method just raises an exception."""
      self.lock.acquire()
      try:
        # This simulates an error by calling a non-existent function.
        some_obj.process()
      finally:
        self.lock.release()

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
    self.assertEqual(stats.STATS.Get(self.test_pool.name + "_task_exceptions"),
                     2)

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
      self.assertEqual(i+1,
                       stats.STATS.GetFunction("test_pool3_outstanding_tasks"))

  def testDuplicateNameError(self):
    """Tests that creating two pools with the same name fails."""

    prefix = self.test_pool.name
    self.assertRaises(threadpool.DuplicateThreadpoolError,
                      threadpool.ThreadPool, prefix, 10)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
