#!/usr/bin/env python
"""A registry of all new style well known flows."""

from grr_response_server import foreman
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import transfer

message_handlers = [
    administrative.ClientAlertHandler,
    administrative.ClientStartupHandler,
    administrative.ClientStatsHandler,
    foreman.ForemanMessageHandler,
    transfer.BlobHandler,
]

handler_name_map = {
    handler.handler_name: handler for handler in message_handlers
}
