#!/usr/bin/env python
"""Benchmark to compare different BlobStore implementations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io

import time

from absl import app
from absl import flags

import numpy as np

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core.lib import rdfvalue
from grr_response_server import blob_store
from grr_response_server import server_startup
from grr_response_server.rdfvalues import objects as rdf_objects

flags.DEFINE_list(
    "target",
    default=None,
    help="Benchmark the given BlobStore implementation classes. "
    "Separate multiple by comma.")

flags.DEFINE_list(
    "sizes",
    default=["500K", "200K", "100K", "50K", "5K", "500", "50"],
    help="Use the given blob sizes for the benchmark.")

flags.DEFINE_integer(
    "per_size_duration_seconds",
    default=30,
    help="Benchmark duration per blob size in seconds.")


def _MakeBlobStore(blobstore_name):
  try:
    cls = blob_store.REGISTRY[blobstore_name]
  except KeyError:
    raise ValueError("No blob store %s found." % blobstore_name)
  return blob_store.BlobStoreValidationWrapper(cls())


def _MakeRandomBlob(size_b, random_fd):
  blob_data = random_fd.read(size_b)
  blob_id = rdf_objects.BlobID.FromBlobData(blob_data)
  return blob_id, blob_data


def _Timed(fn, *args, **kwargs):
  start = time.time()
  result = fn(*args, **kwargs)
  return result, time.time() - start


def _PrintStats(size, size_b, durations):
  durations_ms = np.array(durations) * 1000
  total_s = sum(durations)
  qps = len(durations) / total_s
  print(
      "{size}\t{total:.1f}s\t{num}\t{qps:.2f}\t{bps: >7}\t{p50:.1f}\t{p90:.1f}"
      "\t{p95:.1f}\t{p99:.1f}".format(
          size=size,
          total=total_s,
          num=len(durations),
          qps=qps,
          bps=str(rdfvalue.ByteSize(int(size_b * qps))).replace("iB", ""),
          p50=np.percentile(durations_ms, 50),
          p90=np.percentile(durations_ms, 90),
          p95=np.percentile(durations_ms, 95),
          p99=np.percentile(durations_ms, 99),
      ))


def _RunBenchmark(bs, size_b, duration_sec, random_fd):
  """Returns a list of runtimes for writes of the given size."""
  start_timestamp = time.time()
  durations = []

  # Monotonically increasing time would be nice, but is unavailable in Py2.
  while time.time() < start_timestamp + duration_sec:
    blob_id, blob_data = _MakeRandomBlob(size_b, random_fd)
    _, write_time = _Timed(bs.WriteBlobs, {blob_id: blob_data})
    durations.append(write_time)
  return durations


def main(argv):
  """Main."""
  del argv  # Unused.

  # Initialise flows and config_lib
  server_startup.Init()

  if not flags.FLAGS.target:
    store_names = ", ".join(sorted(blob_store.REGISTRY.keys()))
    print("Missing --target. Use one or multiple of: {}.".format(store_names))
    exit(1)

  stores = [
      _MakeBlobStore(blobstore_name) for blobstore_name in flags.FLAGS.target
  ]

  with io.open("/dev/urandom", "rb") as random_fd:
    for blobstore_name, bs in zip(flags.FLAGS.target, stores):
      print()
      print(blobstore_name)
      print("size\ttotal\tnum\tqps\t  b/sec\tp50\tp90\tp95\tp99")
      for size in flags.FLAGS.sizes:
        size_b = rdfvalue.ByteSize(size)
        durations = _RunBenchmark(bs, size_b,
                                  flags.FLAGS.per_size_duration_seconds,
                                  random_fd)
        _PrintStats(size, size_b, durations)


if __name__ == "__main__":
  app.run(main)
