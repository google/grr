#!/usr/bin/env python
"""Stats-related client rdfvalues."""

from __future__ import absolute_import
from __future__ import division

from future.utils import itervalues

from grr_response_core.lib import rdfvalue

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import jobs_pb2


class CpuSeconds(rdf_structs.RDFProtoStruct):
  """CPU usage is reported as both a system and user components."""
  protobuf = jobs_pb2.CpuSeconds


class CpuSample(rdf_structs.RDFProtoStruct):
  """A single CPU sample."""
  protobuf = jobs_pb2.CpuSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromMany(cls, samples):
    """Constructs a single sample that best represents a list of samples.

    Args:
      samples: An iterable collection of `CpuSample` instances.

    Returns:
      A `CpuSample` instance representing `samples`.

    Raises:
      ValueError: If `samples` is empty.
    """
    if not samples:
      raise ValueError("Empty `samples` argument")

    # It only makes sense to average the CPU percentage. For all other values
    # we simply take the biggest of them.
    cpu_percent = sum(sample.cpu_percent for sample in samples) / len(samples)

    return CpuSample(
        timestamp=max(sample.timestamp for sample in samples),
        cpu_percent=cpu_percent,
        user_cpu_time=max(sample.user_cpu_time for sample in samples),
        system_cpu_time=max(sample.system_cpu_time for sample in samples))


class IOSample(rdf_structs.RDFProtoStruct):
  """A single I/O sample as collected by `psutil`."""

  protobuf = jobs_pb2.IOSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromMany(cls, samples):
    """Constructs a single sample that best represents a list of samples.

    Args:
      samples: An iterable collection of `IOSample` instances.

    Returns:
      An `IOSample` instance representing `samples`.

    Raises:
      ValueError: If `samples` is empty.
    """
    if not samples:
      raise ValueError("Empty `samples` argument")

    return IOSample(
        timestamp=max(sample.timestamp for sample in samples),
        read_bytes=max(sample.read_bytes for sample in samples),
        write_bytes=max(sample.write_bytes for sample in samples))


class ClientStats(rdf_structs.RDFProtoStruct):
  """A client stat object."""
  protobuf = jobs_pb2.ClientStats
  rdf_deps = [
      CpuSample,
      IOSample,
      rdfvalue.RDFDatetime,
  ]

  DEFAULT_SAMPLING_INTERVAL = rdfvalue.Duration("60s")

  @classmethod
  def Downsampled(cls, stats, interval=None):
    """Constructs a copy of given stats but downsampled to given interval.

    Args:
      stats: A `ClientStats` instance.
      interval: A downsampling interval.

    Returns:
      A downsampled `ClientStats` instance.
    """
    interval = interval or cls.DEFAULT_SAMPLING_INTERVAL

    result = cls(stats)
    result.cpu_samples = cls._Downsample(
        kind=CpuSample, samples=stats.cpu_samples, interval=interval)
    result.io_samples = cls._Downsample(
        kind=IOSample, samples=stats.io_samples, interval=interval)
    return result

  @classmethod
  def _Downsample(cls, kind, samples, interval):
    buckets = {}
    for sample in samples:
      bucket = buckets.setdefault(sample.timestamp.Floor(interval), [])
      bucket.append(sample)

    for bucket in itervalues(buckets):
      yield kind.FromMany(bucket)


class ClientResources(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing the client resource usage."""
  protobuf = jobs_pb2.ClientResources
  rdf_deps = [
      rdf_client.ClientURN,
      CpuSeconds,
      rdfvalue.SessionID,
  ]
