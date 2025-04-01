#!/usr/bin/env python
"""Generic definitions for Fleetspeak."""

import dataclasses
from typing import Mapping, Sequence

from google.protobuf import any_pb2


@dataclasses.dataclass(frozen=True)
class MessageBatch:
  """Group of messages delivered by Fleetspeak to a frontend.

  Attributes:
    client_id: Identifier of the endpoint that sent messages.
    service: Name of the Fleetspeak agent service that sent messages.
    message_type: Type of messages in the batch.
    messages: Actual messages of this batch.
    validation_info_tags: Tags produced by the Fleetspeak validation procedure.
  """

  client_id: str
  service: str
  message_type: str
  messages: Sequence[any_pb2.Any]
  validation_info_tags: Mapping[str, str]
