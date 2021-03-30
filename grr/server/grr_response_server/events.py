#!/usr/bin/env python
"""The GRR event publishing classes."""


from grr_response_core.lib import rdfvalue
from grr_response_core.lib.registry import EventRegistry


class EventListener(metaclass=EventRegistry):
  """Base Class for all Event Listeners.

  Event listeners can register for an event by specifying the event
  name in the EVENTS constant.
  """
  EVENTS = []

  def ProcessEvents(self, msgs=None, publisher_username=None):
    """Processes a message for the event."""

  def ProcessEvent(self, event=None, publisher_username=None):
    return self.ProcessEvents([event], publisher_username=publisher_username)


class Events(object):
  """A class that provides event publishing methods."""

  @classmethod
  def PublishEvent(cls, event_name, event, username=None):
    """Publish the message into all listeners of the event.

    We send the message to all event handlers which contain this
    string in their EVENT static member. This allows the event to be
    sent to multiple interested listeners.

    Args:
      event_name: An event name.
      event: The message to send to the event handler.
      username: Username of the publisher of the message.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    cls.PublishMultipleEvents({event_name: [event]}, username=username)

  @classmethod
  def PublishMultipleEvents(cls, events, username=None):
    """Publishes multiple messages at once.

    Args:
      events: A dict with keys being event names and values being lists of
        messages.
      username: Username of the publisher of the messages.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    event_name_map = EventRegistry.EVENT_NAME_MAP
    for event_name, messages in events.items():
      if not isinstance(event_name, str):
        raise ValueError(
            "Event names should be string, got: %s" % type(event_name))
      for msg in messages:
        if not isinstance(msg, rdfvalue.RDFValue):
          raise ValueError("Can only publish RDFValue instances.")

      for event_cls in event_name_map.get(event_name, []):
        event_cls().ProcessEvents(messages, publisher_username=username)
