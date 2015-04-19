#!/usr/bin/env python
"""Tests for grr.lib.checks.filters."""
import collections
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import filters
from grr.lib.rdfvalues import checks


# Just a named tuple that can be used to test objectfilter expressions.
Sample = collections.namedtuple("Sample", ["x", "y"])


class BaseFilterTests(test_lib.GRRBaseTest):
  """Test base filter methods and operations."""

  def testEnforceList(self):
    filt = filters.Filter()
    self.assertRaises(filters.ProcessingError, filt.Parse, "not_a_list", False)

  def testValidate(self):
    filt = filters.Filter()
    self.assertRaises(NotImplementedError, filt.Validate, "anything")

  def testParse(self):
    filt = filters.Filter()
    self.assertRaises(NotImplementedError, filt.Parse, [], "do nothing")


class AttrFilterTests(test_lib.GRRBaseTest):
  """Test attribute filter methods and operations."""

  def testValidate(self):
    filt = filters.AttrFilter()
    self.assertRaises(filters.DefinitionError, filt.Validate, " ")
    self.assertFalse(filt.Validate("cfg1"))
    self.assertFalse(filt.Validate("cfg1 cfg1.test1"))

  def testParse(self):
    filt = filters.AttrFilter()

    hit1 = rdfvalue.Config(k1="hit1", k2="found1", k3=[3, 4])
    hit2 = rdfvalue.Config(k1="hit2", k2="found2")
    meta = rdfvalue.Config(one=hit1, two=hit2)
    objs = [hit1, hit2, meta]

    results = filt.Parse(objs, "k1 k2 one.k3")
    self.assertEqual(5, len(results))
    r1, r2, r3, r4, r5 = results
    self.assertEqual("k1", r1.k)
    self.assertEqual("hit1", r1.v)
    self.assertEqual("k1", r2.k)
    self.assertEqual("hit2", r2.v)
    self.assertEqual("k2", r3.k)
    self.assertEqual("found1", r3.v)
    self.assertEqual("k2", r4.k)
    self.assertEqual("found2", r4.v)
    self.assertEqual("one.k3", r5.k)
    self.assertEqual([3, 4], r5.v)


class ItemFilterTests(test_lib.GRRBaseTest):
  """Test item filter methods and operations."""

  def testParse(self):
    filt = filters.ItemFilter()

    one = rdfvalue.Config(test1="1", test2=[2, 3])
    foo = rdfvalue.Config(test1="foo", test2=["bar", "baz"])
    fs = rdfvalue.Filesystem(device="/dev/sda1", mount_point="/root")
    objs = [one, foo, fs]

    results = filt.Parse(objs, "test1 is '1'")
    self.assertEqual(1, len(results))
    self.assertEqual("test1", results[0].k)
    self.assertEqual("1", results[0].v)

    results = filt.Parse(objs, "test1 is '2'")
    self.assertFalse(results)

    results = filt.Parse(objs, "test2 contains 3")
    self.assertEqual(1, len(results))
    self.assertEqual("test2", results[0].k)
    self.assertEqual([2, 3], results[0].v)

    results = filt.Parse(objs, "test1 is '1' or test1 contains 'foo'")
    self.assertEqual(2, len(results))
    self.assertEqual("test1", results[0].k)
    self.assertEqual("1", results[0].v)
    self.assertEqual("test1", results[1].k)
    self.assertEqual("foo", results[1].v)

    results = filt.Parse(objs, "mount_point is '/root'")
    self.assertEqual(1, len(results))
    self.assertEqual("mount_point", results[0].k)
    self.assertEqual("/root", results[0].v)


class ObjectFilterTests(test_lib.GRRBaseTest):
  """Test object filter methods and operations."""

  def testValidate(self):
    filt = filters.ObjectFilter()
    self.assertRaises(filters.DefinitionError, filt.Validate, "bad term")
    self.assertFalse(filt.Validate("test is 'ok'"))

  def testParse(self):
    filt = filters.ObjectFilter()

    hit1 = rdfvalue.Config(test="hit1")
    hit2 = rdfvalue.Config(test="hit2")
    miss = rdfvalue.Config(test="miss")
    objs = [hit1, hit2, miss]
    results = filt.Parse(objs, "test is 'hit1'")
    self.assertItemsEqual([hit1], results)
    results = filt.Parse(objs, "test is 'hit2'")
    self.assertItemsEqual([hit2], results)
    results = filt.Parse(objs, "test inset 'hit1,hit2'")
    self.assertItemsEqual([hit1, hit2], results)


