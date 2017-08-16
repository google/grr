#!/usr/bin/env python
"""VFS-related test classes."""

import os

import logging

from grr import config
from grr.client import vfs
from grr.client.vfs_handlers import files
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import client_fixture
from grr.server.aff4_objects import aff4_grr
from grr.server.aff4_objects import standard as aff4_standard


class VFSOverrider(object):
  """A context to temporarily change VFS handlers."""

  def __init__(self, vfs_type, temp_handler):
    self._vfs_type = vfs_type
    self._temp_handler = temp_handler

  def __enter__(self):
    self.Start()

  def Start(self):
    self._old_handler = vfs.VFS_HANDLERS.get(self._vfs_type)
    vfs.VFS_HANDLERS[self._vfs_type] = self._temp_handler

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    if self._old_handler:
      vfs.VFS_HANDLERS[self._vfs_type] = self._old_handler
    else:
      del vfs.VFS_HANDLERS[self._vfs_type]


class ClientVFSHandlerFixtureBase(vfs.VFSHandler):
  """A base class for VFSHandlerFixtures."""

  def ListNames(self):
    for stat in self.ListFiles():
      yield os.path.basename(stat.pathspec.path)

  def IsDirectory(self):
    return bool(self.ListFiles())

  def _FakeDirStat(self):
    # We return some fake data, this makes writing tests easier for some
    # things but we give an error to the tester as it is often not what you
    # want.
    logging.warn("Fake value for %s under %s", self.path, self.prefix)
    return rdf_client.StatEntry(
        pathspec=self.pathspec,
        st_mode=16877,
        st_size=12288,
        st_atime=1319796280,
        st_dev=1)


class ClientVFSHandlerFixture(ClientVFSHandlerFixtureBase):
  """A client side VFS handler for the OS type - returns the fixture."""
  # A class wide cache for fixtures. Key is the prefix, and value is the
  # compiled fixture.
  cache = {}

  paths = None
  supported_pathtype = rdf_paths.PathSpec.PathType.OS

  # Do not auto-register.
  auto_register = False

  # Everything below this prefix is emulated
  prefix = "/fs/os"

  def __init__(self,
               base_fd=None,
               prefix=None,
               pathspec=None,
               progress_callback=None,
               full_pathspec=None):
    super(ClientVFSHandlerFixture, self).__init__(
        base_fd,
        pathspec=pathspec,
        progress_callback=progress_callback,
        full_pathspec=full_pathspec)

    self.prefix = self.prefix or prefix
    self.pathspec.Append(pathspec)
    self.path = self.pathspec.CollapsePath()
    self.paths = self.cache.get(self.prefix)

    self.PopulateCache()

  def PopulateCache(self):
    """Parse the paths from the fixture."""
    if self.paths:
      return

    # The cache is attached to the class so it can be shared by all instance.
    self.paths = self.__class__.cache[self.prefix] = {}
    for path, (vfs_type, attributes) in client_fixture.VFS:
      if not path.startswith(self.prefix):
        continue

      path = utils.NormalizePath(path[len(self.prefix):])
      if path == "/":
        continue

      stat = rdf_client.StatEntry()
      args = {"client_id": "C.1234"}
      attrs = attributes.get("aff4:stat")

      if attrs:
        attrs %= args  # Remove any %% and interpolate client_id.
        stat = rdf_client.StatEntry.FromTextFormat(utils.SmartStr(attrs))

      stat.pathspec = rdf_paths.PathSpec(
          pathtype=self.supported_pathtype, path=path)

      # TODO(user): Once we add tests around not crossing device boundaries,
      # we need to be smarter here, especially for the root entry.
      stat.st_dev = 1
      path = self._NormalizeCaseForPath(path, vfs_type)
      self.paths[path] = (vfs_type, stat)

    self.BuildIntermediateDirectories()

  def _NormalizeCaseForPath(self, path, vfs_type):
    """Handle casing differences for different filesystems."""
    # Special handling for case sensitivity of registry keys.
    # This mimicks the behavior of the operating system.
    if self.supported_pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
      self.path = self.path.replace("\\", "/")
      parts = path.split("/")
      if vfs_type == aff4_grr.VFSFile:
        # If its a file, the last component is a value which is case sensitive.
        lower_parts = [x.lower() for x in parts[0:-1]]
        lower_parts.append(parts[-1])
        path = utils.Join(*lower_parts)
      else:
        path = utils.Join(*[x.lower() for x in parts])
    return path

  def BuildIntermediateDirectories(self):
    """Interpolate intermediate directories based on their children.

    This avoids us having to put in useless intermediate directories to the
    client fixture.
    """
    for dirname, (_, stat) in self.paths.items():
      pathspec = stat.pathspec
      while 1:
        dirname = os.path.dirname(dirname)

        new_pathspec = pathspec.Copy()
        new_pathspec.path = os.path.dirname(pathspec.path)
        pathspec = new_pathspec

        if dirname == "/" or dirname in self.paths:
          break

        self.paths[dirname] = (aff4_standard.VFSDirectory, rdf_client.StatEntry(
            st_mode=16877, st_size=1, st_dev=1, pathspec=new_pathspec))

  def ListFiles(self):
    # First return exact matches
    for k, (_, stat) in self.paths.items():
      dirname = os.path.dirname(k)
      if dirname == self._NormalizeCaseForPath(self.path, None):
        yield stat

  def Read(self, length):
    result = self.paths.get(
        self._NormalizeCaseForPath(self.path, aff4_grr.VFSFile))
    if not result:
      raise IOError("File not found")

    result = result[1]  # We just want the stat.
    data = ""
    if result.HasField("resident"):
      data = result.resident
    elif result.HasField("registry_type"):
      data = utils.SmartStr(result.registry_data.GetValue())

    data = data[self.offset:self.offset + length]

    self.offset += len(data)
    return data

  def Stat(self):
    """Get Stat for self.path."""
    stat_data = self.paths.get(self._NormalizeCaseForPath(self.path, None))
    if (not stat_data and
        self.supported_pathtype == rdf_paths.PathSpec.PathType.REGISTRY):
      # Check in case it is a registry value. Unfortunately our API doesn't let
      # the user specify if they are after a value or a key, so we have to try
      # both.
      stat_data = self.paths.get(
          self._NormalizeCaseForPath(self.path, aff4_grr.VFSFile))
    if stat_data:
      return stat_data[1]  # Strip the vfs_type.
    else:
      return self._FakeDirStat()


