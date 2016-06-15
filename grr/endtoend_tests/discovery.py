#!/usr/bin/env python
"""End to end tests for lib.flows.general.discovery."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr


class TestClientInterrogateEndToEnd(base.AutomatedTest):
  """Tests the Interrogate flow on Windows."""
  platforms = ["Windows", "Linux", "Darwin"]
  flow = "Interrogate"

  attributes = [aff4_grr.VFSGRRClient.SchemaCls.CLIENT_INFO,
                aff4_grr.VFSGRRClient.SchemaCls.GRR_CONFIGURATION,
                aff4_grr.VFSGRRClient.SchemaCls.HOSTNAME,
                aff4_grr.VFSGRRClient.SchemaCls.INSTALL_DATE,
                aff4_grr.VFSGRRClient.SchemaCls.MAC_ADDRESS,
                aff4_grr.VFSGRRClient.SchemaCls.OS_RELEASE,
                aff4_grr.VFSGRRClient.SchemaCls.OS_VERSION,
                aff4_grr.VFSGRRClient.SchemaCls.SYSTEM,
                aff4_grr.VFSGRRClient.SchemaCls.USERNAMES]

  kb_attributes = ["hostname", "os", "os_major_version", "os_minor_version"]

  # TODO(user): time_zone, environ_path, and environ_temp are currently only
  # implemented for Windows, move to kb_attributes once available on other OSes.
  kb_win_attributes = ["time_zone", "environ_path", "environ_temp",
                       "environ_systemroot", "environ_windir",
                       "environ_programfiles", "environ_programfilesx86",
                       "environ_systemdrive", "environ_allusersprofile",
                       "environ_allusersappdata", "current_control_set",
                       "code_page"]

  # Intentionally excluded:
  # userdomain: too slow to collect, not in lightweight interrogate
  user_win_kb_attributes = ["sid", "userprofile", "appdata", "localappdata",
                            "internet_cache", "cookies", "recent", "personal",
                            "startup", "localappdata_low"]
  timeout = 240

  def setUp(self):
    super(TestClientInterrogateEndToEnd, self).setUp()
    data_store.DB.DeleteAttributes(self.client_id,
                                   [str(attribute)
                                    for attribute in self.attributes],
                                   sync=True,
                                   token=self.token)
    aff4.FACTORY.Flush()

    # When run on Windows this flow has 20 sub flows, so it takes some time to
    # complete.
    self.assertRaises(AssertionError, self.CheckFlow)

  def _IsCompleteWindowsUser(self, user):
    for attribute in self.user_win_kb_attributes:
      value = user.Get(attribute)
      if not value:
        return False
    return True

  def _CheckAttributes(self, attributes, fd):
    for attribute in attributes:
      value = fd.Get(attribute)
      self.assertTrue(value is not None, "Attribute %s is None." % attribute)
      self.assertTrue(str(value), "str(%s) is empty" % attribute)

  def CheckFlow(self):
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(fd, aff4_grr.VFSGRRClient)

    # Check KnowledgeBase was populated correctly
    kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    system = fd.Get(fd.Schema.SYSTEM)

    self._CheckAttributes(self.attributes, fd)
    self._CheckAttributes(self.kb_attributes, kb)
    if system == "Windows":
      self._CheckAttributes(self.kb_win_attributes, kb)

    self.assertTrue(kb.users)
    # Now check all the kb users have the right attributes
    complete_user = False
    for user in kb.users:
      value = user.Get("username")
      self.assertTrue(value is not None, "username is none for user: %s" % user)
      self.assertTrue(utils.SmartUnicode(value))

      if system == "Windows":
        # The amount of information collected per user can vary wildly on
        # Windows depending on the type of user, whether they have logged in,
        # whether they are local/domain etc.  We expect to find at least one
        # user with all of these fields filled out.
        complete_user = self._IsCompleteWindowsUser(user)
        if complete_user:
          return
      else:
        complete_user = user.Get("uid") is not None

    self.assertTrue(complete_user,
                    "No users with complete KB user attributes: %s" % kb.users)
