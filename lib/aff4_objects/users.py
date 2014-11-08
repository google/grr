#!/usr/bin/env python
"""AFF4 object representing grr users."""


import crypt
import random
import string
import time

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.proto import flows_pb2
from grr.proto import jobs_pb2


class GlobalNotification(rdfvalue.RDFProtoStruct):
  """Global notification shown to all the users of GRR."""

  protobuf = jobs_pb2.GlobalNotification

  def __init__(self, *args, **kwargs):
    super(GlobalNotification, self).__init__(*args, **kwargs)

    if not self.duration:
      self.duration = rdfvalue.Duration("2w")

    if not self.show_from:
      self.show_from = rdfvalue.RDFDatetime().Now()

  @property
  def hash(self):
    """Having hash property makes things easier in Django templates."""
    return hash(self)

  @property
  def type_name(self):
    return self.Type.reverse_enum[self.type]


class GlobalNotificationSet(rdfvalue.RDFProtoStruct):
  """A set of global notifications: one notification per notification's type."""

  protobuf = jobs_pb2.GlobalNotificationSet

  def AddNotification(self, new_notification):
    """Adds new notification to the set.

    There can be only one notification of particular type (info, warning,
    error) in the set. Notifications are guaranteed to be stored in the
    order of their priority.

    Args:
      new_notification: New notification to add.
    """
    current_list = [notification for notification in self.notifications
                    if notification.type != new_notification.type]
    current_list.append(new_notification)
    current_list = sorted(current_list, key=lambda x: x.type)
    self.notifications = current_list

  def __iter__(self):
    for notification in self.notifications:
      yield notification

  def __contains__(self, notification):
    return notification in self.notifications


class GlobalNotificationStorage(aff4.AFF4Object):
  """Object that stores GRR's GlobalNotifications."""

  DEFAULT_PATH = rdfvalue.RDFURN("aff4:/config/global_notifications")

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for GlobalNotificationsManager."""

    NOTIFICATIONS = aff4.Attribute(
        "aff4:global_notification_storage/notifications", GlobalNotificationSet,
        "List of currently active notifications", versioned=False)

  def AddNotification(self, new_notification):
    """Adds new notification to the set."""
    current_set = self.GetNotifications()
    current_set.AddNotification(new_notification)
    self.Set(self.Schema.NOTIFICATIONS, current_set)

  def GetNotifications(self):
    return self.Get(self.Schema.NOTIFICATIONS, default=GlobalNotificationSet())


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

  # URN of the index for labels for users.
  labels_index_urn = rdfvalue.RDFURN("aff4:/index/labels/users")

  SYSTEM_USERS = set(["GRRWorker", "GRREnroller", "GRRCron", "test"])

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

    SHOWN_GLOBAL_NOTIFICATIONS = aff4.Attribute(
        "aff4:global_notification/timestamp_list", GlobalNotificationSet,
        "Global notifications shown to this user.",
        default=GlobalNotificationSet(), versioned=False)

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

  def GetPendingGlobalNotifications(self):
    storage = aff4.FACTORY.Create(GlobalNotificationStorage.DEFAULT_PATH,
                                  aff4_type="GlobalNotificationStorage",
                                  mode="r", token=self.token)
    current_notifications = storage.GetNotifications()

    shown_notifications = self.Get(self.Schema.SHOWN_GLOBAL_NOTIFICATIONS,
                                   default=GlobalNotificationSet())

    result = []
    for notification in current_notifications:
      if notification in shown_notifications:
        continue

      current_time = rdfvalue.RDFDatetime().Now()
      if (notification.show_from + notification.duration >= current_time and
          current_time >= notification.show_from):
        result.append(notification)

    return result

  def MarkGlobalNotificationAsShown(self, notification):
    shown_notifications = self.Get(self.Schema.SHOWN_GLOBAL_NOTIFICATIONS)
    shown_notifications.AddNotification(notification)
    self.Set(self.Schema.SHOWN_GLOBAL_NOTIFICATIONS, shown_notifications)
