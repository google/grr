#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test client vfs."""


import __builtin__
import hashlib
import os
import platform
import stat


from grr.client import conf
from grr.client import conf as flags

# Populate the action registry
from grr.client import client_actions
from grr.client import conf
from grr.client import vfs
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class MockVFSHandlerFind(vfs.AbstractDirectoryHandler):
  """A mock VFS handler for finding files.

  This is used to create the /mock2/ client vfs branch which is utilized in the
  below tests.
  """
  altitude = 5
  supported_pathtype = jobs_pb2.Path.OS
  prefix = "/mock2"

  filesystem = {"/": ["directory1", "directory3"],
                "/directory1": ["file1.txt", "file2.txt", "directory2"],
                "/directory1/file1.txt": "Secret 1",
                "/directory1/file2.txt": "Another file",
                "/directory1/directory2": ["file.jpg", "file.mp3"],
                "/directory1/directory2/file.jpg": "JPEG",
                "/directory1/directory2/file.mp3": "MP3 movie",
                "/directory3": ["file1.txt", "long_file.text"],
                "/directory3/file1.txt": "A text file",
                "/directory3/long_file.text": "space " * 100000 + "A Secret",
               }

  def __init__(self, pathspec):
    # Parts are already normalized, this is guaranteed to work
    path = pathspec.mountpoint + pathspec.path
    if not path.startswith(self.prefix):
      raise IOError()

    # Strip the prefix
    self.path = "/" + path[1+len(self.prefix):]
    self.pathspec = pathspec

    try:
      self.content = self.filesystem[self.path]
      if isinstance(self.content, str):
        self.size = len(self.content)
    except KeyError:
      raise IOError("not mocking")

  def Read(self, length):
    result = self.content[self.offset:self.offset+length]
    self.offset = min(self.size, self.offset + len(result))
    return result

  def ListFiles(self):
    """Mock the filesystem."""
    for child in self.content:
      path = os.path.join(self.path, child)
      f = self.filesystem[path]

      ps = jobs_pb2.Path()
      ps.CopyFrom(self.pathspec)
      ps.path = utils.JoinPath(ps.path, child)
      result = jobs_pb2.StatResponse(pathspec=ps)

      if isinstance(f, str):
        result.st_mode = 0100664
      else:
        result.st_mode = 040775

      result.st_size = len(child)

      yield result


