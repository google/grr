#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from future.builtins import map

import mock

from grr_response_core.lib import factory
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr.test_lib import test_lib


class ArtifactParserFactoryTest(absltest.TestCase):

  @mock.patch.object(parsers, "SINGLE_RESPONSE_PARSER_FACTORY",
                     factory.Factory(parser.SingleResponseParser))
  def testSingleResponseParsers(self):

    class FooParser(parser.SingleResponseParser):

      supported_artifacts = ["Quux", "Norf"]

      def ParseResponse(self, knowledge_base, response, path_type):
        raise NotImplementedError()

    class BarParser(parser.SingleResponseParser):

      supported_artifacts = ["Norf", "Thud"]

      def ParseResponse(self, knowledge_base, response, path_type):
        raise NotImplementedError()

    class BazParser(parser.SingleResponseParser):

      supported_artifacts = ["Thud", "Quux"]

      def ParseResponse(self, knowledge_base, response, path_type):
        raise NotImplementedError()

    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("Foo", FooParser)
    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("Bar", BarParser)
    parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register("Baz", BazParser)

    quux_factory = parsers.ArtifactParserFactory("Quux")
    quux_parsers = quux_factory.SingleResponseParsers()
    self.assertCountEqual(map(type, quux_parsers), [FooParser, BazParser])

    norf_factory = parsers.ArtifactParserFactory("Norf")
    norf_parsers = norf_factory.SingleResponseParsers()
    self.assertCountEqual(map(type, norf_parsers), [FooParser, BarParser])

    thud_factory = parsers.ArtifactParserFactory("Thud")
    thud_parsers = thud_factory.SingleResponseParsers()
    self.assertCountEqual(map(type, thud_parsers), [BarParser, BazParser])

  @mock.patch.object(parsers, "MULTI_RESPONSE_PARSER_FACTORY",
                     factory.Factory(parser.MultiResponseParser))
  def testMultiResponseParsers(self):

    class FooParser(parser.MultiResponseParser):

      supported_artifacts = ["Foo"]

      def ParseResponses(self, knowledge_base, responses):
        raise NotImplementedError()

    class BarParser(parser.MultiResponseParser):

      supported_artifacts = ["Bar"]

      def ParseResponses(self, knowledge_base, responses):
        raise NotImplementedError()

    parsers.MULTI_RESPONSE_PARSER_FACTORY.Register("Foo", FooParser)
    parsers.MULTI_RESPONSE_PARSER_FACTORY.Register("Bar", BarParser)

    foo_factory = parsers.ArtifactParserFactory("Foo")
    foo_parsers = foo_factory.MultiResponseParsers()
    self.assertCountEqual(map(type, foo_parsers), [FooParser])

    bar_factory = parsers.ArtifactParserFactory("Bar")
    bar_parsers = bar_factory.MultiResponseParsers()
    self.assertCountEqual(map(type, bar_parsers), [BarParser])

  @mock.patch.object(parsers, "SINGLE_FILE_PARSER_FACTORY",
                     factory.Factory(parser.SingleFileParser))
  def testSingleFileParsers(self):

    class FooParser(parser.SingleFileParser):

      supported_artifacts = ["Bar"]

      def ParseFile(self, knowledge_base, pathspec, filedesc):
        raise NotImplementedError()

    parsers.SINGLE_FILE_PARSER_FACTORY.Register("Foo", FooParser)

    bar_factory = parsers.ArtifactParserFactory("Bar")
    bar_parsers = bar_factory.SingleFileParsers()
    self.assertCountEqual(map(type, bar_parsers), [FooParser])

    baz_factory = parsers.ArtifactParserFactory("Baz")
    baz_parsers = baz_factory.SingleFileParsers()
    self.assertCountEqual(map(type, baz_parsers), [])

  @mock.patch.object(parsers, "MULTI_FILE_PARSER_FACTORY",
                     factory.Factory(parser.MultiFileParser))
  def testMultiFileParsers(self):

    class FooParser(parser.MultiFileParser):

      supported_artifacts = ["Quux", "Norf"]

      def ParseFiles(self, knowledge_base, pathspecs, filedescs):
        raise NotImplementedError()

    class BarParser(parser.MultiFileParser):

      supported_artifacts = ["Quux", "Thud"]

      def ParseFiles(self, knowledge_base, pathspecs, filedescs):
        raise NotImplementedError()

    parsers.MULTI_FILE_PARSER_FACTORY.Register("Foo", FooParser)
    parsers.MULTI_FILE_PARSER_FACTORY.Register("Bar", BarParser)

    quux_factory = parsers.ArtifactParserFactory("Quux")
    quux_parsers = quux_factory.MultiFileParsers()
    self.assertCountEqual(map(type, quux_parsers), [FooParser, BarParser])

    norf_factory = parsers.ArtifactParserFactory("Norf")
    norf_parsers = norf_factory.MultiFileParsers()
    self.assertCountEqual(map(type, norf_parsers), [FooParser])

    thud_factory = parsers.ArtifactParserFactory("Thud")
    thud_parsers = thud_factory.MultiFileParsers()
    self.assertCountEqual(map(type, thud_parsers), [BarParser])


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
