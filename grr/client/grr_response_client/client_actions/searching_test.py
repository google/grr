#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test client vfs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import os


from builtins import range  # pylint: disable=redefined-builtin
from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_client import vfs
from grr_response_client.client_actions import searching
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import benchmark_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import temp
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class MockVFSHandlerFind(vfs.VFSHandler):
  """A mock VFS handler for finding files.

  This is used to create the /mock2/ client vfs branch which is utilized in the
  below tests.
  """
  supported_pathtype = rdf_paths.PathSpec.PathType.OS

  filesystem = {
      "/": ["mock2"],
      "/mock2": ["directory1", "directory3"],
      "/mock2/directory1": ["file1.txt", "file2.txt", "directory2"],
      "/mock2/directory1/file1.txt": b"Secret 1",
      "/mock2/directory1/file2.txt": b"Another file",
      "/mock2/directory1/directory2": ["file.jpg", "file.mp3"],
      "/mock2/directory1/directory2/file.jpg": b"JPEG",
      "/mock2/directory1/directory2/file.mp3": b"MP3 movie",
      "/mock2/directory3": ["file1.txt", "long_file.text"],
      "/mock2/directory3/file1.txt": b"A text file",
      "/mock2/directory3/long_file.text": (b"space " * 100000 + b"A Secret")
  }

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    super(MockVFSHandlerFind, self).__init__(
        base_fd, pathspec=pathspec, progress_callback=progress_callback)

    self.pathspec.Append(pathspec)
    self.path = self.pathspec.CollapsePath()

    try:
      self.content = self.filesystem[self.path]
      if isinstance(self.content, bytes):
        self.size = len(self.content)
    except KeyError:
      raise IOError("not mocking %s" % self.path)

  def Read(self, length):
    # Reading the mocked directory raises.
    if isinstance(self.content, list):
      raise IOError()

    result = self.content[self.offset:self.offset + length]
    self.offset = min(self.size, self.offset + len(result))
    return result

  def ListNames(self):
    return self.content

  def DoStat(self, path):
    result = rdf_client_fs.StatEntry()
    if path.startswith("/mock2/directory3"):
      result.st_dev = 1
    else:
      result.st_dev = 2
    f = self.filesystem[path]
    if isinstance(f, bytes):
      if path.startswith("/mock2/directory1/directory2"):
        result.st_mode = 0o0100644  # u=rw,g=r,o=r on regular file
        result.st_uid = 50
        result.st_gid = 500
      elif path.startswith("/mock2/directory3"):
        result.st_mode = 0o0100643  # u=rw,g=r,o=wx on regular file
        result.st_uid = 60
        result.st_gid = 600
      else:
        result.st_mode = 0o0104666  # setuid, u=rw,g=rw,o=rw on regular file
        result.st_uid = 90
        result.st_gid = 900
    else:
      result.st_mode = 0o0040775  # u=rwx,g=rwx,o=rx on directory
      result.st_uid = 0
      result.st_gid = 4
    result.st_size = len(f)
    result.st_mtime = 1373185602

    return result

  def ListFiles(self, ext_attrs=None):
    """Mock the filesystem."""
    del ext_attrs  # Unused.

    for child in self.content:
      # We have a mock FS here that only uses "/".
      path = "/".join([self.path, child])
      result = self.DoStat(path)
      ps = self.pathspec.Copy()
      ps.Append(path=child, pathtype=self.supported_pathtype)
      result.pathspec = ps
      yield result

  def IsDirectory(self):
    return bool(self.content)

  def Stat(self, path=None, ext_attrs=None):
    del path, ext_attrs  # Unused.

    result = self.DoStat(self.path)
    result.pathspec = self.pathspec
    return result


def SearchParams(block_size, envelope_size):

  def Decorator(func):

    @functools.wraps(func)
    def _SearchParams(*args, **kwargs):
      """Wrapper function that sets and restores search parameters."""

      old_sizes = (searching.Grep.BUFF_SIZE, searching.Grep.ENVELOPE_SIZE)
      searching.Grep.BUFF_SIZE = block_size
      searching.Grep.ENVELOPE_SIZE = envelope_size
      try:
        return func(*args, **kwargs)
      finally:
        searching.Grep.BUFF_SIZE, searching.Grep.ENVELOPE_SIZE = old_sizes

    return _SearchParams

  return Decorator


