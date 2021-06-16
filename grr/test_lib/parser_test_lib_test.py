#!/usr/bin/env python

from typing import IO
from typing import Iterator
from unittest import mock

from absl.testing import absltest

from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import all as all_parsers
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import parser_test_lib


class FooParser(parsers.SingleResponseParser[None]):

  def ParseResponse(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      response: rdfvalue.RDFValue,
  ) -> Iterator[None]:
    raise NotImplementedError()


class BarParser(parsers.SingleFileParser[None]):

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[None]:
    raise NotImplementedError()


class BazParser(parsers.SingleFileParser[None]):

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[None]:
    raise NotImplementedError()


def SingleResponseParsers():
  return parsers.SINGLE_RESPONSE_PARSER_FACTORY.CreateAll()


def SingleFileParsers():
  return parsers.SINGLE_FILE_PARSER_FACTORY.CreateAll()


class WithAnnotationTestMixin(object):

  # TODO(hanuszczak): This could actually be moved to some base test class.
  def assertTypesEqual(self, instances, types):
    self.assertCountEqual(map(type, instances), types)


class WithParserTest(WithAnnotationTestMixin, absltest.TestCase):

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


class WithAllParsersTest(WithAnnotationTestMixin, absltest.TestCase):

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
  absltest.main()
