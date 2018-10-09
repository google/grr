#!/usr/bin/env python
from __future__ import unicode_literals

import mock

import unittest
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import all as all_parsers
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib


class FooParser(parser.SingleResponseParser):

  def ParseResponse(self, knowledge_base, response, path_type):
    raise NotImplementedError()


class BarParser(parser.SingleFileParser):

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    raise NotImplementedError()


class BazParser(parser.SingleFileParser):

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    raise NotImplementedError()


def SingleResponseParsers():
  return parsers.SINGLE_RESPONSE_PARSER_FACTORY.CreateAll()


def SingleFileParsers():
  return parsers.SINGLE_FILE_PARSER_FACTORY.CreateAll()


class WithAnnotationTestMixin(object):

  # TODO(hanuszczak): This could actually be moved to some base test class.
  def assertTypesEqual(self, instances, types):
    self.assertItemsEqual(map(type, instances), types)


class WithParserTest(WithAnnotationTestMixin, unittest.TestCase):

  def testSingleParser(self):

    @parser_test_lib.WithParser("Foo", FooParser)
    def AssertFooIsRegistered():
      self.assertTypesEqual(SingleResponseParsers(), [FooParser])

    # By default, no parsers should be registered.
    self.assertTypesEqual(SingleResponseParsers(), [])

    # This function is annotated and should register defined parsers.
    AssertFooIsRegistered()

    # Afterwards, the factory should not have any parser registered again.
    self.assertTypesEqual(SingleResponseParsers(), [])

  def testMultipleParsers(self):

    @parser_test_lib.WithParser("Foo", FooParser)
    @parser_test_lib.WithParser("Bar", BarParser)
    @parser_test_lib.WithParser("Baz", BazParser)
    def AssertTestParsersAreRegistered():
      self.assertTypesEqual(SingleResponseParsers(), [FooParser])
      self.assertTypesEqual(SingleFileParsers(), [BarParser, BazParser])

    # Again, by default no parsers should be registered.
    self.assertTypesEqual(SingleResponseParsers(), [])
    self.assertTypesEqual(SingleFileParsers(), [])

    # Every annotation should register corresponding parser.
    AssertTestParsersAreRegistered()

    # And again, all parsers should leave the clean state again.
    self.assertTypesEqual(SingleResponseParsers(), [])
    self.assertTypesEqual(SingleFileParsers(), [])


class WithAllParsersTest(WithAnnotationTestMixin, unittest.TestCase):

  def testWithCustomRegisterMethod(self):

    def Register():
      parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("Foo", FooParser)
      parsers.SINGLE_FILE_PARSER_FACTORY.Register("Bar", BarParser)
      parsers.SINGLE_FILE_PARSER_FACTORY.Register("Baz", BazParser)

    @parser_test_lib.WithAllParsers
    def AssertAllTestParsersAreRegistered():
      self.assertTypesEqual(SingleResponseParsers(), [FooParser])
      self.assertTypesEqual(SingleFileParsers(), [BarParser, BazParser])

    with mock.patch.object(all_parsers, "Register", Register):
      self.assertTypesEqual(SingleResponseParsers(), [])
      self.assertTypesEqual(SingleFileParsers(), [])

      AssertAllTestParsersAreRegistered()

      self.assertTypesEqual(SingleResponseParsers(), [])
      self.assertTypesEqual(SingleFileParsers(), [])


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
