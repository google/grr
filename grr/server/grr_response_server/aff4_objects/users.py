#!/usr/bin/env python
"""AFF4 object representing grr users."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import itertools
import time

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import user_pb2
from grr_response_server import aff4


class Error(Exception):
  pass


class UniqueKeyError(Error):
  pass


class CryptedPassword(rdfvalue.RDFString):
  """Encoded crypted password."""

  def _MakeTemplate(self, pwhash, salt):
    return "%s$%s$%s" % ("sha256", salt, pwhash)

  def safe_str_cmp(self, a, b):
    if len(a) != len(b):
      return False
    rv = 0
    for x, y in itertools.izip(a, b):
      rv |= ord(x) ^ ord(y)
    return rv == 0

  def _CalculateHash(self, password, salt):
    pwhash = hashlib.sha256(salt + password + salt).hexdigest()
    return self._MakeTemplate(pwhash, salt)

  def SetPassword(self, password, salt=None):
    if salt is None:
      salt = "%08x" % random.UInt32()

    self._value = self._CalculateHash(password, salt)
    return self

  def _CheckLegacyPassword(self, password):
    """Check password with legacy crypt based method."""
    # This import will fail on Windows.
    import crypt  # pylint: disable=g-import-not-at-top
    salt = self._value[:2]
    return crypt.crypt(password, salt) == self._value

  def CheckPassword(self, password):
    # Old, legacy crypt based password.
    if not self._value.startswith("sha256$"):
      return self._CheckLegacyPassword(password)

    salt = self._value.split("$")[1]
    return self.safe_str_cmp(self._value, self._CalculateHash(password, salt))


class GUISettings(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.GUISettings


class GRRUser(aff4.AFF4Object):
  """An AFF4 object modeling a GRR User."""

  SYSTEM_USERS = set([
      "GRRWorker", "GRRCron", "GRRSystem", "GRRFrontEnd", "GRRConsole",
      "GRRArtifactRegistry", "GRRStatsStore", "GRREndToEndTest", "GRR",
      "GRRBenchmarkTest"
  ])

  _SYSTEM_USERS_LOWERCASE = set(username.lower() for username in SYSTEM_USERS)

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for GRRUser."""
    PENDING_NOTIFICATIONS = aff4.Attribute(
        "aff4:notification/pending",
        rdf_flows.NotificationList,
        "The notifications pending for the user.",
        default=rdf_flows.NotificationList(),
        versioned=False)

    SHOWN_NOTIFICATIONS = aff4.Attribute(
        "aff4:notifications/shown",
        rdf_flows.NotificationList,
        "Notifications already shown to the user.",
        default=rdf_flows.NotificationList(),
        versioned=False)

    GUI_SETTINGS = aff4.Attribute(
        "aff4:gui/settings", GUISettings, "GUI Settings", default=GUISettings())

    PASSWORD = aff4.Attribute("aff4:user/password", CryptedPassword,
                              "Encrypted Password for the user")

  @staticmethod
  def IsValidUsername(username):
    return username.lower() not in GRRUser._SYSTEM_USERS_LOWERCASE

  def Notify(self, message_type, subject, msg, source):
    """Send an AFF4-based notification to the user in the UI.

    Args:
      message_type: One of aff4_grr.Notification.notification_types e.g.
        "ViewObject", "HostInformation", "GrantAccess" or
        the same with an added ":[new-style notification type] suffix, e.g.
        "ViewObject:TYPE_CLIENT_INTERROGATED".
      subject: The subject to use, normally a URN.
      msg: The message to display.
      source: The class doing the notification.

    Raises:
      TypeError: On invalid message_type.
    """
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    if pending is None:
      pending = self.Schema.PENDING_NOTIFICATIONS()

    # This is a legacy code that should go away after RELDB migration is done.
    # RELDB notifications have an explicitly stored notification type (that
    # is then mapped to ApiNotification.notification_type). However, legacy
    # AFF4-based data model notification types are different from the newly
    # introduced ones (new types are very concrete, i.e. "vfs file download
    # completed", legacy ones are very generic, i.e. "ViewObject").
    #
    # In order to temporarily keep the legacy code working and keep the tests
    # passing, we "pack" new-style notification type into an old style
    # "message_type". I.e. what was ViewObject before, will become
    # ViewObject:TYPE_CLIENT_INTERROGATED.
    #
    # Notifications without the ":[notification type]" suffix are also still
    # supported for backwards compatibility reasonds. They will be treated
    # as notifications with an unknown new-style type.
    if message_type.split(
        ":", 2)[0] not in rdf_flows.Notification.notification_types:
      raise TypeError("Invalid notification type %s" % message_type)

    pending.Append(
        type=message_type,
        subject=subject,
        message=msg,
        source=source,
        timestamp=int(time.time() * 1e6))

    # Limit the notification to 50, expiring older notifications.
    while len(pending) > 50:
      pending.Pop(0)

    self.Set(self.Schema.PENDING_NOTIFICATIONS, pending)

  def DeletePendingNotification(self, timestamp):
    """Deletes the pending notification with the given timestamp.

    Args:
      timestamp: The timestamp of the notification. Assumed to be unique.

    Raises:
      UniqueKeyError: Raised if multiple notifications have the timestamp.
    """
    shown_notifications = self.Get(self.Schema.SHOWN_NOTIFICATIONS)
    if not shown_notifications:
      shown_notifications = self.Schema.SHOWN_NOTIFICATIONS()

    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    if not pending:
      return

    # Remove all notifications with the given timestamp from pending
    # and add them to the shown notifications.
    delete_count = 0
    for idx in reversed(range(0, len(pending))):
      if pending[idx].timestamp == timestamp:
        shown_notifications.Append(pending[idx])
        pending.Pop(idx)
        delete_count += 1

    if delete_count > 1:
      raise UniqueKeyError("Multiple notifications at %s" % timestamp)

    self.Set(self.Schema.PENDING_NOTIFICATIONS, pending)
    self.Set(self.Schema.SHOWN_NOTIFICATIONS, shown_notifications)

  def ShowNotifications(self, reset=True):
    """A generator of current notifications."""
    shown_notifications = self.Schema.SHOWN_NOTIFICATIONS()

    # Pending notifications first
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS, [])
    for notification in pending:
      shown_notifications.Append(notification)

    notifications = self.Get(self.Schema.SHOWN_NOTIFICATIONS, [])
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
    labels = [l.name for l in self.GetLabels()]
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
