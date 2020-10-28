#!/usr/bin/env python
# Lint as: python3
"""Tests for casing functions."""

from absl.testing import absltest

from grr_response_core.lib import casing


class SnakeToCamelTest(absltest.TestCase):

  def testSnakeToCamelWorksOnEmptyString(self):
    self.assertEqual("", casing.SnakeToCamel(""))

  def testSnakeToCamelWorksOnOneWordStrings(self):
    self.assertEqual("abcd", casing.SnakeToCamel("abcd"))
    self.assertEqual("a", casing.SnakeToCamel("a"))

  def testSnakeToCamelWorksOnRegularStrings(self):
    self.assertEqual("thisIsACamel", casing.SnakeToCamel("this_is_a_camel"))
    self.assertEqual("aCamelThisIs", casing.SnakeToCamel("a_camel_this_is"))
    self.assertEqual("aBCD", casing.SnakeToCamel("a_b_c_d"))

  def testSnakeToCamelWorksOnStringsWithUnderscoresOnly(self):
    self.assertEqual("", casing.SnakeToCamel("_"))
    self.assertEqual("", casing.SnakeToCamel("__"))
    self.assertEqual("", casing.SnakeToCamel("_________"))

  def testSnakeToCamelWorksOnStringsWithPrefixOrSuffixUnderscores(self):
    self.assertEqual("a", casing.SnakeToCamel("_a"))
    self.assertEqual("a", casing.SnakeToCamel("a_"))
    self.assertEqual("a", casing.SnakeToCamel("_a_"))
    self.assertEqual("a", casing.SnakeToCamel("___a___"))
    self.assertEqual("abcd", casing.SnakeToCamel("___abcd___"))
    self.assertEqual("aBCD", casing.SnakeToCamel("_a_b_c_d_"))
    self.assertEqual("aBCD", casing.SnakeToCamel("____a_b_c_d____"))
    self.assertEqual("aaBbCcDd", casing.SnakeToCamel("____aa_bb_cc_dd____"))
    self.assertEqual("aaaBbbCccDdd",
                     casing.SnakeToCamel("____aaa_bbb_ccc_ddd____"))

  def testSnakeToCamelWorksOnStringsWithMultipleUnderscoresBetweenWords(self):
    self.assertEqual("aBCD", casing.SnakeToCamel("a__b__c__d"))
    self.assertEqual("aBCD", casing.SnakeToCamel("a____b____c____d"))
    self.assertEqual("aBCD", casing.SnakeToCamel("___a___b___c___d___"))
    self.assertEqual("aaBbCcDd", casing.SnakeToCamel("___aa___bb___cc___dd___"))
    self.assertEqual("aaaBbbCccDdd",
                     casing.SnakeToCamel("___aaa___bbb___ccc___ddd___"))

  def testSnakeToCamelWorksOnStringsWithUppercaseLetters(self):
    self.assertEqual("a", casing.SnakeToCamel("A"))
    self.assertEqual("aaaaaa", casing.SnakeToCamel("Aaaaaa"))
    self.assertEqual("aaaaBbbbCccc", casing.SnakeToCamel("AaAa_bBbB_CcCc"))

  def testSnakeToCamelWorksOnStringsWithUnicodeCharacters(self):
    self.assertEqual("ąĆĘ", casing.SnakeToCamel("ą_ć_ę"))
    self.assertEqual("ąąąaĆććaĘęęa", casing.SnakeToCamel("ąąąa_ććća_ęęęa"))
    self.assertEqual("ąąąaĆććaĘęęa", casing.SnakeToCamel("ĄąĄA_ĆćĆa_ĘĘĘa"))


class CamelToSnakeTest(absltest.TestCase):

  def testCamelToSnakeWorksOnEmptyString(self):
    self.assertEqual("", casing.CamelToSnake(""))

  def testCamelToSnakeWorksOnOneWordStrings(self):
    self.assertEqual("abcd", casing.CamelToSnake("abcd"))
    self.assertEqual("a", casing.CamelToSnake("a"))

  def testCamelToSnakeWorksOnRegularStrings(self):
    self.assertEqual("this_is_a_snake", casing.CamelToSnake("thisIsASnake"))
    self.assertEqual("a_snake_this_is", casing.CamelToSnake("aSnakeThisIs"))
    self.assertEqual("a_b_c_d", casing.CamelToSnake("aBCD"))

  def testCamelToSnakeWorksOnStringsWithUppercaseLettersOnly(self):
    self.assertEqual("t_h_i_s_i_s_a_s_n_a_k_e",
                     casing.CamelToSnake("THISISASNAKE"))
    self.assertEqual("a_s_n_a_k_e_t_h_i_s_i_s",
                     casing.CamelToSnake("ASNAKETHISIS"))
    self.assertEqual("a_b_c_d", casing.CamelToSnake("ABCD"))
    self.assertEqual("a", casing.CamelToSnake("A"))

  def testCamelToSnakeWorksOnStringsWithUnicodeCharacters(self):
    self.assertEqual("ą_ć_ę", casing.CamelToSnake("ąĆĘ"))
    self.assertEqual("ąąąa_ććća_ęęęa", casing.CamelToSnake("ąąąaĆććaĘęęa"))
    self.assertEqual("ą_ą_ąa_ć_ć_ća_ę_ę_ęa",
                     casing.CamelToSnake("ĄĄĄaĆĆĆaĘĘĘa"))
    self.assertEqual("ą_ą_ą_ć_ć_ć_ę_ę_ę", casing.CamelToSnake("ĄĄĄĆĆĆĘĘĘ"))
    self.assertEqual("ą", casing.CamelToSnake("Ą"))

  def testCamelToSnakeWorksOnStringsWithUnderscores(self):
    self.assertEqual("a_b_c", casing.CamelToSnake("aB_c"))
    self.assertEqual("a_b", casing.CamelToSnake("a_b"))
    self.assertEqual("a_b", casing.CamelToSnake("A_b"))
    self.assertEqual("a_b", casing.CamelToSnake("a_B"))
    self.assertEqual("a_b", casing.CamelToSnake("A_B"))
    self.assertEqual("aa_bb", casing.CamelToSnake("_aaBb_"))
    self.assertEqual("a_bb_c", casing.CamelToSnake("___a_Bb__C___"))


if __name__ == "__main__":
  absltest.main()
