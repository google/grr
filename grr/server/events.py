#!/usr/bin/env python
"""The GRR event publishing classes."""

import functools
import logging


from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr.server import queue_manager


class AuditEvent(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.AuditEvent
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  def __init__(self, initializer=None, age=None, **kwargs):

    super(AuditEvent, self).__init__(initializer=initializer, age=age, **kwargs)
    if not self.id:
      self.id = utils.PRNG.GetULong()
    if not self.timestamp:
      self.timestamp = rdfvalue.RDFDatetime.Now()


def EventHandler(source_restriction=False,
                 auth_required=True,
                 allow_client_access=False):
  """A convenience decorator for Event Handlers.

  Args:

    source_restriction: If this is set to True, each time a message is
      received, its source is passed to the method "CheckSource" of
      the event listener. If that method returns True, processing is
      permitted. Otherwise, the message is rejected.

    auth_required: Do we require messages to be authenticated? If the
                message is not authenticated we raise.

    allow_client_access: If True this event is allowed to handle published
      events from clients.

  Returns:
    A decorator which injects the following keyword args to the handler:

     message: The original raw message RDFValue (useful for checking the
       source).
     event: The decoded RDFValue.

  """

  def Decorator(f):
    """Initialised Decorator."""

    @functools.wraps(f)
    def Decorated(self, msg):
      """A decorator that assists in enforcing EventListener restrictions."""
      if (auth_required and
          msg.auth_state != msg.AuthorizationState.AUTHENTICATED):
        raise ValueError("Message from %s not authenticated." % msg.source)

      if (not allow_client_access and msg.source and
          rdf_client.ClientURN.Validate(msg.source)):
        raise ValueError("Event does not support clients.")

      if source_restriction:
        source_check_method = getattr(self, "CheckSource")
        if not source_check_method:
          raise ValueError("CheckSource method not found.")
        if not source_check_method(msg.source):
          raise ValueError("Message source invalid.")

      stats.STATS.IncrementCounter("grr_worker_states_run")
      rdf_msg = rdf_flows.GrrMessage(msg)
      res = f(self, message=rdf_msg, event=rdf_msg.payload)
      return res

    return Decorated

  return Decorator


class Events(object):
  """A class that provides event publishing methods."""

  @classmethod
  def PublishEvent(cls, event_name, msg, delay=None, token=None):
    """Publish the message into all listeners of the event.

    If event_name is a string, we send the message to all event handlers which
    contain this string in their EVENT static member. This allows the event to
    be sent to multiple interested listeners. Alternatively, the event_name can
    specify a single URN of an event listener to receive the message.

    Args:
      event_name: Either a URN of an event listener or an event name.
      msg: The message to send to the event handler.
      delay: An rdfvalue.Duration object. If given, the event will be published
             after the indicated time.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    cls.PublishMultipleEvents({event_name: [msg]}, delay=delay, token=token)

  @classmethod
  def PublishMultipleEvents(cls, events, delay=None, token=None):
    """Publish the message into all listeners of the event.

    If event_name is a string, we send the message to all event handlers which
    contain this string in their EVENT static member. This allows the event to
    be sent to multiple interested listeners. Alternatively, the event_name can
    specify a single URN of an event listener to receive the message.

    Args:

      events: A dict with keys being event names and values being lists of
        messages.
      delay: An rdfvalue.Duration object. If given, the event will be published
             after the indicated time.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    with queue_manager.WellKnownQueueManager(token=token) as manager:
      event_name_map = registry.EventRegistry.EVENT_NAME_MAP
      for event_name, messages in events.iteritems():
        handler_urns = []
        if isinstance(event_name, basestring):
          for event_cls in event_name_map.get(event_name, []):
            if event_cls.well_known_session_id is None:
              logging.error("Well known flow %s has no session_id.",
                            event_cls.__name__)
            else:
              handler_urns.append(event_cls.well_known_session_id)

        else:
          handler_urns.append(event_name)

        for msg in messages:
          # Allow the event name to be either a string or a URN of an event
          # listener.
          if not isinstance(msg, rdfvalue.RDFValue):
            raise ValueError("Can only publish RDFValue instances.")

          # Wrap the message in a GrrMessage if needed.
          if not isinstance(msg, rdf_flows.GrrMessage):
            msg = rdf_flows.GrrMessage(payload=msg)

          # Randomize the response id or events will get overwritten.
          msg.response_id = msg.task_id = msg.GenerateTaskID()
          # Well known flows always listen for request id 0.
          msg.request_id = 0

          timestamp = None
          if delay:
            timestamp = (
                rdfvalue.RDFDatetime.Now() + delay).AsMicroSecondsFromEpoch()

          # Forward the message to the well known flow's queue.
          for event_urn in handler_urns:
            tmp_msg = msg.Copy()
            tmp_msg.session_id = event_urn
            manager.QueueResponse(tmp_msg)
            manager.QueueNotification(
                rdf_flows.GrrNotification(
                    session_id=event_urn,
                    priority=msg.priority,
                    timestamp=timestamp))

  @classmethod
  def PublishEventInline(cls, event_name, msg, token=None):
    """Directly publish the message into all listeners of the event."""

    if not isinstance(msg, rdfvalue.RDFValue):
      raise ValueError("Can only publish RDFValue instances.")

    # Wrap the message in a GrrMessage if needed.
    if not isinstance(msg, rdf_flows.GrrMessage):
      msg = rdf_flows.GrrMessage(payload=msg)

    # Event name must be a string.
    if not isinstance(event_name, basestring):
      raise ValueError("Event name must be a string.")
    event_name_map = registry.EventRegistry.EVENT_NAME_MAP
    for event_cls in event_name_map.get(event_name, []):
      event_obj = event_cls(
          event_cls.well_known_session_id, mode="rw", token=token)
      event_obj.ProcessMessage(msg)
