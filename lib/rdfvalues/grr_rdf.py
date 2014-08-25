#!/usr/bin/env python
"""Basic GRR rdfvalue definitions."""

from grr.lib import rdfvalue
from grr.proto import jobs_pb2


# TODO(user): deprecate as soon as migration to AFF4ObjectLabelsList is
# complete.
class LabelList(rdfvalue.RDFValueArray):
  """A list of labels."""
  rdf_type = rdfvalue.RDFString


class CronJobRunStatus(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus
