#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""AFF4 object representing grr users."""


import crypt
import random
import string
import time

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class CryptedPassword(rdfvalue.RDFString):
  """Encoded crypted password."""

  def _CalculateHash(self, password, salt=None):
    # Note: As of python 3.3. there is a function to do this, but we do our
    # own for backwards compatibility.
    valid_salt_chars = string.ascii_letters + string.digits + "./"
    if salt is None:
      salt = "".join(random.choice(valid_salt_chars) for i in range(2))

    return crypt.crypt(password, salt)

  def SetPassword(self, password, salt=None):
    self._value = self._CalculateHash(password, salt=salt)
    return self

  def CheckPassword(self, password):
    salt = self._value[:2]
    return self._CalculateHash(password, salt=salt) == self._value


class GUISettings(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GUISettings


class GRRUser(aff4.AFF4Object):
  """An AFF4 object modeling a GRR User."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for GRRUser."""
    PENDING_NOTIFICATIONS = aff4.Attribute(
        "aff4:notification/pending", rdfvalue.NotificationList,
        "The notifications pending for the user.", default="",
        versioned=False)

    SHOWN_NOTIFICATIONS = aff4.Attribute(
        "aff4:notifications/shown", rdfvalue.NotificationList,
        "Notifications already shown to the user.", default="",
        versioned=False)

    GUI_SETTINGS = aff4.Attribute(
        "aff4:gui/settings", rdfvalue.GUISettings,
        "GUI Settings", default="")

    PASSWORD = aff4.Attribute(
        "aff4:user/password", CryptedPassword,
        "Encrypted Password for the user")

  def Notify(self, message_type, subject, msg, source):
    """Send a notification to the user in the UI.

    Args:
      message_type: One of aff4_grr.Notification.notification_types e.g.
        "ViewObject", "HostInformation", "GrantAccess".
      subject: The subject to use, normally a URN.
      msg: The message to display.
      source: The class doing the notification.

    Raises:
      TypeError: On invalid message_type.
    """
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    if pending is None:
      pending = self.Schema.PENDING_NOTIFICATIONS()

    if message_type not in rdfvalue.Notification.notification_types:
      raise TypeError("Invalid notification type %s" % message_type)

    pending.Append(type=message_type, subject=subject, message=msg,
                   source=source, timestamp=long(time.time() * 1e6))

    # Limit the notification to 50, expiring older notifications.
    while len(pending) > 50:
      pending.Pop(0)

    self.Set(self.Schema.PENDING_NOTIFICATIONS, pending)

  def ShowNotifications(self, reset=True):
    """A generator of current notifications."""
    shown_notifications = self.Schema.SHOWN_NOTIFICATIONS()

    # Pending notifications first
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    for notification in pending:
      shown_notifications.Append(notification)

    notifications = self.Get(self.Schema.SHOWN_NOTIFICATIONS)
    for notification in notifications:
      shown_notifications.Append(notification)

    # Shall we reset the pending notification state?
    if reset:
      self.Set(shown_notifications)
      self.Set(self.Schema.PENDING_NOTIFICATIONS())
      self.Flush()

    return shown_notifications

  def Describe(self):
    """Return a description of this user."""
    result = ["\nUsername: %s" % self.urn.Basename()]
    fd = aff4.FACTORY.Open(self.urn.Add("labels"), token=self.token)
    labels = [str(x) for x in fd.Get(fd.Schema.LABEL, [])]
    result.append("Labels: %s" % ",".join(labels))

    if self.Get(self.Schema.PASSWORD) is None:
      result.append("Password: not set")
    else:
      result.append("Password: set")

    return "\n".join(result)

  def SetPassword(self, password):
    self.Set(self.Schema.PASSWORD().SetPassword(password))

  def CheckPassword(self, password):
    password_obj = self.Get(self.Schema.PASSWORD)
    return password_obj and password_obj.CheckPassword(password)

  def SetLabels(self, *labels):
    with aff4.FACTORY.Create(self.urn.Add("labels"), "AFF4Object",
                             token=self.token) as fd:
      new_labels = fd.Schema.LABEL()
      for label in labels:
        new_labels.Append(label)

      fd.Set(new_labels)

  def GetLabels(self):
    fd = aff4.FACTORY.Open(self.urn.Add("labels"), token=self.token)
    return [str(x) for x in fd.Get(fd.Schema.LABEL, [])]
