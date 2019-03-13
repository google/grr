#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import io
import os
import platform
import re
import subprocess
import unittest

from absl import app
from absl.testing import absltest

from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.util import filesystem
from grr_response_core.lib.util import temp
from grr.test_lib import filesystem_test_lib
from grr.test_lib import test_lib


class RegexMatcherTest(absltest.TestCase):

  @staticmethod
  def _RegexMatcher(regex):
    return conditions.RegexMatcher(re.compile(regex))

  def testMatchLiteral(self):
    matcher = self._RegexMatcher(b"foo")

    span = matcher.Match(b"foobar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 3)

    span = matcher.Match(b"foobarfoobar", 2)
    self.assertTrue(span)
    self.assertEqual(span.begin, 6)
    self.assertEqual(span.end, 9)

  def testNoMatchLiteral(self):
    matcher = self._RegexMatcher(b"baz")

    span = matcher.Match(b"foobar", 0)
    self.assertFalse(span)

    span = matcher.Match(b"foobazbar", 5)
    self.assertFalse(span)

  def testMatchWildcard(self):
    matcher = self._RegexMatcher(b"foo.*bar")

    span = matcher.Match(b"foobar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 6)

    span = matcher.Match(b"quuxfoobazbarnorf", 2)
    self.assertTrue(span)
    self.assertEqual(span.begin, 4)
    self.assertEqual(span.end, 13)

  def testMatchRepeated(self):
    matcher = self._RegexMatcher(b"qu+x")

    span = matcher.Match(b"quuuux", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 6)

    span = matcher.Match(b"qx", 0)
    self.assertFalse(span)

    span = matcher.Match(b"qvvvvx", 0)
    self.assertFalse(span)


class LiteralMatcherTest(absltest.TestCase):

  def testMatchLiteral(self):
    matcher = conditions.LiteralMatcher(b"bar")

    span = matcher.Match(b"foobarbaz", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 3)
    self.assertEqual(span.end, 6)

    span = matcher.Match(b"barbarbar", 0)
    self.assertTrue(span)
    self.assertEqual(span.begin, 0)
    self.assertEqual(span.end, 3)

    span = matcher.Match(b"barbarbar", 4)
    self.assertTrue(span)
    self.assertEqual(span.begin, 6)
    self.assertEqual(span.end, 9)

  def testNoMatchLiteral(self):
    matcher = conditions.LiteralMatcher(b"norf")

    span = matcher.Match(b"quux", 0)
    self.assertFalse(span)

    span = matcher.Match(b"norf", 2)
    self.assertFalse(span)

    span = matcher.Match(b"quuxnorf", 5)
    self.assertFalse(span)


class ConditionTestMixin(object):

  def setUp(self):
    super(ConditionTestMixin, self).setUp()
    self.temp_filepath = temp.TempFilePath()
    self.addCleanup(lambda: os.remove(self.temp_filepath))


@unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
class MetadataConditionTestMixin(ConditionTestMixin):

  def Stat(self):
    return filesystem.Stat.FromPath(self.temp_filepath, follow_symlink=False)

  def Touch(self, mode, date):
    self.assertIn(mode, ["-m", "-a"])
    result = subprocess.call(["touch", mode, "-t", date, self.temp_filepath])
    # Sanity check in case something is wrong with the test.
    self.assertEqual(result, 0)


class ModificationTimeConditionTest(MetadataConditionTestMixin,
                                    absltest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = conditions.ModificationTimeCondition(params)

    self.Touch("-m", "198309121200")  # 1983-09-12 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-m", "201710020815")  # 2017-10-02 8:15
    self.assertTrue(condition.Check(self.Stat()))

  def testMinTime(self):
    time = rdfvalue.RDFDatetime.FromHumanReadable("2017-12-24 19:00:00")

    params = rdf_file_finder.FileFinderCondition()
    params.modification_time.min_last_modified_time = time
    condition = conditions.ModificationTimeCondition(params)

    self.Touch("-m", "201712240100")  # 2017-12-24 1:30
    self.assertFalse(condition.Check(self.Stat()))

    self.Touch("-m", "201806141700")  # 2018-06-14 17:00
    self.assertTrue(condition.Check(self.Stat()))

  def testMaxTime(self):
    time = rdfvalue.RDFDatetime.FromHumanReadable("2125-12-28 18:45")

    params = rdf_file_finder.FileFinderCondition()
    params.modification_time.max_last_modified_time = time
    condition = conditions.ModificationTimeCondition(params)

    self.Touch("-m", "211811111200")  # 2118-11-11 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-m", "222510201500")  # 2225-10-20 15:00
    self.assertFalse(condition.Check(self.Stat()))


class AccessTimeConditionTest(MetadataConditionTestMixin, absltest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = conditions.AccessTimeCondition(params)

    self.Touch("-a", "241007151200")  # 2410-07-15 12:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-a", "201005160745")  # 2010-05-16 7:45
    self.assertTrue(condition.Check(self.Stat()))

  def testRange(self):
    min_time = rdfvalue.RDFDatetime.FromHumanReadable("2156-01-27")
    max_time = rdfvalue.RDFDatetime.FromHumanReadable("2191-12-05")

    params = rdf_file_finder.FileFinderCondition()
    params.access_time.min_last_access_time = min_time
    params.access_time.max_last_access_time = max_time
    condition = conditions.AccessTimeCondition(params)

    self.Touch("-a", "215007280000")  # 2150-07-28 0:00
    self.assertFalse(condition.Check(self.Stat()))

    self.Touch("-a", "219101010000")  # 2191-01-01 0:00
    self.assertTrue(condition.Check(self.Stat()))

    self.Touch("-a", "221003010000")  # 2210-03-01 0:00
    self.assertFalse(condition.Check(self.Stat()))


class SizeConditionTest(MetadataConditionTestMixin, absltest.TestCase):

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = conditions.SizeCondition(params)

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"1234567")
    self.assertTrue(condition.Check(self.Stat()))

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"")
    self.assertTrue(condition.Check(self.Stat()))

  def testRange(self):
    params = rdf_file_finder.FileFinderCondition()
    params.size.min_file_size = 2
    params.size.max_file_size = 6
    condition = conditions.SizeCondition(params)

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"1")
    self.assertFalse(condition.Check(self.Stat()))

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"12")
    self.assertTrue(condition.Check(self.Stat()))

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"1234")
    self.assertTrue(condition.Check(self.Stat()))

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"123456")
    self.assertTrue(condition.Check(self.Stat()))

    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"1234567")
    self.assertFalse(condition.Check(self.Stat()))


