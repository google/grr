#!/usr/bin/env python

from absl.testing import absltest

from grr.test_lib import skip


@skip.If(True, "All class test methods are skipped strictly")
class IfClassStrictTest(absltest.TestCase):

  def testFailure1(self):
    self.fail("This test should be skipped.")

  def testFailure2(self):
    self.fail("This test should be skipped.")


@skip.If(lambda: True, "All class test methods are skipped lazily")
class IfClassLazyTest(absltest.TestCase):

  def testFailure1(self):
    self.fail("This test should be skipped.")

  def testFailure2(self):
    self.fail("This test should be skipped.")


@skip.Unless(False, "All class test methods are skipped strictly")
class UnlessClassStrictTest(absltest.TestCase):

  def testFailure1(self):
    self.fail("This test should be skipped.")

  def testFailure2(self):
    self.fail("This test should be skipped.")


@skip.Unless(lambda: False, "All class test methods skipped lazily")
class UnlessClassLazyTest(absltest.TestCase):

  def testFailure1(self):
    self.fail("This test should be skipped.")

  def testFailure2(self):
    self.fail("This test should be skipped.")


class IfTest(absltest.TestCase):

  @skip.If(True, "Method is skipped strictly.")
  def testFailureStrict(self):
    self.fail("This test should be skipped.")

  @skip.If(lambda: True, "Method is skipped lazily.")
  def testFailureLazy(self):
    self.fail("This test should be skipped.")

  @skip.If(False, "Method should not be skipped.")
  def testSuccessStrict(self):
    pass

  @skip.If(lambda: False, "Method should not be skipped.")
  def testSuccessLazy(self):
    pass

  def testRaisesOnWrongTestType(self):
    with self.assertRaises(TypeError):
      skip.If(lambda: True, "Foo.")(42)


class UnlessTest(absltest.TestCase):

  @skip.Unless(False, "Method is skipped strictly.")
  def testFailureStrict(self):
    self.fail("This test should be skipped.")

  @skip.Unless(lambda: False, "Method is skipped lazily.")
  def testFailureLazy(self):
    self.fail("This test should be skipped.")

  @skip.Unless(True, "Method should not be skipped.")
  def testSuccessStrict(self):
    pass

  @skip.Unless(lambda: True, "Method should not be skipped.")
  def testSuccessLazy(self):
    pass

  def testRaisesOnWrongTestType(self):
    with self.assertRaises(TypeError):
      skip.Unless(lambda: True, "Foo.")(42)


if __name__ == "__main__":
  absltest.main()
