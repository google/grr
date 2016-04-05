#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""RDFValue implementations for hunts."""



from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class HuntNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntNotification
