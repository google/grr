#!/usr/bin/env python
"""Basic GRR rdfvalue definitions."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


# TODO(user): deprecate as soon as migration to AFF4ObjectLabelsList is
# complete.
class LabelList(rdf_protodict.RDFValueArray):
  """A list of labels."""
  rdf_type = rdfvalue.RDFString


class CronJobRunStatus(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus
