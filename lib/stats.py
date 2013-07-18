#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Functions for audit and logging."""



import bisect
import collections
import functools
import os
import threading
import time
from wsgiref import validate


import psutil


from grr.client import conf as flags
import logging
from grr.lib import registry




class CountingExceptionMixin(object):
  """Each time this exception is raised we increment the counter."""
  # Override with the name of the counter
  counter = None

  def __init__(self, *args, **kwargs):
    if self.counter:
      STATS.Increment(self.counter)
    super(CountingExceptionMixin, self).__init__(*args, **kwargs)


class Varz(object):
  """This class keeps tabs on stats."""

  def __init__(self):
    self._exported_vars = {}
    self._exported_maps = {}
    self._callbacks = {}
    self._bins = {}
    self._avgs = {}
    self._timespan_avgs = {}
    self.lock = threading.Lock()

  def RegisterVar(self, varname):
    self._exported_vars[varname] = 0

  def IsRegistered(self, varname):
    return varname in self._exported_vars

  def Get(self, varname):
    # Initialize attributes to 0 if not initialized
    return self._exported_vars.setdefault(varname, 0)

  def Set(self, varname, value):
    """Sets the value for an exported variable."""
    with self.lock:
      if varname not in self._exported_vars:
        logging.error("Variable %s not registered.", varname)
      else:
        self._exported_vars[varname] = value

  def Increment(self, varname):
    self.Add(varname, 1)

  def Decrement(self, varname):
    self.Add(varname, -1)

  def Add(self, varname, n):
    with self.lock:
      try:
        self._exported_vars[varname] += n
      except KeyError as e:
        logging.error("Variable %s not registered.", e)

  def RegisterMap(self, varname, label, bin_list=None,
                  precision=6):
    """This registers an exported map to publish timing information."""
    _ = (label, precision)

    if varname in self._exported_maps:
      return self._exported_maps[varname]

    if bin_list:
      self._bins[varname] = bin_list
    else:
      self._bins[varname] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1,
                             1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10,
                             15, 20]
    m = {}

    for b in self._bins[varname]:
      m[b] = 0
    m[">" + str(self._bins[varname][-1])] = 0
    self._exported_maps[varname] = m

  def GetMap(self, varname):
    return self._exported_maps[varname]

  def ExportTime(self, varname, time_to_log):
    """A method to export times grouped in bins."""
    with self.lock:
      bins = self._bins[varname]
      pos = bisect.bisect(bins, time_to_log)
      var = self._exported_maps[varname]
      try:
        b = bins[pos]
        var[b] += 1
      except IndexError:
        # Time is greater than any bin in the array
        s = ">" + str(bins[-1])
        var[s] += 1

  def RegisterFunction(self, varname, function):
    self._callbacks[varname] = function

  def GetFunction(self, varname):
    """Return the current value of a exported function."""
    f = self._callbacks[varname]
    return f()

  def RegisterNAvg(self, varname, n):
    self.RegisterVar(varname)
    self._avgs[varname] = ([], 0.0, n)

  def ExportNAvg(self, varname, time_to_log):
    """A method to export times as running averages."""
    with self.lock:
      times, act_sum, n = self._avgs[varname]
      times.insert(0, time_to_log)
      act_sum += time_to_log
      if len(times) > n:
        act_sum -= times.pop()
      self._avgs[varname] = (times, act_sum, n)
      avg = act_sum / len(times)
    self.Set(varname, avg)

  def CalcTimespanAvg(self, varname):
    """Calculates the average when the exported variable is requested."""
    with self.lock:
      (values, timespan, act_sum) = self._timespan_avgs[varname]

      # Clean up old values
      now = time.time()
      while values:
        (timestamp, value) = values.popleft()
        if now - timestamp < timespan:
          values.appendleft((timestamp, value))
          break
        else:
          act_sum -= value

      self._timespan_avgs[varname] = (values, timespan, act_sum)
      if not values:
        return 0
      return act_sum / len(values)

  def RegisterTimespanAvg(self, varname, timespan):
    """This registers a new average that uses only recent samples.

    Args:
      varname: The name of the exported var.
      timespan: The length of interval that is considered for the average,
                given in seconds.
    """
    self.RegisterFunction(varname,
                          lambda name=varname: self.CalcTimespanAvg(name))

    self._timespan_avgs[varname] = (collections.deque(), timespan, 0.0)

  def ExportTimespanAvg(self, varname, time_to_log):
    with self.lock:
      (values, timespan, act_sum) = self._timespan_avgs[varname]

      # Clean up old values
      now = time.time()
      while values:
        (timestamp, value) = values.popleft()
        if now - timestamp < timespan:
          values.appendleft((timestamp, value))
          break
        else:
          act_sum -= value

      values.append((now, time_to_log))
      act_sum += time_to_log

      self._timespan_avgs[varname] = (values, timespan, act_sum)