class FindTest(client_test_lib.EmptyActionTest):
  """Test the find client Actions."""

  def setUp(self):
    super(FindTest, self).setUp()

    # Install the mock
    self.vfs_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, MockVFSHandlerFind)
    self.vfs_overrider.Start()

  def tearDown(self):
    super(FindTest, self).tearDown()
    self.vfs_overrider.Stop()

  def testFindAction(self):
    """Test the find action."""
    # First get all the files at once
    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client_fs.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    # Ask for the files one at the time
    files = []
    request = rdf_client_fs.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 1

    while True:
      result = self.RunAction(searching.Find, request)
      if request.iterator.state == rdf_client_action.Iterator.State.FINISHED:
        break

      self.assertLen(result, 2)
      self.assertIsInstance(result[0], rdf_client_fs.FindSpec)
      self.assertIsInstance(result[1], rdf_client_action.Iterator)
      files.append(result[0].hit)

      request.iterator = result[1].Copy()

    for x, y in zip(all_files, files):
      self.assertRDFValuesEqual(x, y)

    # Make sure the iterator is finished
    self.assertEqual(request.iterator.state,
                     rdf_client_action.Iterator.State.FINISHED)

    # Ensure we remove old states from client_state
    self.assertEmpty(request.iterator.client_state.dat)

  def testFindAction2(self):
    """Test the find action path regex."""
    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client_fs.FindSpec(pathspec=pathspec, path_regex=".*mp3")
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 1)
    self.assertEqual(all_files[0].pathspec.Basename(), "file.mp3")

  def testFindAction3(self):
    """Test the find action data regex."""
    # First get all the files at once
    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, data_regex="Secret", cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]
    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Basename(), "file1.txt")
    self.assertEqual(all_files[1].pathspec.Basename(), "long_file.text")

  def testFindSizeLimits(self):
    """Test the find action size limits."""
    # First get all the files at once
    request = rdf_client_fs.FindSpec(
        min_file_size=4, max_file_size=15, cross_devs=True)
    request.pathspec.Append(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)

    request.iterator.number = 200
    results = self.RunAction(searching.Find, request)
    all_files = []
    for result in results:
      if isinstance(result, rdf_client_fs.FindSpec):
        all_files.append(result.hit.pathspec.Basename())
    self.assertLen(all_files, 5)

    for filename in all_files:
      # Our mock filesize is the length of the base filename, check all the
      # files we got match the size criteria
      self.assertBetween(len(filename), 4, 15)

  def testNoFilters(self):
    """Test the we get all files with no filters in place."""
    # First get all the files at once
    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client_fs.FindSpec(pathspec=pathspec, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]
    self.assertLen(all_files, 9)

  def testFindActionCrossDev(self):
    """Test that devices boundaries don't get crossed, also by default."""
    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, cross_devs=True, path_regex=".")
    request.iterator.number = 200
    results = self.RunAction(searching.Find, request)
    all_files = [
        x.hit for x in results if isinstance(x, rdf_client_fs.FindSpec)
    ]
    self.assertLen(all_files, 9)

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, cross_devs=False, path_regex=".")
    request.iterator.number = 200
    results = self.RunAction(searching.Find, request)
    all_files = [
        x.hit for x in results if isinstance(x, rdf_client_fs.FindSpec)
    ]
    self.assertLen(all_files, 7)

    request = rdf_client_fs.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 200
    results = self.RunAction(searching.Find, request)
    all_files = [
        x.hit for x in results if isinstance(x, rdf_client_fs.FindSpec)
    ]
    self.assertLen(all_files, 7)

  def testPermissionFilter(self):
    """Test filtering based on file/folder permission happens correctly."""

    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)

    # Look for files that match exact permissions

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", perm_mode=0o644, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[0].pathspec.Basename(), "file.jpg")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[1].pathspec.Basename(), "file.mp3")

    # Look for files/folders where 'others' have 'write' permission. All other
    # attributes don't matter. Setuid bit must also be set and guid or sticky
    # bit must not be set.

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec,
        path_regex=".",
        perm_mode=0o4002,
        perm_mask=0o7002,
        cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory1")
    self.assertEqual(all_files[0].pathspec.Basename(), "file1.txt")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory1")
    self.assertEqual(all_files[1].pathspec.Basename(), "file2.txt")

    # Look for files where 'others' have 'execute' permission. All other
    # attributes don't matter. Only look for 'regular' files.

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec,
        path_regex=".",
        perm_mode=0o0100001,
        perm_mask=0o0100001,
        cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory3")
    self.assertEqual(all_files[0].pathspec.Basename(), "file1.txt")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory3")
    self.assertEqual(all_files[1].pathspec.Basename(), "long_file.text")

    # Look for folders where 'group' have 'execute' permission. All other
    # attributes don't matter. Only look for folders.

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec,
        path_regex=".",
        perm_mode=0o0040010,
        perm_mask=0o0040010,
        cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 3)
    self.assertEqual(all_files[0].pathspec.Basename(), "directory2")
    self.assertEqual(all_files[1].pathspec.Basename(), "directory1")
    self.assertEqual(all_files[2].pathspec.Basename(), "directory3")

  def testUIDFilter(self):
    """Test filtering based on uid happens correctly."""

    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)

    # Look for files that have uid of 60

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", uid=60, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory3")
    self.assertEqual(all_files[0].pathspec.Basename(), "file1.txt")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory3")
    self.assertEqual(all_files[1].pathspec.Basename(), "long_file.text")

    # Look for files that have uid of 0

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", uid=0, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 3)
    self.assertEqual(all_files[0].pathspec.Basename(), "directory2")
    self.assertEqual(all_files[1].pathspec.Basename(), "directory1")
    self.assertEqual(all_files[2].pathspec.Basename(), "directory3")

  def testGIDFilter(self):
    """Test filtering based on gid happens correctly."""

    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)

    # Look for files that have gid of 500

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", gid=500, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[0].pathspec.Basename(), "file.jpg")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[1].pathspec.Basename(), "file.mp3")

    # Look for files that have uid of 900

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", gid=900, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory1")
    self.assertEqual(all_files[0].pathspec.Basename(), "file1.txt")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory1")
    self.assertEqual(all_files[1].pathspec.Basename(), "file2.txt")

  def testUIDAndGIDFilter(self):
    """Test filtering based on combination of uid and gid happens correctly."""

    pathspec = rdf_paths.PathSpec(
        path="/mock2/", pathtype=rdf_paths.PathSpec.PathType.OS)

    # Look for files that have uid of 90 and gid of 500

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", uid=90, gid=500, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertEmpty(all_files)

    # Look for files that have uid of 50 and gid of 500

    request = rdf_client_fs.FindSpec(
        pathspec=pathspec, path_regex=".", uid=50, gid=500, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction(searching.Find, request)
    all_files = [x.hit for x in result if isinstance(x, rdf_client_fs.FindSpec)]

    self.assertLen(all_files, 2)
    self.assertEqual(all_files[0].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[0].pathspec.Basename(), "file.jpg")
    self.assertEqual(all_files[1].pathspec.Dirname().Basename(), "directory2")
    self.assertEqual(all_files[1].pathspec.Basename(), "file.mp3")


class FindExtAttrsTest(client_test_lib.EmptyActionTest):

  def testExtAttrsCollection(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      foo_filepath = temp.TempFilePath(dir=temp_dirpath)
      client_test_lib.SetExtAttr(foo_filepath, name="user.quux", value="foo")

      bar_filepath = temp.TempFilePath(dir=temp_dirpath)
      client_test_lib.SetExtAttr(bar_filepath, name="user.quux", value="bar")

      baz_filepath = temp.TempFilePath(dir=temp_dirpath)
      client_test_lib.SetExtAttr(baz_filepath, name="user.quux", value="baz")

      request = rdf_client_fs.FindSpec(
          pathspec=rdf_paths.PathSpec(
              path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS),
          path_glob="*",
          collect_ext_attrs=True)
      request.iterator.number = 100

      hits = []
      for response in self.RunAction(searching.Find, request):
        if isinstance(response, rdf_client_fs.FindSpec):
          hits.append(response.hit)

      self.assertLen(hits, 3)

      values = []
      for hit in hits:
        self.assertLen(hit.ext_attrs, 1)
        values.append(hit.ext_attrs[0].value)

      self.assertCountEqual(values, ["foo", "bar", "baz"])


class GrepTest(client_test_lib.EmptyActionTest):
  """Test the find client Actions."""

  XOR_IN_KEY = 0
  XOR_OUT_KEY = 0

  def setUp(self):
    super(GrepTest, self).setUp()

    # Install the mock
    self.vfs_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, MockVFSHandlerFind)
    self.vfs_overrider.Start()
    self.filename = "/mock2/directory1/grepfile.txt"

  def tearDown(self):
    super(GrepTest, self).tearDown()
    self.vfs_overrider.Stop()

  def testGrep(self):
    # Use the real file system.
    vfs.VFSInit().Run()

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"10", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = os.path.join(self.base_path, "numbers.txt")
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction(searching.Grep, request)
    hits = [x.offset for x in result]
    self.assertEqual(hits, [
        18, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324, 329, 729, 1129,
        1529, 1929, 2329, 2729, 3129, 3529, 3888
    ])
    for x in result:
      self.assertIn(b"10", utils.Xor(x.data, self.XOR_OUT_KEY))
      self.assertEqual(request.target.path, x.pathspec.path)

  def testGrepRegex(self):
    # Use the real file system.
    vfs.VFSInit().Run()

    request = rdf_client_fs.GrepSpec(
        regex="1[0]",
        xor_out_key=self.XOR_OUT_KEY,
        start_offset=0,
        target=rdf_paths.PathSpec(
            path=os.path.join(self.base_path, "numbers.txt"),
            pathtype=rdf_paths.PathSpec.PathType.OS))

    result = self.RunAction(searching.Grep, request)
    hits = [x.offset for x in result]
    self.assertEqual(hits, [
        18, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324, 329, 729, 1129,
        1529, 1929, 2329, 2729, 3129, 3529, 3888
    ])
    for x in result:
      self.assertIn(b"10", utils.Xor(x.data, self.XOR_OUT_KEY))

  def testGrepLength(self):
    data = b"X" * 100 + b"HIT"

    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction(searching.Grep, request)
    self.assertLen(result, 1)
    self.assertEqual(result[0].offset, 100)

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0
    request.length = 100

    result = self.RunAction(searching.Grep, request)
    self.assertEmpty(result)

  def testGrepOffset(self):
    data = b"X" * 10 + b"HIT" + b"X" * 100

    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction(searching.Grep, request)
    self.assertLen(result, 1)
    self.assertEqual(result[0].offset, 10)

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 5

    result = self.RunAction(searching.Grep, request)
    self.assertLen(result, 1)
    # This should still report 10.
    self.assertEqual(result[0].offset, 10)

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 11

    result = self.RunAction(searching.Grep, request)
    self.assertEmpty(result)

  def testOffsetAndLength(self):

    data = b"X" * 10 + b"HIT" + b"X" * 100 + b"HIT" + b"X" * 10
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 11
    request.length = 100

    result = self.RunAction(searching.Grep, request)
    self.assertEmpty(result)

  @SearchParams(1000, 100)
  def testSecondBuffer(self):

    data = b"X" * 1500 + b"HIT" + b"X" * 100
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction(searching.Grep, request)
    self.assertLen(result, 1)
    self.assertEqual(result[0].offset, 1500)

  @SearchParams(1000, 100)
  def testBufferBoundaries(self):

    for offset in range(-20, 20):

      data = b"X" * (1000 + offset) + b"HIT" + b"X" * 100
      MockVFSHandlerFind.filesystem[self.filename] = data

      request = rdf_client_fs.GrepSpec(
          literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
          xor_in_key=self.XOR_IN_KEY,
          xor_out_key=self.XOR_OUT_KEY)
      request.target.path = self.filename
      request.target.pathtype = rdf_paths.PathSpec.PathType.OS
      request.start_offset = 0

      result = self.RunAction(searching.Grep, request)
      self.assertLen(result, 1)
      self.assertEqual(result[0].offset, 1000 + offset)
      expected = b"X" * 10 + b"HIT" + b"X" * 10
      self.assertLen(expected, result[0].length)
      self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY), expected)

  def testSnippetSize(self):

    data = b"X" * 100 + b"HIT" + b"X" * 100
    MockVFSHandlerFind.filesystem[self.filename] = data

    for before in [50, 10, 1, 0]:
      for after in [50, 10, 1, 0]:
        request = rdf_client_fs.GrepSpec(
            literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
            xor_in_key=self.XOR_IN_KEY,
            xor_out_key=self.XOR_OUT_KEY)
        request.target.path = self.filename
        request.target.pathtype = rdf_paths.PathSpec.PathType.OS
        request.start_offset = 0
        request.bytes_before = before
        request.bytes_after = after

        result = self.RunAction(searching.Grep, request)
        self.assertLen(result, 1)
        self.assertEqual(result[0].offset, 100)
        expected = b"X" * before + b"HIT" + b"X" * after
        self.assertLen(expected, result[0].length)
        self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY), expected)

  @SearchParams(100, 50)
  def testGrepEverywhere(self):

    for offset in range(500):
      data = b"X" * offset + b"HIT" + b"X" * (500 - offset)
      MockVFSHandlerFind.filesystem[self.filename] = data

      request = rdf_client_fs.GrepSpec(
          literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
          xor_in_key=self.XOR_IN_KEY,
          xor_out_key=self.XOR_OUT_KEY)
      request.target.path = self.filename
      request.target.pathtype = rdf_paths.PathSpec.PathType.OS
      request.start_offset = 0
      request.bytes_before = 10
      request.bytes_after = 10

      result = self.RunAction(searching.Grep, request)
      self.assertLen(result, 1)
      self.assertEqual(result[0].offset, offset)
      expected = data[max(0, offset - 10):offset + 3 + 10]
      self.assertLen(expected, result[0].length)
      self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY), expected)

  def testHitLimit(self):
    limit = searching.Grep.HIT_LIMIT

    hit = b"x" * 10 + b"HIT" + b"x" * 10
    data = hit * (limit + 100)
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdf_client_fs.GrepSpec(
        literal=utils.Xor(b"HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdf_paths.PathSpec.PathType.OS
    request.start_offset = 0
    request.bytes_before = 10
    request.bytes_after = 10

    result = self.RunAction(searching.Grep, request)
    self.assertLen(result, limit + 1)
    error = b"maximum number of hits"
    self.assertIn(error, utils.Xor(result[-1].data, self.XOR_OUT_KEY))


class XoredSearchingTest(GrepTest):
  """Test the searching client Actions using XOR."""

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57


class FindBenchmarks(benchmark_test_lib.AverageMicroBenchmarks,
                     client_test_lib.EmptyActionTest):
  REPEATS = 100
  units = "us"

  def testFindAction(self):
    # First get all the files at once
    def RunFind():

      pathspec = rdf_paths.PathSpec(
          path=self.base_path, pathtype=rdf_paths.PathSpec.PathType.OS)
      request = rdf_client_fs.FindSpec(pathspec=pathspec)
      request.iterator.number = 80
      result = self.RunAction(searching.Find, request)
      # 80 results plus one iterator.
      self.assertLen(result, 81)

    self.TimeIt(RunFind, "Find files with no filters.")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
