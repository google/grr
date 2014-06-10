#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test client vfs."""

import functools
import os


from grr.client import vfs
from grr.client.client_actions import searching
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class MockVFSHandlerFind(vfs.VFSHandler):
  """A mock VFS handler for finding files.

  This is used to create the /mock2/ client vfs branch which is utilized in the
  below tests.
  """
  supported_pathtype = rdfvalue.PathSpec.PathType.OS

  filesystem = {"/": ["mock2"],
                "/mock2": ["directory1", "directory3"],
                "/mock2/directory1": ["file1.txt", "file2.txt", "directory2"],
                "/mock2/directory1/file1.txt": "Secret 1",
                "/mock2/directory1/file2.txt": "Another file",
                "/mock2/directory1/directory2": ["file.jpg", "file.mp3"],
                "/mock2/directory1/directory2/file.jpg": "JPEG",
                "/mock2/directory1/directory2/file.mp3": "MP3 movie",
                "/mock2/directory3": ["file1.txt", "long_file.text"],
                "/mock2/directory3/file1.txt": "A text file",
                "/mock2/directory3/long_file.text": ("space " * 100000 +
                                                     "A Secret"),
               }

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    super(MockVFSHandlerFind, self).__init__(
        base_fd, pathspec=pathspec, progress_callback=progress_callback)

    self.pathspec.Append(pathspec)
    self.path = self.pathspec.CollapsePath()

    try:
      self.content = self.filesystem[self.path]
      if isinstance(self.content, str):
        self.size = len(self.content)
    except KeyError:
      raise IOError("not mocking %s" % self.path)

  def Read(self, length):
    # Reading the mocked directory raises.
    if isinstance(self.content, list):
      raise IOError()

    result = self.content[self.offset:self.offset+length]
    self.offset = min(self.size, self.offset + len(result))
    return result

  def ListNames(self):
    return self.content

  def DoStat(self, path):
    result = rdfvalue.StatEntry()
    if path.startswith("/mock2/directory3"):
      result.st_dev = 1
    else:
      result.st_dev = 2
    f = self.filesystem[path]
    if isinstance(f, str):
      result.st_mode = 0100664
    else:
      result.st_mode = 040775
    result.st_size = len(f)
    result.st_mtime = 1373185602

    return result

  def ListFiles(self):
    """Mock the filesystem."""
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

  def Stat(self):
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


