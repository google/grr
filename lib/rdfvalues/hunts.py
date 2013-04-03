#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""RDFValue implementations for hunts."""



from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class HuntNotification(rdfvalue.RDFProto):
  _proto = jobs_pb2.HuntNotification