class FakeRegistryVFSHandler(ClientVFSHandlerFixture):
  """Special client VFS mock that will emulate the registry."""
  prefix = "/registry"
  supported_pathtype = rdf_paths.PathSpec.PathType.REGISTRY


class FakeFullVFSHandler(ClientVFSHandlerFixture):
  """Full client VFS mock."""
  prefix = "/"
  supported_pathtype = rdf_paths.PathSpec.PathType.OS


class FakeTestDataVFSHandler(ClientVFSHandlerFixtureBase):
  """Client VFS mock that looks for files in the test_data directory."""
  prefix = "/fs/os"
  supported_pathtype = rdf_paths.PathSpec.PathType.OS

  def __init__(self,
               base_fd=None,
               prefix=None,
               pathspec=None,
               progress_callback=None,
               full_pathspec=None):
    super(FakeTestDataVFSHandler, self).__init__(
        base_fd,
        pathspec=pathspec,
        progress_callback=progress_callback,
        full_pathspec=full_pathspec)
    # This should not really be done since there might be more information
    # in the pathspec than the path but here in the test is ok.
    if not base_fd:
      self.pathspec = pathspec
    else:
      self.pathspec.last.path = os.path.join(
          self.pathspec.last.path, pathspec.CollapsePath().lstrip("/"))
    self.path = self.pathspec.CollapsePath()

  def _AbsPath(self, filename=None):
    path = self.path
    if filename:
      path = os.path.join(path, filename)
    return os.path.join(config.CONFIG["Test.data_dir"], "VFSFixture",
                        path.lstrip("/"))

  def Read(self, length):
    test_data_path = self._AbsPath()

    if not os.path.exists(test_data_path):
      raise IOError("Could not find %s" % test_data_path)

    data = open(test_data_path, "rb").read()[self.offset:self.offset + length]

    self.offset += len(data)
    return data

  def Stat(self):
    """Get Stat for self.path."""
    test_data_path = self._AbsPath()
    st = os.stat(test_data_path)
    return files.MakeStatResponse(st, self.pathspec)

  def ListFiles(self):
    for f in os.listdir(self._AbsPath()):
      ps = self.pathspec.Copy()
      ps.last.path = os.path.join(ps.last.path, f)
      yield files.MakeStatResponse(os.stat(self._AbsPath(f)), ps)
