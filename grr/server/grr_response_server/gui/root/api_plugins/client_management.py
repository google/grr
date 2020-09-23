#!/usr/bin/env python
# Lint as: python3
"""Root-access-level API handlers for client management."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api.root import client_management_pb2
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base


def _CheckFleetspeakConnection() -> None:
  if fleetspeak_connector.CONN is None:
    raise Exception("Fleetspeak connection is not available.")


class ApiKillFleetspeakArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_management_pb2.ApiKillFleetspeakArgs
  rdf_deps = [
      rdf_client.ClientURN,
  ]


class ApiKillFleetspeakHandler(api_call_handler_base.ApiCallHandler):
  """Kills fleetspeak on the given client."""

  args_type = ApiKillFleetspeakArgs

  def Handle(self,
             args: ApiKillFleetspeakArgs,
             context: Optional[api_call_context.ApiCallContext] = None) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.KillFleetspeak(args.client_id.Basename(), args.force)


class ApiRestartFleetspeakGrrServiceArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_management_pb2.ApiRestartFleetspeakGrrServiceArgs
  rdf_deps = [
      rdf_client.ClientURN,
  ]


class ApiRestartFleetspeakGrrServiceHandler(api_call_handler_base.ApiCallHandler
                                           ):
  """Restarts the GRR fleetspeak service on the given client."""

  args_type = ApiRestartFleetspeakGrrServiceArgs

  def Handle(self,
             args: ApiRestartFleetspeakGrrServiceArgs,
             context: Optional[api_call_context.ApiCallContext] = None) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.RestartFleetspeakGrrService(args.client_id.Basename())