class FindTest(test_lib.EmptyActionTest):
  """Test the find client Actions."""

  def setUp(self):
    super(FindTest, self).setUp()

    # Install the mock
    vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.OS] = MockVFSHandlerFind

  def testFindAction(self):
    """Test the find action."""
    # First get all the files at once
    pathspec = rdfvalue.PathSpec(path="/mock2/",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)
    request = rdfvalue.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, rdfvalue.FindSpec)]

    # Ask for the files one at the time
    files = []
    request = rdfvalue.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 1

    while True:
      result = self.RunAction("Find", request)
      if request.iterator.state == rdfvalue.Iterator.State.FINISHED:
        break

      self.assertEqual(len(result), 2)
      self.assertTrue(isinstance(result[0], rdfvalue.FindSpec))
      self.assertTrue(isinstance(result[1], rdfvalue.Iterator))
      files.append(result[0].hit)

      request.iterator = result[1].Copy()

    for x, y in zip(all_files, files):
      self.assertProtoEqual(x, y)

    # Make sure the iterator is finished
    self.assertEqual(request.iterator.state, rdfvalue.Iterator.State.FINISHED)

    # Ensure we remove old states from client_state
    self.assertEqual(len(request.iterator.client_state.dat), 0)

  def testFindAction2(self):
    """Test the find action path regex."""
    pathspec = rdfvalue.PathSpec(path="/mock2/",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)
    request = rdfvalue.FindSpec(pathspec=pathspec, path_regex=".*mp3")
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, rdfvalue.FindSpec)]

    self.assertEqual(len(all_files), 1)
    self.assertEqual(
        all_files[0].pathspec.Basename(), "file.mp3")

  def testFindAction3(self):
    """Test the find action data regex."""
    # First get all the files at once
    pathspec = rdfvalue.PathSpec(path="/mock2/",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)
    request = rdfvalue.FindSpec(pathspec=pathspec, data_regex="Secret",
                                cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, rdfvalue.FindSpec)]
    self.assertEqual(len(all_files), 2)
    self.assertEqual(all_files[0].pathspec.Basename(),
                     "file1.txt")
    self.assertEqual(all_files[1].pathspec.Basename(),
                     "long_file.text")

  def testFindSizeLimits(self):
    """Test the find action size limits."""
    # First get all the files at once
    request = rdfvalue.FindSpec(min_file_size=4, max_file_size=15,
                                cross_devs=True)
    request.pathspec.Append(path="/mock2/",
                            pathtype=rdfvalue.PathSpec.PathType.OS)

    request.iterator.number = 200
    results = self.RunAction("Find", request)
    all_files = []
    for result in results:
      if isinstance(result, rdfvalue.FindSpec):
        all_files.append(result.hit.pathspec.Basename())
    self.assertEqual(len(all_files), 5)

    for filename in all_files:
      # Our mock filesize is the length of the base filename, check all the
      # files we got match the size criteria
      self.assertTrue(4 <= len(filename) <= 15)

  def testNoFilters(self):
    """Test the we get all files with no filters in place."""
    # First get all the files at once
    pathspec = rdfvalue.PathSpec(path="/mock2/",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)
    request = rdfvalue.FindSpec(pathspec=pathspec, cross_devs=True)
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, rdfvalue.FindSpec)]
    self.assertEqual(len(all_files), 9)

  def testFindActionCrossDev(self):
    """Test that devices boundaries don't get crossed, also by default."""
    pathspec = rdfvalue.PathSpec(path="/mock2/",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)
    request = rdfvalue.FindSpec(pathspec=pathspec, cross_devs=True,
                                path_regex=".")
    request.iterator.number = 200
    results = self.RunAction("Find", request)
    all_files = [x.hit for x in results if isinstance(x, rdfvalue.FindSpec)]
    self.assertEqual(len(all_files), 9)

    request = rdfvalue.FindSpec(pathspec=pathspec, cross_devs=False,
                                path_regex=".")
    request.iterator.number = 200
    results = self.RunAction("Find", request)
    all_files = [x.hit for x in results if isinstance(x, rdfvalue.FindSpec)]
    self.assertEqual(len(all_files), 7)

    request = rdfvalue.FindSpec(pathspec=pathspec, path_regex=".")
    request.iterator.number = 200
    results = self.RunAction("Find", request)
    all_files = [x.hit for x in results if isinstance(x, rdfvalue.FindSpec)]
    self.assertEqual(len(all_files), 7)


