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

"""A simple thread pool for the Google Response Rig.

This file defines a simple thread pool that is used throughout this
project for parallelizing data store accesses. This thread pool is
rather lightweight and optimized to be used in combination with the
GRR data_store modules. It is not meant to be general purpose - if you
need a generalized thread pool, you should probably use a better
suited alternative implementation.

If during creation not all new worker threads can be spawned by the
ThreadPool, a log entry will be written but execution will continue
using a smaller pool of workers. In this case, consider reducing the
--threadpool_size.

Example usage:
>>> def PrintMsg(value):
>>>   print "Message: %s" % value
>>> for _ in range(10):
>>>   SharedPool().AddTask(PrintMsg, ("Hello World!", ))
>>> SharedPool().Join()

"""



import Queue
import threading
import time


import logging

from grr.lib import stats

STOP_MESSAGE = "Stop message"


class Error(Exception):
  pass


class DuplicateThreadpoolError(Error):
  """Raised when a thread pool with the same name already exists."""
  pass


class _WorkerThread(threading.Thread):
  """The workers used in the ThreadPool class."""

  def __init__(self, threadpool_name, queue):
    """Initializer.

    This creates a new worker object for the ThreadPool class.

    Args:
      threadpool_name: The name of the thread pool this worker belongs to.
      queue: A Queue.Queue object that is used by the ThreadPool class to
          communicate with the workers. When a new task arrives, the ThreadPool
          notifies the workers by putting a message into this queue that has the
          format (target, args, name, queueing_time).

          target - A callable, the function to call.
          args - A tuple of positional arguments to target. Keyword arguments
                 are not supported.
          name - A name for this task.
          queueing_time - The timestamp when this task was queued as returned by
                          time.time().

          Or, alternatively, the message in the queue can be STOP_MESSAGE
          which indicates that the worker should terminate.
    """

    threading.Thread.__init__(self, name=threadpool_name + "_worker")
    self._queue = queue
    self.daemon = True
    self.threadpool_name = threadpool_name

  def run(self):
    """This overrides the Thread.run method.

    This method checks in an endless loop if new tasks are available
    in the queue and processes them.
    """
    while True:
      stats.STATS.Increment(self.threadpool_name + "_idle_threads")

      task = self._queue.get()

      try:
        stats.STATS.Decrement(self.threadpool_name + "_idle_threads")

        if task == STOP_MESSAGE:
          break

        target, args, name, queueing_time = task

        time_in_queue = time.time() - queueing_time
        stats.STATS.ExportTime(self.threadpool_name + "_queueing_time",
                               time_in_queue)

        start_time = time.time()
        try:
          target(*args)
        # We can't let a worker die because one of the tasks it has to process
        # throws an exception. Therefore, we catch every error that is
        # raised in the call to target().
        except Exception as e:
          stats.STATS.Increment(self.threadpool_name + "_task_exceptions")
          logging.exception("Caught exception in worker thread (%s): %s",
                            name, str(e))

        total_time = time.time() - start_time
        stats.STATS.ExportTimespanAvg(self.threadpool_name +
                                      "_working_time_running_avg", total_time)
        stats.STATS.ExportTime(self.threadpool_name + "_working_time",
                               total_time)
      finally:
        self._queue.task_done()


THREADPOOL = None


class ThreadPool(object):
  """A simple implementation of a thread pool used in GRR.

  This class implements a very simple thread pool intended for
  lightweight parallelization of data_store accesses.

  Note that this class should not be instantiated directly, but the Factory
  should be used.
  """
  # A global dictionary of pools, keyed by pool name.
  POOLS = {}
  factory_lock = threading.Lock()

  @classmethod
  def Factory(cls, name, num_threads):
    """Creates a new thread pool with the given name.

    If the thread pool of this name already exist, we just return the existing
    one. This allows us to have different pools with different characteristics
    used by different parts of the code, at the same time.

    Args:
      name: The name of the required pool.
      num_threads: The number of threads in the pool.

    Returns:
      A threadpool instance.
    """
    with cls.factory_lock:
      result = cls.POOLS.get(name)
      if result is None:
        cls.POOLS[name] = result = cls(name, num_threads)

      return result

  def __init__(self, name, num_threads):
    """This creates a new thread pool using num_threads workers.

    Args:
      name: A prefix to identify this thread pool in the exported stats.
      num_threads: The intended number of worker threads this pool should have.

    Raises:
      threading.ThreadError: If no threads can be spawned at all, ThreadError
                             will be raised.
      DuplicateThreadpoolError: This exception is raised if a thread pool with
                                the desired name already exists.
    """

    self._queue = Queue.Queue(2 * num_threads)
    self.num_threads = num_threads
    self.name = name
    self.started = False

    if stats.STATS.IsRegistered(self.name + "_idle_threads"):
      raise DuplicateThreadpoolError(
          "A thread pool with the name %s already exists.", name)

    stats.STATS.RegisterFunction(name + "_outstanding_tasks", self._queue.qsize)
    stats.STATS.RegisterVar(self.name + "_idle_threads")
    stats.STATS.RegisterVar(self.name + "_outstanding_tasks")
    stats.STATS.RegisterVar(self.name + "_task_exceptions")
    stats.STATS.RegisterMap(self.name + "_working_time", "times", precision=0)
    stats.STATS.RegisterMap(self.name + "_queueing_time", "times", precision=0)
    stats.STATS.RegisterTimespanAvg(self.name + "_working_time_running_avg", 60)

  def __del__(self):
    if self.started:
      self.Stop()

  def Start(self):
    """This starts the worker threads."""
    self.workers = []

    if not self.started:
      self.started = True
      for thread_counter in range(self.num_threads):
        try:
          worker = _WorkerThread(self.name, self._queue)
          worker.start()
          self.workers.append(worker)
        except threading.ThreadError:
          if thread_counter == 0:
            logging.error(("Threadpool exception: "
                           "Could not spawn worker threads."))
            # If we cannot spawn any threads at all, bail out.
            raise
          else:
            logging.warning(("Threadpool exception: "
                             "Could only start %d threads."), thread_counter)
          break

  def Stop(self):
    """This stops all the worker threads."""
    if not self.started:
      logging.warning("Tried to stop a thread pool that was not running.")
      return

    # Send a stop message to all the workers.
    for _ in self.workers:
      self._queue.put(STOP_MESSAGE)

    self.started = False
    self.Join()

    # Wait for the threads to all exit now.
    for worker in self.workers:
      worker.join()

  def AddTask(self, target, args, name="Unnamed task"):
    """Adds a task to be processed later.

    Args:
      target: A callable which should be processed by one of the workers.
      args: A tuple of arguments to target.
      name: The name of this task. Used to identify tasks in the log.
    """
    self._queue.put((target, args, name, time.time()))

  def Join(self):
    """Waits until all outstanding tasks are completed."""""
    self._queue.join()