# A global store of statistics
STATS = None


class StatsInit(registry.InitHook):

  def RunOnce(self):
    global STATS

    if STATS is None:
     STATS = Varz()




# Stats decorators
class TimingDecorator(object):
  """Base class for timing decorators."""

  def __init__(self, varname):
    self.varname = varname

  def ExportVarname(self, total_time):
    pass

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      start_time = time.time()
      res = None
      try:
        res = func(*args, **kwargs)
      finally:
        total_time = time.time() - start_time
        self.ExportVarname(total_time)

      return res

    return Decorated


class Timed(TimingDecorator):
  """A decorator to automatically export timing info for function calls."""

  def ExportVarname(self, total_time):
    STATS.ExportTime(self.varname, total_time)


class NAvgTimed(TimingDecorator):
  """A decorator to automatically export running average timing info."""

  def ExportVarname(self, total_time):
    STATS.ExportNAvg(self.varname, total_time)


class TimespanAvg(TimingDecorator):
  """A decorator to automatically export timing info for a set timespan."""

  def ExportVarname(self, total_time):
    STATS.ExportTimespanAvg(self.varname, total_time)


class AvgTimed(object):
  """A decorator to automatically export average timing info."""

  def __init__(self, varname):
    self.varname = varname
    self.total_time = 0.0
    self.n = 0

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """The decorated function."""
      start_time = time.time()
      try:
        res = func(*args, **kwargs)
      finally:
        total_time = time.time() - start_time
        self.total_time += total_time
        self.n += 1
        avg = self.total_time / self.n
        STATS.Set(self.varname, avg)
      return res

    return Decorated


class Counted(object):
  """A decorator to automatically count function calls."""

  def __init__(self, varname):
    self.varname = varname

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      try:
        res = func(*args, **kwargs)
      finally:
        STATS.Increment(self.varname)
      return res

    return Decorated


class StatsCollector(threading.Thread):
  """This thread keeps track of client stats."""

  exit = False

  def __init__(self, worker, sleep_time=10):
    super(StatsCollector, self).__init__()
    self.sleep_time = sleep_time
    self.daemon = True
    self.proc = psutil.Process(os.getpid())
    self.cpu_samples = []
    self.io_samples = []
    self.worker = worker
    STATS.RegisterFunction("grr_client_cpu_usage", self.PrintCpuSamples)
    STATS.RegisterFunction("grr_client_io_usage", self.PrintIOSample)

  def run(self):
    while True:
      time.sleep(self.sleep_time)
      if self.exit:
        break
      self.Collect()
      # Let the worker check if it should send back the stats.
      self.worker.CheckStats()

  def Collect(self):
    """Collects the stats."""

    user, system = self.proc.get_cpu_times()
    percent = self.proc.get_cpu_percent()
    self.cpu_samples.append((time.time(), user, system, percent))
    # Keep stats for one hour.
    self.cpu_samples = self.cpu_samples[-3600/self.sleep_time:]

    # Not supported on MacOS.
    try:
      _, _, read_bytes, write_bytes = self.proc.get_io_counters()
      self.io_samples.append((time.time(), read_bytes, write_bytes))
      self.io_samples = self.io_samples[-3600/self.sleep_time:]
    except (AttributeError, NotImplementedError, psutil.Error):
      pass

  def PrintCpuSamples(self):
    samples = [str(sample[3]) for sample in self.cpu_samples[-20:]]
    return ", ".join(samples)

  def PrintIOSample(self):
    try:
      return str(self.proc.get_io_counters())
    except (NotImplementedError, AttributeError):
      return "Not available on this platform."
