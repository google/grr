#!/usr/bin/env python
"""Message handlers."""


class MessageHandler(object):
  """The base class for all message handlers."""

  handler_name = ""

  def __init__(self, token=None):
    # TODO(amoser): Get rid of the token once well known flows don't
    # write to aff4 anymore.
    self.token = token

  def ProcessMessages(self, msgs):
    """This is where messages get processed.

    Override in derived classes.

    Args:
      msgs: The GrrMessages sent by the client.
    """