class RDFFilterTests(test_lib.GRRBaseTest):
  """Test rdf filter methods and operations."""

  def testValidate(self):
    filt = filters.RDFFilter()
    self.assertFalse(filt.Validate("KnowledgeBase,Config"))
    self.assertRaises(filters.DefinitionError, filt.Validate,
                      "KnowledgeBase,Nonexistent")

  def testParse(self):
    filt = filters.RDFFilter()
    cfg = rdfvalue.Config()
    anom = rdfvalue.Anomaly()
    objs = [cfg, anom]
    results = filt.Parse(objs, "KnowledgeBase")
    self.assertFalse(results)
    results = filt.Parse(objs, "Config,KnowledgeBase")
    self.assertItemsEqual([cfg], results)
    results = filt.Parse(objs, "Anomaly,Config,KnowledgeBase")
    self.assertItemsEqual(objs, results)


class StatFilterTests(test_lib.GRRBaseTest):
  """Test stat filter methods and operations."""

  bad_null = ["", " :"]
  bad_file = ["file_re:[[["]
  bad_gids = ["gid: ", "gid 0", "gid:0", "gid:=", "gid:gid:"]
  bad_mode = ["mode 755", "mode:755", "mode:0999", "mode:0777,0775"]
  bad_mask = ["mask 755", "mask:755", "mask:0999", "mask:0777,0775"]
  bad_path = ["path_re:[[["]
  bad_type = ["file_type: ", "file_type foo", "file_type:foo",
              "file_type:directory,regular"]
  bad_uids = ["uid: ", "uid 0", "uid:0", "uid:=", "uid:gid:"]
  badness = [bad_null, bad_file, bad_gids, bad_mask, bad_mode, bad_path,
             bad_type, bad_uids]

  ok_file = ["file_re:/etc/passwd"]
  ok_gids = ["gid:=0", "gid:=1,>1,<1,>=1,<=1,!1"]
  ok_mode = ["mode:0002"]
  ok_mask = ["mode:1002"]
  ok_path = ["path_re:/home/*"]
  ok_type = ["file_type:REGULAR", "file_type:directory"]
  ok_uids = ["uid:=0", "uid:=1,>1,<1,>=1,<=1,!1"]
  just_fine = [ok_file, ok_gids, ok_mask, ok_mode, ok_path, ok_type, ok_uids]

  def _GenStat(self, path="/etc/passwd", st_mode=33184, st_ino=1063090,
               st_dev=64512L, st_nlink=1, st_uid=1001, st_gid=5000,
               st_size=1024, st_atime=1336469177, st_mtime=1336129892,
               st_ctime=1336129892):
    """Generate a StatEntry RDF value."""
    pathspec = rdfvalue.PathSpec(
        path=path, pathtype=rdfvalue.PathSpec.PathType.OS)
    return rdfvalue.StatEntry(pathspec=pathspec, st_mode=st_mode, st_ino=st_ino,
                              st_dev=st_dev, st_nlink=st_nlink, st_uid=st_uid,
                              st_gid=st_gid, st_size=st_size, st_atime=st_atime,
                              st_mtime=st_mtime, st_ctime=st_ctime)

  def testValidate(self):
    filt = filters.StatFilter()
    for params in self.badness:
      for bad in params:
        self.assertRaises(filters.DefinitionError, filt.Validate, bad)
    for params in self.just_fine:
      for ok in params:
        self.assertTrue(filt.Validate(ok), "Rejected valid expression: %s" % ok)

  def testFileTypeParse(self):
    """FileType filters restrict results to specified file types."""
    all_types = {"BLOCK": self._GenStat(st_mode=24992),        # 0060640
                 "Character": self._GenStat(st_mode=8608),     # 0020640
                 "directory": self._GenStat(st_mode=16873),    # 0040751
                 "fiFO": self._GenStat(st_mode=4534),          # 0010666
                 "REGULAR": self._GenStat(st_mode=33204),      # 0100664
                 "socket": self._GenStat(st_mode=49568),       # 0140640
                 "SymLink": self._GenStat(st_mode=41471)}      # 0120777
    filt = filters.StatFilter()
    for file_type, expected in all_types.iteritems():
      filt._Flush()
      results = filt.Parse(all_types.values(), "file_type:%s" % file_type)
      self.assertEqual(1, len(results), "Expected exactly 1 %s" % file_type)
      self.assertEqual(expected, results[0],
                       "Expected stat %s, got %s" % (expected, results[0]))

  def testFileREParse(self):
    """File regexes operate successfully."""
    filt = filters.StatFilter()
    obj1 = self._GenStat(path="/etc/passwd")
    obj2 = self._GenStat(path="/etc/alternatives/ssh-askpass")
    obj3 = self._GenStat(path="/etc/alternatives/ssh-askpass.1.gz")
    objs = [obj1, obj2, obj3]
    results = filt.Parse(objs, "file_re:pass")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "file_re:pass$")
    self.assertItemsEqual([obj2], results)
    results = filt.Parse(objs, "file_re:^pass")
    self.assertItemsEqual([obj1], results)

  def testPathREParse(self):
    """Path regexes operate successfully."""
    filt = filters.StatFilter()
    obj1 = self._GenStat(path="/etc/passwd")
    obj2 = self._GenStat(path="/etc/alternatives/ssh-askpass")
    obj3 = self._GenStat(path="/etc/alternatives/ssh-askpass.1.gz")
    objs = [obj1, obj2, obj3]
    results = filt.Parse(objs, "path_re:/etc/*")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "path_re:alternatives")
    self.assertItemsEqual([obj2, obj3], results)
    results = filt.Parse(objs, "path_re:alternatives file_re:pass$")
    self.assertItemsEqual([obj2], results)

  def testGIDParse(self):
    """GID comparisons operate successfully."""
    filt = filters.StatFilter()
    obj1 = self._GenStat(st_gid=0)
    obj2 = self._GenStat(st_gid=500)
    obj3 = self._GenStat(st_gid=5000)
    objs = [obj1, obj2, obj3]
    results = filt.Parse(objs, "gid:=0")
    self.assertItemsEqual([obj1], results)
    results = filt.Parse(objs, "gid:>=0")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "gid:>0")
    self.assertItemsEqual([obj2, obj3], results)
    results = filt.Parse(objs, "gid:>0,<=5000")
    self.assertItemsEqual([obj2, obj3], results)
    results = filt.Parse(objs, "gid:>0,<5000")
    self.assertItemsEqual([obj2], results)
    results = filt.Parse(objs, "gid:!5000")
    self.assertItemsEqual([obj1, obj2], results)

  def testUIDParse(self):
    """UID comparisons operate successfully."""
    filt = filters.StatFilter()
    obj1 = self._GenStat(st_uid=1001)
    obj2 = self._GenStat(st_uid=5000)
    objs = [obj1, obj2]
    results = filt.Parse(objs, "uid:=0")
    self.assertFalse(results)
    results = filt.Parse(objs, "uid:=1001")
    self.assertItemsEqual([obj1], results)
    results = filt.Parse(objs, "uid:>=0")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "uid:>0")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "uid:>0,<=5000")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "uid:>0,<5000")
    self.assertItemsEqual([obj1], results)
    results = filt.Parse(objs, "uid:!5000")
    self.assertItemsEqual([obj1], results)

  def testPermissionsParse(self):
    """Permissions comparisons operate successfully."""
    filt = filters.StatFilter()
    obj1 = self._GenStat(st_mode=0100740)
    obj2 = self._GenStat(st_mode=0100755)
    objs = [obj1, obj2]
    results = filt.Parse(objs, "mode:0644")
    self.assertFalse(results)
    results = filt.Parse(objs, "mode:0740")
    self.assertItemsEqual([obj1], results)
    results = filt.Parse(objs, "mode:0640 mask:0640")
    self.assertItemsEqual(objs, results)
    results = filt.Parse(objs, "mode:0014 mask:0014")
    self.assertItemsEqual([obj2], results)

  def testParseFileObjs(self):
    """Multiple file types are parsed successfully."""
    filt = filters.StatFilter()
    ok = self._GenStat(
        path="/etc/shadow", st_uid=0, st_gid=0, st_mode=0100640)
    link = self._GenStat(
        path="/etc/shadow", st_uid=0, st_gid=0, st_mode=0120640)
    user = self._GenStat(
        path="/etc/shadow", st_uid=1000, st_gid=1000, st_mode=0100640)
    writable = self._GenStat(
        path="/etc/shadow", st_uid=0, st_gid=0, st_mode=0100666)
    cfg = {"path": "/etc/shadow", "st_uid": 0, "st_gid": 0, "st_mode": 0100640}
    invalid = rdfvalue.Config(**cfg)
    objs = [ok, link, user, writable, invalid]
    results = filt.Parse(objs, "uid:>=0 gid:>=0")
    self.assertItemsEqual([ok, link, user, writable], results)
    results = filt.Parse(objs, "uid:=0 mode:0440 mask:0440")
    self.assertItemsEqual([ok, link, writable], results)
    results = filt.Parse(objs, "uid:=0 mode:0440 mask:0444")
    self.assertItemsEqual([ok, link], results)
    results = list(
        filt.Parse(objs, "uid:=0 mode:0440 mask:0444 file_type:regular"))
    self.assertItemsEqual([ok], results)


