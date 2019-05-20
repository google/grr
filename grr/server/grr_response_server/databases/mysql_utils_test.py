#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server.databases import mysql_utils
from grr.test_lib import test_lib


class DocTest(test_lib.DocTest):
  module = mysql_utils


class PlaceholdersTest(absltest.TestCase):

  def testEmpty(self):
    self.assertEqual(mysql_utils.Placeholders(0), "()")

  def testOne(self):
    self.assertEqual(mysql_utils.Placeholders(1), "(%s)")

  def testMany(self):
    self.assertEqual(mysql_utils.Placeholders(4), "(%s, %s, %s, %s)")

  def testZeroValues(self):
    self.assertEqual(mysql_utils.Placeholders(3, 0), "")

  def testManyValues(self):
    self.assertEqual(
        mysql_utils.Placeholders(3, 2), "(%s, %s, %s), (%s, %s, %s)")


class NamedPlaceholdersTest(absltest.TestCase):

  def testEmpty(self):
    self.assertEqual(mysql_utils.NamedPlaceholders([]), "()")

  def testOne(self):
    self.assertEqual(mysql_utils.NamedPlaceholders(["foo"]), "(%(foo)s)")

  def testMany(self):
    self.assertEqual(
        mysql_utils.NamedPlaceholders(["bar", "baz", "foo"]),
        "(%(bar)s, %(baz)s, %(foo)s)")

  def testDictUsesKeys(self):
    self.assertIn(
        mysql_utils.NamedPlaceholders({
            "bar": 42,
            "baz": 42,
            "foo": 42
        }), ["(%(bar)s, %(baz)s, %(foo)s)"])

  def testSortsNames(self):
    self.assertEqual(
        mysql_utils.NamedPlaceholders(["bar", "foo", "baz"]),
        "(%(bar)s, %(baz)s, %(foo)s)")


class ColumnsTest(absltest.TestCase):

  def testEmpty(self):
    self.assertEqual(mysql_utils.Columns([]), "()")

  def testOne(self):
    self.assertEqual(mysql_utils.Columns(["foo"]), "(`foo`)")

  def testMany(self):
    self.assertEqual(
        mysql_utils.Columns(["bar", "baz", "foo"]), "(`bar`, `baz`, `foo`)")

  def testDictUsesKeys(self):
    self.assertIn(
        mysql_utils.Columns({
            "bar": 42,
            "baz": 42,
            "foo": 42
        }), ["(`bar`, `baz`, `foo`)"])

  def testSortsNames(self):
    self.assertEqual(
        mysql_utils.Columns(["bar", "foo", "baz"]), "(`bar`, `baz`, `foo`)")

  def testSortsRawNamesWithoutEscape(self):
    self.assertGreater("`", "_")
    self.assertEqual(mysql_utils.Columns(["a", "a_hash"]), "(`a`, `a_hash`)")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