class ExtFlagsConditionTest(MetadataConditionTestMixin, absltest.TestCase):

  # https://github.com/apple/darwin-xnu/blob/master/bsd/sys/stat.h
  UF_NODUMP = 0x00000001
  UF_IMMUTABLE = 0x00000002
  UF_HIDDEN = 0x00008000

  # https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h
  FS_COMPR_FL = 0x00000004
  FS_IMMUTABLE_FL = 0x00000010
  FS_NODUMP_FL = 0x00000040

  def testDefault(self):
    params = rdf_file_finder.FileFinderCondition()
    condition = conditions.ExtFlagsCondition(params)

    self.assertTrue(condition.Check(self.Stat()))

  def testNoMatchOsxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_IMMUTABLE | self.UF_NODUMP
    condition = conditions.ExtFlagsCondition(params)

    self._Chflags(["nodump"])

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchOsxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_unset = self.UF_NODUMP | self.UF_HIDDEN
    condition = conditions.ExtFlagsCondition(params)

    self._Chflags(["hidden"])

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchLinuxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_IMMUTABLE_FL
    condition = conditions.ExtFlagsCondition(params)

    self.assertFalse(condition.Check(self.Stat()))

  def testNoMatchLinuxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_unset = self.FS_COMPR_FL
    condition = conditions.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertFalse(condition.Check(self.Stat()))

  def testMatchOsxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_NODUMP | self.UF_HIDDEN
    condition = conditions.ExtFlagsCondition(params)

    self._Chflags(["nodump", "hidden", "uappend"])

    try:
      self.assertTrue(condition.Check(self.Stat()))
    finally:
      # Make the test file deletable.
      self._Chflags(["nouappend"])

  def testMatchLinuxBitsSet(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_COMPR_FL | self.FS_NODUMP_FL
    condition = conditions.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchOsxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_unset = self.UF_NODUMP | self.UF_IMMUTABLE
    condition = conditions.ExtFlagsCondition(params)

    self._Chflags(["hidden", "uappend"])

    try:
      self.assertTrue(condition.Check(self.Stat()))
    finally:
      # Make the test file deletable.
      self._Chflags(["nouappend"])

  def testMatchLinuxBitsUnset(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_unset = self.FS_IMMUTABLE_FL
    condition = conditions.ExtFlagsCondition(params)

    self._Chattr(["+c", "+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def testMatchOsxBitsMixed(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.osx_bits_set = self.UF_NODUMP
    params.ext_flags.osx_bits_unset = self.UF_HIDDEN
    params.ext_flags.linux_bits_unset = self.FS_NODUMP_FL
    condition = conditions.ExtFlagsCondition(params)

    self._Chflags(["nodump", "uappend"])

    try:
      self.assertTrue(condition.Check(self.Stat()))
    finally:
      # Make the test file deletable.
      self._Chflags(["nouappend"])

  def testMatchLinuxBitsMixed(self):
    params = rdf_file_finder.FileFinderCondition()
    params.ext_flags.linux_bits_set = self.FS_NODUMP_FL
    params.ext_flags.linux_bits_unset = self.FS_COMPR_FL
    params.ext_flags.osx_bits_unset = self.UF_IMMUTABLE
    condition = conditions.ExtFlagsCondition(params)

    self._Chattr(["+d"])

    self.assertTrue(condition.Check(self.Stat()))

  def _Chattr(self, attrs):
    filesystem_test_lib.Chattr(self.temp_filepath, attrs=attrs)

  def _Chflags(self, flgs):
    filesystem_test_lib.Chflags(self.temp_filepath, flags=flgs)


# TODO(hanuszczak): Write tests for the metadata change condition.


class LiteralMatchConditionTest(ConditionTestMixin, absltest.TestCase):

  def testNoHits(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foo bar quux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = b"baz"
    params.contents_literal_match.mode = "ALL_HITS"
    condition = conditions.LiteralMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertFalse(results)

  def testSomeHits(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foo bar foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = b"foo"
    params.contents_literal_match.mode = "ALL_HITS"
    condition = conditions.LiteralMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 2)
    self.assertEqual(results[0].data, b"foo")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 3)
    self.assertEqual(results[1].data, b"foo")
    self.assertEqual(results[1].offset, 8)
    self.assertEqual(results[1].length, 3)

  def testFirstHit(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"bar foo baz foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = b"foo"
    params.contents_literal_match.mode = "FIRST_HIT"
    condition = conditions.LiteralMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 1)
    self.assertEqual(results[0].data, b"foo")
    self.assertEqual(results[0].offset, 4)
    self.assertEqual(results[0].length, 3)

  def testContext(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foo foo foo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = b"foo"
    params.contents_literal_match.mode = "ALL_HITS"
    params.contents_literal_match.bytes_before = 3
    params.contents_literal_match.bytes_after = 2
    condition = conditions.LiteralMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 3)
    self.assertEqual(results[0].data, b"foo f")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 5)
    self.assertEqual(results[1].data, b"oo foo f")
    self.assertEqual(results[1].offset, 1)
    self.assertEqual(results[1].length, 8)
    self.assertEqual(results[2].data, b"oo foo")
    self.assertEqual(results[2].offset, 5)
    self.assertEqual(results[2].length, 6)

  def testStartOffset(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"oooooooo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_literal_match.literal = b"ooo"
    params.contents_literal_match.mode = "ALL_HITS"
    params.contents_literal_match.start_offset = 2
    condition = conditions.LiteralMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 2)
    self.assertEqual(results[0].data, b"ooo")
    self.assertEqual(results[0].offset, 2)
    self.assertEqual(results[0].length, 3)
    self.assertEqual(results[1].data, b"ooo")
    self.assertEqual(results[1].offset, 5)
    self.assertEqual(results[1].length, 3)


class RegexMatchCondition(ConditionTestMixin, absltest.TestCase):

  def testNoHits(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foo bar quux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = b"\\d+"
    params.contents_regex_match.mode = "FIRST_HIT"
    condition = conditions.RegexMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertFalse(results)

  def testSomeHits(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foo 7 bar 49 baz343")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = b"\\d+"
    params.contents_regex_match.mode = "ALL_HITS"
    condition = conditions.RegexMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 3)
    self.assertEqual(results[0].data, b"7")
    self.assertEqual(results[0].offset, 4)
    self.assertEqual(results[0].length, 1)
    self.assertEqual(results[1].data, b"49")
    self.assertEqual(results[1].offset, 10)
    self.assertEqual(results[1].length, 2)
    self.assertEqual(results[2].data, b"343")
    self.assertEqual(results[2].offset, 16)
    self.assertEqual(results[2].length, 3)

  def testFirstHit(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"4 8 15 16 23 42 foo 108 bar")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = b"[a-z]+"
    params.contents_regex_match.mode = "FIRST_HIT"
    condition = conditions.RegexMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 1)
    self.assertEqual(results[0].data, b"foo")
    self.assertEqual(results[0].offset, 16)
    self.assertEqual(results[0].length, 3)

  def testContext(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"foobarbazbaaarquux")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = b"ba+r"
    params.contents_regex_match.mode = "ALL_HITS"
    params.contents_regex_match.bytes_before = 3
    params.contents_regex_match.bytes_after = 4
    condition = conditions.RegexMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 2)
    self.assertEqual(results[0].data, b"foobarbazb")
    self.assertEqual(results[0].offset, 0)
    self.assertEqual(results[0].length, 10)
    self.assertEqual(results[1].data, b"bazbaaarquux")
    self.assertEqual(results[1].offset, 6)
    self.assertEqual(results[1].length, 12)

  def testStartOffset(self):
    with io.open(self.temp_filepath, "wb") as fd:
      fd.write(b"ooooooo")

    params = rdf_file_finder.FileFinderCondition()
    params.contents_regex_match.regex = b"o+"
    params.contents_regex_match.mode = "FIRST_HIT"
    params.contents_regex_match.start_offset = 3
    condition = conditions.RegexMatchCondition(params)

    with io.open(self.temp_filepath, "rb") as fd:
      results = list(condition.Search(fd))
    self.assertLen(results, 1)
    self.assertEqual(results[0].data, b"oooo")
    self.assertEqual(results[0].offset, 3)
    self.assertEqual(results[0].length, 4)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
