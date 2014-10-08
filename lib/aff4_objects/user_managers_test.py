#!/usr/bin/env python


from grr.lib import access_control
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import user_managers


class GRRUserTest(test_lib.AFF4ObjectTest):

  def testUserPasswords(self):
    with aff4.FACTORY.Create("aff4:/users/test", "GRRUser",
                             token=self.token) as user:
      user.SetPassword("hello")

    user = aff4.FACTORY.Open(user.urn, token=self.token)

    self.assertFalse(user.CheckPassword("goodbye"))
    self.assertTrue(user.CheckPassword("hello"))

  def testLabels(self):
    with aff4.FACTORY.Create("aff4:/users/test", "GRRUser",
                             token=self.token) as user:
      user.SetLabels("hello", "world", owner="GRR")

    user = aff4.FACTORY.Open(user.urn, token=self.token)
    self.assertListEqual(["hello", "world"], user.GetLabelsNames())


class CheckAccessHelperTest(test_lib.AFF4ObjectTest):

  def setUp(self):
    super(CheckAccessHelperTest, self).setUp()
    self.helper = user_managers.CheckAccessHelper("test")
    self.subject = rdfvalue.RDFURN("aff4:/some/path")

  def testReturnsFalseByDefault(self):
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testReturnsFalseOnFailedMatch(self):
    self.helper.Allow("aff4:/some/otherpath")
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testReturnsTrueOnMatch(self):
    self.helper.Allow("aff4:/some/path")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testReturnsTrueIfOneMatchFails1(self):
    self.helper.Allow("aff4:/some/otherpath")
    self.helper.Allow("aff4:/some/path")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testReturnsTrueIfOneMatchFails2(self):
    self.helper.Allow("aff4:/some/path")
    self.helper.Allow("aff4:/some/otherpath")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchFormatIsUsedByDefault1(self):
    self.helper.Allow("aff4:/some/*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchFormatIsUsedByDefault2(self):
    self.helper.Allow("aff4:/some*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchPatternCorrectlyMatchesFilesBelowDirectory(self):
    self.helper.Allow("aff4:/some/*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess,
                      rdfvalue.RDFURN("aff4:/some"), self.token)

  def testCustomCheckWorksCorrectly(self):
    def CustomCheck(unused_subject, unused_token):
      return True

    self.helper.Allow("aff4:/some/path", CustomCheck)
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testCustomCheckFailsCorrectly(self):
    def CustomCheck(unused_subject, unused_token):
      raise access_control.UnauthorizedAccess("Problem")

    self.helper.Allow("aff4:/some/path", CustomCheck)
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testCustomCheckAcceptsAdditionalArguments(self):
    def CustomCheck(subject, unused_token, another_subject):
      if subject == another_subject:
        return True
      else:
        raise access_control.UnauthorizedAccess("Problem")

    self.helper.Allow("aff4:/*", CustomCheck, self.subject)
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess,
                      rdfvalue.RDFURN("aff4:/some/other/path"),
                      self.token)
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def Ok(self, subject, access="r"):
    self.assertTrue(
        self.access_manager.CheckDataStoreAccess(self.token, [subject], access))

  def NotOk(self, subject, access="r"):
    self.assertRaises(
        access_control.UnauthorizedAccess,
        self.access_manager.CheckDataStoreAccess,
        self.token, [subject], access)

  def testReadSomePaths(self):
    """Tests some real world paths."""
    self.access_manager = user_managers.FullAccessControlManager()
    access = "r"

    self.Ok("aff4:/", access)
    self.Ok("aff4:/users", access)
    self.NotOk("aff4:/users/randomuser", access)

    self.Ok("aff4:/blobs", access)
    self.Ok("aff4:/blobs/12345678", access)

    self.Ok("aff4:/FP", access)
    self.Ok("aff4:/FP/12345678", access)

    self.Ok("aff4:/files", access)
    self.Ok("aff4:/files/12345678", access)

    self.Ok("aff4:/ACL", access)
    self.Ok("aff4:/ACL/randomuser", access)

    self.Ok("aff4:/stats", access)
    self.Ok("aff4:/stats/FileStoreStats", access)

    self.Ok("aff4:/config", access)
    self.Ok("aff4:/config/drivers", access)
    self.Ok("aff4:/config/drivers/windows/memory/winpmem.amd64.sys", access)

    self.Ok("aff4:/flows", access)
    self.Ok("aff4:/flows/W:12345678", access)

    self.Ok("aff4:/hunts", access)
    self.Ok("aff4:/hunts/W:12345678/C.1234567890123456", access)
    self.Ok("aff4:/hunts/W:12345678/C.1234567890123456/W:AAAAAAAA", access)

    self.Ok("aff4:/cron", access)
    self.Ok("aff4:/cron/OSBreakDown", access)

    self.Ok("aff4:/crashes", access)
    self.Ok("aff4:/crashes/Stream", access)

    self.Ok("aff4:/audit", access)
    self.Ok("aff4:/audit/log", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows/W:12345678", access)

    self.Ok("aff4:/tmp", access)
    self.Ok("aff4:/tmp/C8FAFC0F", access)

  def testQuerySomePaths(self):
    """Tests some real world paths."""
    self.access_manager = user_managers.FullAccessControlManager()
    access = "rq"

    self.NotOk("aff4:/", access)
    self.NotOk("aff4:/users", access)
    self.NotOk("aff4:/users/randomuser", access)

    self.NotOk("aff4:/blobs", access)

    self.NotOk("aff4:/FP", access)

    self.NotOk("aff4:/files", access)
    self.Ok("aff4:/files/hash/generic/sha256/" + "a" * 64, access)

    self.Ok("aff4:/ACL", access)
    self.Ok("aff4:/ACL/randomuser", access)

    self.NotOk("aff4:/stats", access)

    self.Ok("aff4:/config", access)
    self.Ok("aff4:/config/drivers", access)
    self.Ok("aff4:/config/drivers/windows/memory/winpmem.amd64.sys", access)

    self.NotOk("aff4:/flows", access)
    self.Ok("aff4:/flows/W:12345678", access)

    self.Ok("aff4:/hunts", access)
    self.Ok("aff4:/hunts/W:12345678/C.1234567890123456", access)
    self.Ok("aff4:/hunts/W:12345678/C.1234567890123456/W:AAAAAAAA", access)

    self.Ok("aff4:/cron", access)
    self.Ok("aff4:/cron/OSBreakDown", access)

    self.NotOk("aff4:/crashes", access)

    self.NotOk("aff4:/audit", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows", access)

    self.NotOk("aff4:/tmp", access)