class ActionTest(test_lib.EmptyActionTest):
  """Test the client Actions."""

  def testReadBuffer(self):
    """Test reading a buffer."""
    path = os.path.join(self.base_path, "numbers.txt")
    p = jobs_pb2.Path(path=path, pathtype=jobs_pb2.Path.OS)
    result = self.RunAction("ReadBuffer",
                            jobs_pb2.BufferReadMessage(
                                pathspec=p, offset=100, length=10))[0]

    self.assertEqual(result.offset, 100)
    self.assertEqual(result.length, 10)
    self.assertEqual(result.data, "7\n38\n39\n40")

  def testListDirectory(self):
    """Tests listing directories."""
    p = jobs_pb2.Path(path=self.base_path, pathtype=0)
    results = self.RunAction("ListDirectory",
                             jobs_pb2.ListDirRequest(
                                 pathspec=p))
    # Find the number.txt file
    result = None
    for result in results:
      if os.path.basename(result.pathspec.path) == "numbers.txt":
        break

    self.assert_(result)
    self.assertEqual(result.__class__, jobs_pb2.StatResponse)
    self.assertEqual(os.path.basename(result.pathspec.path), "numbers.txt")
    self.assertEqual(result.st_size, 3893)
    self.assert_(stat.S_ISREG(result.st_mode))

  def testIteratedListDirectory(self):
    p = jobs_pb2.Path(path=self.base_path, pathtype=jobs_pb2.Path.OS)
    non_iterated_results = self.RunAction(
        "ListDirectory", jobs_pb2.ListDirRequest(pathspec=p))
    # Make sure we get some results.
    self.assert_(len(non_iterated_results) > 0)

    iterated_results = []
    request = jobs_pb2.ListDirRequest(pathspec=p)
    request.iterator.number = 2
    while True:
      responses = self.RunAction("IteratedListDirectory", request)
      results = responses[:-1]
      iterator = responses[-1]
      if not results: break

      for result in results:
        iterated_results.append(result)

      request.iterator.CopyFrom(iterator)

    for x, y in zip(non_iterated_results, iterated_results):
      self.assertEqual(x, y)

  def testHashFile(self):
    """Can we hash a file?"""
    path = os.path.join(self.base_path, "numbers.txt")
    p = jobs_pb2.Path(path=path, pathtype=jobs_pb2.Path.OS)
    result = self.RunAction("HashFile",
                            jobs_pb2.ListDirRequest(
                                pathspec=p))[0]

    self.assertEqual(result.data,
                     hashlib.sha256(open(path).read()).digest())

  def testEnumerateUsersLinux(self):
    """Enumerate users from the wtmp file."""
    # Linux only
    if platform.system() != "Linux": return

    # If the --nomock flag is set we just print all the usernames we find
    if test_lib.FLAGS.nomock:
      for result in self.RunAction("EnumerateUsers"):
        print "Found user %s" % result.username

      return

    path = os.path.join(self.base_path, "wtmp")
    old_open = __builtins__.open

    # Mock the open call
    def mocked_open(_):
      return old_open(path)

    __builtin__.open = mocked_open
    try:
      results = self.RunAction("EnumerateUsers")
    finally:
      # Restore the mock
      __builtin__.open = old_open

    found = 0
    for result in results:
      if result.username == "user1":
        found += 1
        self.assertEqual(result.last_logon, 1296552099 * 1000000)
      elif result.username == "user2":
        found += 1
        self.assertEqual(result.last_logon, 1296552102 * 1000000)
      elif result.username == "user3":
        found += 1
        self.assertEqual(result.last_logon, 1296569997 * 1000000)

    self.assertEqual(found, 3)

  def testFindAction(self):
    """Test the find action."""
    # First get all the files at once
    pathspec = jobs_pb2.Path(path="/mock2/", pathtype=jobs_pb2.Path.OS)
    request = jobs_pb2.Find(pathspec=pathspec, path_regex=".")
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, jobs_pb2.Find)]

    # Ask for the files one at the time
    files = []
    request = jobs_pb2.Find(pathspec=pathspec)
    request.iterator.number = 1

    while True:
      result = self.RunAction("Find", request)
      if request.iterator.state == jobs_pb2.Iterator.FINISHED:
        break

      self.assertEqual(len(result), 2)
      self.assert_(isinstance(result[0], jobs_pb2.Find))
      self.assert_(isinstance(result[1], jobs_pb2.Iterator))
      files.append(result[0].hit)
      request.iterator.CopyFrom(result[1])

    for x, y in zip(all_files, files):
      self.assertEqual(x, y)

    # Make sure the iterator is finished
    self.assertEqual(request.iterator.state, jobs_pb2.Iterator.FINISHED)

    # Ensure we remove old states from client_state
    self.assertEqual(len(request.iterator.client_state.dat), 0)

  def testFindAction2(self):
    """Test the find action path regex."""
    pathspec = jobs_pb2.Path(path="/mock2/", pathtype=jobs_pb2.Path.OS)
    request = jobs_pb2.Find(pathspec=pathspec, path_regex=".*mp3")
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, jobs_pb2.Find)]

    self.assertEqual(len(all_files), 1)
    self.assertEqual(os.path.basename(all_files[0].pathspec.path), "file.mp3")

  def testFindAction3(self):
    """Test the find action data regex."""
    # First get all the files at once
    pathspec = jobs_pb2.Path(path="/mock2/", pathtype=jobs_pb2.Path.OS)
    request = jobs_pb2.Find(pathspec=pathspec, data_regex="Secret")
    request.iterator.number = 200
    result = self.RunAction("Find", request)
    all_files = [x.hit for x in result if isinstance(x, jobs_pb2.Find)]
    self.assertEqual(len(all_files), 2)
    self.assertEqual(os.path.basename(all_files[0].pathspec.path),
                     "file1.txt")
    self.assertEqual(os.path.basename(all_files[1].pathspec.path),
                     "long_file.text")

  def testUpdateConfig(self):
    """Test that we can update the config."""
    # Make sure the config file is not already there
    try:
      os.unlink(FLAGS.config)
    except OSError: pass

    request = jobs_pb2.GRRConfig(location="http://www.example.com",
                                 foreman_check_frequency=3600)
    result = self.RunAction("UpdateConfig", request)

    self.assertEqual(result, [])
    self.assertEqual(conf.FLAGS.foreman_check_frequency, 3600)
    data = open(conf.FLAGS.config).read()
    self.assert_("location = http://www.example.com" in data)


def main(argv):
  conf.FLAGS.config = FLAGS.test_tmpdir + "/config.ini"
  # Initialize the VFS system
  vfs.VFSInit()

  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
