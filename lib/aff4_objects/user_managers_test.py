#!/usr/bin/env python


from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import user_managers


class CheckAccessHelperTest(test_lib.GRRBaseTest):
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

  def testUserManagement(self):

    config_lib.CONFIG.Set("Users.authorization", "")
    um = user_managers.ConfigBasedUserManager()

    # Make sure we start from a clean state.
    self.assertEquals(len(um._user_cache), 0)

    um.AddUser("admin", password="admin", admin=True)

    # There should be one user now.
    self.assertEquals(len(um._user_cache), 1)

    # Make sure we can authenticate.
    class MyAuthObj(object):
      pass
    auth_obj = MyAuthObj()
    auth_obj.user_provided_hash = "admin"
    self.assertTrue(um.CheckUserAuth("admin", auth_obj))

    # Change the password for the existing user.
    um.AddUser("admin", password="new_pwd", admin=True)

    # There should still only be one user.
    self.assertEquals(len(um._user_cache), 1)

    # Check old password, should not work.
    self.assertFalse(um.CheckUserAuth("admin", auth_obj))

    # Try the new password.
    auth_obj.user_provided_hash = "new_pwd"
    self.assertTrue(um.CheckUserAuth("admin", auth_obj))

    # Now add a second user but do not provide a password.
    self.assertRaises(RuntimeError, um.AddUser, ("johndoe"))

    # Ok, lets provide one.
    um.AddUser("johndoe", password="jane", labels=["label1", "label2"],
               admin=True)

    # There should be two now.
    self.assertEquals(len(um._user_cache), 2)

    # Make sure the admin label got added.
    self.assertEquals(um._user_cache["johndoe"]["labels"],
                      ["admin", "label1", "label2"])
