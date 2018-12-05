#!/usr/bin/env python
"""The GRR event publishing classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems
from future.utils import string_types
from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry


class EventListener(with_metaclass(registry.EventRegistry, object)):
  """Base Class for all Event Listeners.

  Event listeners can register for an event by specifying the event
  name in the EVENTS constant.
  """
  EVENTS = []

  def ProcessMessages(self, msgs=None, token=None):
    """Processes a message for the event."""

  def ProcessMessage(self, msg=None, token=None):
    return self.ProcessMessages([msg], token=token)


class Events(object):
  """A class that provides event publishing methods."""

  @classmethod
  def PublishEvent(cls, event_name, msg, token=None):
    """Publish the message into all listeners of the event.

    We send the message to all event handlers which contain this
    string in their EVENT static member. This allows the event to be
    sent to multiple interested listeners.

    Args:
      event_name: An event name.
      msg: The message to send to the event handler.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    cls.PublishMultipleEvents({event_name: [msg]}, token=token)

  @classmethod
  def PublishMultipleEvents(cls, events, token=None):
    """Publishes multiple messages at once.

    Args:
      events: A dict with keys being event names and values being lists of
        messages.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    event_name_map = registry.EventRegistry.EVENT_NAME_MAP
    for event_name, messages in iteritems(events):
      if not isinstance(event_name, string_types):
        raise ValueError(
            "Event names should be string, got: %s" % type(event_name))
      for msg in messages:
        if not isinstance(msg, rdfvalue.RDFValue):
          raise ValueError("Can only publish RDFValue instances.")

      for event_cls in event_name_map.get(event_name, []):
        event_cls().ProcessMessages(messages, token=token)
