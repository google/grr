#!/usr/bin/env python
"""Handlers for API calls (that can be bound to HTTP API, for example)."""




# pylint:disable=unused-import
# Import all api_plugins so they are available when we set up acls.
from grr.gui import api_plugins
# pylint: enable=unused-import
from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr.proto import api_pb2


class ApiCallAdditionalArgs(structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCallAdditionalArgs

  def GetArgsClass(self):
    return rdfvalue.RDFValue.classes[self.type]