class FilterRegistryTests(test_lib.GRRBaseTest):
  """Test filter methods and operations."""

  def testFilterRegistry(self):
    filters.Filter.filters = {}

    filt = filters.Filter.GetFilter("Filter")
    # It should be the right type of filter.
    # And should be in the registry already.
    self.assertIsInstance(filt, filters.Filter)
    self.assertEqual(filt, filters.Filter.GetFilter("Filter"))

    filt = filters.Filter.GetFilter("ObjectFilter")
    self.assertIsInstance(filt, filters.ObjectFilter)
    self.assertEqual(filt, filters.Filter.GetFilter("ObjectFilter"))

    filt = filters.Filter.GetFilter("RDFFilter")
    self.assertIsInstance(filt, filters.RDFFilter)
    self.assertEqual(filt, filters.Filter.GetFilter("RDFFilter"))

    filters.Filter.filters = {}
    self.assertRaises(filters.DefinitionError, filters.Filter.GetFilter, "???")


class HandlerTests(test_lib.GRRBaseTest):
  """Test handler operations."""

  def setUp(self):
    super(HandlerTests, self).setUp()
    fx0 = checks.Filter({"type": "ObjectFilter", "expression": "x == 0"})
    fy0 = checks.Filter({"type": "ObjectFilter", "expression": "y == 0"})
    bad = checks.Filter({"type": "ObjectFilter", "expression": "y =="})
    self.ok = [fx0, fy0]
    self.bad = [fx0, fy0, bad]
    self.all = [Sample(0, 0), Sample(0, 1), Sample(1, 0), Sample(1, 1)]

  def GetFilters(self, filt_defs):
    """Initialize one or more filters as if they were contained in a probe."""
    # The artifact isn't actually used for anything, it's just required to
    # initialize handlers.
    probe = rdfvalue.Probe(artifact="Data", filters=filt_defs)
    return probe.filters

  def testValidateFilters(self):
    self.assertEquals(2, len(self.GetFilters(self.ok)))
    self.assertRaises(filters.DefinitionError, self.GetFilters, self.bad)

  def testBaseHandler(self):
    # Handler needs an artifact.
    self.assertRaises(filters.DefinitionError, filters.BaseHandler)
    h = filters.BaseHandler("STUB")
    self.assertRaises(NotImplementedError, h.Parse, "STUB")

  def testNoOpHandler(self):
    h = filters.GetHandler("PASSTHROUGH")
    handler = h("Data", filters=self.GetFilters(self.ok))
    self.assertItemsEqual(self.all, handler.Parse(self.all))

  def testParallelHandler(self):
    h = filters.GetHandler("PARALLEL")
    # Without filters.
    handler = h("Data", filters=[])
    self.assertItemsEqual(self.all, handler.Parse(self.all))
    # With filters.
    handler = h("Data", filters=self.GetFilters(self.ok))
    expected = [Sample(0, 0), Sample(0, 1), Sample(1, 0)]
    self.assertItemsEqual(expected, handler.Parse(self.all))

  def testSerialHandler(self):
    h = filters.GetHandler("SERIAL")
    # Without filters.
    handler = h("Data", filters=[])
    self.assertItemsEqual(self.all, handler.Parse(self.all))
    # With filters.
    handler = h("Data", filters=self.GetFilters(self.ok))
    expected = [Sample(0, 0)]
    self.assertItemsEqual(expected, handler.Parse(self.all))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
