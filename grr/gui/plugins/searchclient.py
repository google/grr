#!/usr/bin/env python
"""This plugin renders the client search page."""

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import users as aff4_users


class SetGlobalNotification(flow.GRRGlobalFlow):
  """Updates user's global notification timestamp."""

  # This is an administrative flow.
  category = "/Administrative/"

  # Only admins can run this flow.
  AUTHORIZED_LABELS = ["admin"]

  # This flow is a SUID flow.
  ACL_ENFORCED = False

  args_type = aff4_users.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=self.token) as storage:
      storage.AddNotification(self.args)


class FilestoreTable(renderers.TableRenderer):
  """Render filestore hits."""

  def __init__(self, **kwargs):
    super(FilestoreTable, self).__init__(**kwargs)

    self.AddColumn(semantic.RDFValueColumn("Client"))
    self.AddColumn(semantic.RDFValueColumn("File"))
    self.AddColumn(semantic.RDFValueColumn("Timestamp"))

  def BuildTable(self, start, end, request):
    query_string = request.REQ.get("q", "")
    if not query_string:
      raise RuntimeError("A query string must be provided.")

    hash_urn = rdfvalue.RDFURN("aff4:/files/hash/generic/sha256/").Add(
        query_string)

    for i, (_, value, timestamp) in enumerate(
        data_store.DB.ResolvePrefix(
            hash_urn, "index:", token=request.token)):

      if i > end:
        break

      self.AddRow(
          row_index=i,
          File=value,
          Client=aff4_grr.VFSGRRClient.ClientURNFromURN(value),
          Timestamp=rdfvalue.RDFDatetime(timestamp))

    # We only display 50 entries.
    return False
