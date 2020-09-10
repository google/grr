# Lint as: python3
"""Tests for casing functions."""

from grr_response_core.lib import casing

from grr.test_lib import test_lib


class CasingTests(test_lib.GRRBaseTest):
  def testSnakeToCamelWorksOnEmptyString(self):
    self.assertEqual("", casing.SnakeToCamel(""))

  def testSnakeToCamelWorksOnOneWordStrings(self):
    self.assertEqual("abcd", casing.SnakeToCamel("abcd"))
    self.assertEqual("a", casing.SnakeToCamel("a"))

  def testSnakeToCamelWorksOnRegularStrings(self):
    self.assertEqual("thisIsACamel", casing.SnakeToCamel("this_is_a_camel"))
    self.assertEqual("aCamelThisIs", casing.SnakeToCamel("a_camel_this_is"))
    self.assertEqual("aBCD", casing.SnakeToCamel("a_b_c_d"))

  def testCamelToSnakeWorksOnEmptyString(self):
    self.assertEqual("", casing.CamelToSnake(""))

  def testCamelToSnakeWorksOnOneWordStrings(self):
    self.assertEqual("abcd", casing.CamelToSnake("abcd"))
    self.assertEqual("a", casing.CamelToSnake("a"))

  def testCamelToSnakeWorksOnRegularStrings(self):
    self.assertEqual("this_is_a_snake", casing.CamelToSnake("thisIsASnake"))
    self.assertEqual("a_snake_this_is", casing.CamelToSnake("aSnakeThisIs"))
    self.assertEqual("a_b_c_d", casing.CamelToSnake("aBCD"))