class GrepTest(test_lib.EmptyActionTest):
  """Test the find client Actions."""

  XOR_IN_KEY = 0
  XOR_OUT_KEY = 0

  def setUp(self):
    super(GrepTest, self).setUp()

    # Install the mock
    vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.OS] = MockVFSHandlerFind
    self.filename = "/mock2/directory1/grepfile.txt"

  def testGrep(self):
    # Use the real file system.
    vfs.VFSInit().Run()

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("10", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = os.path.join(self.base_path, "numbers.txt")
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction("Grep", request)
    hits = [x.offset for x in result]
    self.assertEqual(hits, [18, 288, 292, 296, 300, 304, 308, 312, 316,
                            320, 324, 329, 729, 1129, 1529, 1929, 2329,
                            2729, 3129, 3529, 3888])
    for x in result:
      self.assertTrue("10" in utils.Xor(x.data, self.XOR_OUT_KEY))
      self.assertEqual(request.target.path, x.pathspec.path)

  def testGrepRegex(self):
    # Use the real file system.
    vfs.VFSInit().Run()

    request = rdfvalue.GrepSpec(
        regex="1[0]", xor_out_key=self.XOR_OUT_KEY, start_offset=0,
        target=rdfvalue.PathSpec(
            path=os.path.join(self.base_path, "numbers.txt"),
            pathtype=rdfvalue.PathSpec.PathType.OS))

    result = self.RunAction("Grep", request)
    hits = [x.offset for x in result]
    self.assertEqual(hits, [18, 288, 292, 296, 300, 304, 308, 312, 316,
                            320, 324, 329, 729, 1129, 1529, 1929, 2329,
                            2729, 3129, 3529, 3888])
    for x in result:
      self.assertTrue("10" in utils.Xor(x.data, self.XOR_OUT_KEY))

  def testGrepLength(self):
    data = "X" * 100 + "HIT"

    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0].offset, 100)

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0
    request.length = 100

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 0)

  def testGrepOffset(self):
    data = "X" * 10 + "HIT" + "X" * 100

    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0].offset, 10)

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 5

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 1)
    # This should still report 10.
    self.assertEqual(result[0].offset, 10)

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 11

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 0)

  def testOffsetAndLength(self):

    data = "X" * 10 + "HIT" + "X" * 100 + "HIT" + "X" * 10
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 11
    request.length = 100

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 0)

  @SearchParams(1000, 100)
  def testSecondBuffer(self):

    data = "X" * 1500 + "HIT" + "X" * 100
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0].offset, 1500)

  @SearchParams(1000, 100)
  def testBufferBoundaries(self):

    for offset in xrange(-20, 20):

      data = "X" * (1000 + offset) + "HIT" + "X" * 100
      MockVFSHandlerFind.filesystem[self.filename] = data

      request = rdfvalue.GrepSpec(
          literal=utils.Xor("HIT", self.XOR_IN_KEY),
          xor_in_key=self.XOR_IN_KEY,
          xor_out_key=self.XOR_OUT_KEY)
      request.target.path = self.filename
      request.target.pathtype = rdfvalue.PathSpec.PathType.OS
      request.start_offset = 0

      result = self.RunAction("Grep", request)
      self.assertEqual(len(result), 1)
      self.assertEqual(result[0].offset, 1000 + offset)
      expected = "X" * 10 + "HIT" + "X" * 10
      self.assertEqual(result[0].length, len(expected))
      self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY),
                       expected)

  def testSnippetSize(self):

    data = "X" * 100 + "HIT" + "X" * 100
    MockVFSHandlerFind.filesystem[self.filename] = data

    for before in [50, 10, 1, 0]:
      for after in [50, 10, 1, 0]:
        request = rdfvalue.GrepSpec(
            literal=utils.Xor("HIT", self.XOR_IN_KEY),
            xor_in_key=self.XOR_IN_KEY,
            xor_out_key=self.XOR_OUT_KEY)
        request.target.path = self.filename
        request.target.pathtype = rdfvalue.PathSpec.PathType.OS
        request.start_offset = 0
        request.bytes_before = before
        request.bytes_after = after

        result = self.RunAction("Grep", request)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].offset, 100)
        expected = "X" * before + "HIT" + "X" * after
        self.assertEqual(result[0].length, len(expected))
        self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY),
                         expected)

  @SearchParams(100, 50)
  def testGrepEverywhere(self):

    for offset in xrange(500):
      data = "X" * offset + "HIT" + "X" * (500-offset)
      MockVFSHandlerFind.filesystem[self.filename] = data

      request = rdfvalue.GrepSpec(
          literal=utils.Xor("HIT", self.XOR_IN_KEY),
          xor_in_key=self.XOR_IN_KEY,
          xor_out_key=self.XOR_OUT_KEY)
      request.target.path = self.filename
      request.target.pathtype = rdfvalue.PathSpec.PathType.OS
      request.start_offset = 0
      request.bytes_before = 10
      request.bytes_after = 10

      result = self.RunAction("Grep", request)
      self.assertEqual(len(result), 1)
      self.assertEqual(result[0].offset, offset)
      expected = data[max(0, offset-10):offset+3+10]
      self.assertEqual(result[0].length, len(expected))
      self.assertEqual(utils.Xor(result[0].data, self.XOR_OUT_KEY),
                       expected)

  def testHitLimit(self):
    limit = searching.Grep.HIT_LIMIT

    hit = "x" * 10 + "HIT" + "x" * 10
    data = hit * (limit + 100)
    MockVFSHandlerFind.filesystem[self.filename] = data

    request = rdfvalue.GrepSpec(
        literal=utils.Xor("HIT", self.XOR_IN_KEY),
        xor_in_key=self.XOR_IN_KEY,
        xor_out_key=self.XOR_OUT_KEY)
    request.target.path = self.filename
    request.target.pathtype = rdfvalue.PathSpec.PathType.OS
    request.start_offset = 0
    request.bytes_before = 10
    request.bytes_after = 10

    result = self.RunAction("Grep", request)
    self.assertEqual(len(result), limit + 1)
    error = "maximum number of hits"
    self.assertTrue(error in utils.Xor(result[-1].data,
                                       self.XOR_OUT_KEY))


class XoredSearchingTest(GrepTest):
  """Test the searching client Actions using XOR."""

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57
