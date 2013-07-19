#!/usr/bin/env python


from grr.lib import access_control
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
