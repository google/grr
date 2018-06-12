#!/usr/bin/env python
"""VFS-related test classes."""

import logging
import os
import time

import mock

from grr import config
from grr_response_client import client_utils
from grr_response_client import vfs
# TODO(hanuszczak): This import is required because otherwise VFS handler
# classes are not registered correctly and things start to fail. This is
# terrible and has to be fixed as soon as possible.
from grr_response_client.vfs_handlers import files  # pylint: disable=unused-import
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import client_fixture
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard as aff4_standard


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


class FakeTestDataVFSOverrider(VFSOverrider):
  """A context to temporarily change VFS handler to `FakeTestDataVFSHandler`."""

  def __init__(self):
    super_class = super(FakeTestDataVFSOverrider, self)
    super_class.__init__(rdf_paths.PathSpec.PathType.OS, FakeTestDataVFSHandler)

  def __enter__(self):
    super(FakeTestDataVFSOverrider, self).__enter__()

    def Open(path, *args, **kwagrs):
      path = FakeTestDataVFSHandler.FakeRootPath(path)
      return self._os_open(path, *args, **kwagrs)

    self._os_open = os.open
    os.open = Open

  def __exit__(self, exc_type, exc_value, trace):
    super(FakeTestDataVFSOverrider, self).__exit__(exc_type, exc_value, trace)
    os.open = self._os_open


class ClientVFSHandlerFixtureBase(vfs.VFSHandler):
  """A base class for VFSHandlerFixtures."""

  def ListNames(self):
    for stat in self.ListFiles():
      yield os.path.basename(stat.pathspec.path)

  def IsDirectory(self):
    return bool(self.ListFiles())

  def _FakeDirStat(self, vfs_type=None):
    # We return some fake data, this makes writing tests easier for some
    # things but we give an error to the tester as it is often not what you
    # want.
    logging.warn("Fake value for %s under %s", self.path, self.prefix)

    for path in self.pathspec:
      path.path = self._NormalizeCaseForPath(self.path, vfs_type=vfs_type)

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
        path = utils.Join(* [x.lower() for x in parts])
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

  def ListFiles(self, ext_attrs=None):
    del ext_attrs  # Unused.

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

  def Stat(self, path=None, ext_attrs=None):
    """Get Stat for self.path."""
    del path, ext_attrs  # Unused.
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
      return self._FakeDirStat(aff4_grr.VFSFile)


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

  @classmethod
  def FakeRootPath(cls, path):
    test_data_dir = config.CONFIG["Test.data_dir"]
    return os.path.join(test_data_dir, "VFSFixture", path.lstrip("/"))

  def _AbsPath(self, filename=None):
    path = self.path
    if filename:
      path = os.path.join(path, filename)
    return self.FakeRootPath(path)

  def Read(self, length):
    test_data_path = self._AbsPath()

    if not os.path.exists(test_data_path):
      raise IOError("Could not find %s" % test_data_path)

    data = open(test_data_path, "rb").read()[self.offset:self.offset + length]

    self.offset += len(data)
    return data

  def Stat(self, path=None, ext_attrs=None):
    """Get Stat for self.path."""
    del path  # Unused.
    return client_utils.StatEntryFromPath(
        self._AbsPath(), self.pathspec, ext_attrs=ext_attrs)

  def ListFiles(self, ext_attrs=None):
    for f in os.listdir(self._AbsPath()):
      ps = self.pathspec.Copy()
      ps.last.path = os.path.join(ps.last.path, f)
      yield client_utils.StatEntryFromPath(
          self._AbsPath(f), self.pathspec, ext_attrs=ext_attrs)


class RegistryFake(FakeRegistryVFSHandler):
  """Implementation of fake registry VFS handler."""

  class FakeKeyHandle(object):

    def __init__(self, value):
      self.value = value.replace("\\", "/")

    def __enter__(self):
      return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
      return False

  def OpenKey(self, key, sub_key):
    res = "%s/%s" % (key.value, sub_key.replace("\\", "/"))
    res = res.rstrip("/")
    parts = res.split("/")
    for cache_key in [
        utils.Join(* [p.lower() for p in parts[:-1]] + parts[-1:]),
        res.lower()
    ]:
      if not cache_key.startswith("/"):
        cache_key = "/" + cache_key
      if cache_key in self.cache[self.prefix]:
        return self.__class__.FakeKeyHandle(cache_key)
    raise IOError()

  def QueryValueEx(self, key, value_name):
    full_key = os.path.join(key.value.lower(), value_name).rstrip("/")
    try:
      stat_entry = self.cache[self.prefix][full_key][1]
      data = stat_entry.registry_data.GetValue()
      if data:
        return data, str
    except KeyError:
      pass

    raise IOError()

  def QueryInfoKey(self, key):
    num_keys = len(self._GetKeys(key))
    num_vals = len(self._GetValues(key))
    for path in self.cache[self.prefix]:
      if path == key.value:
        _, stat_entry = self.cache[self.prefix][path]
        modification_time = stat_entry.st_mtime
        if modification_time:
          return num_keys, num_vals, modification_time

    modification_time = time.time()
    return num_keys, num_vals, modification_time

  def EnumKey(self, key, index):
    try:
      return self._GetKeys(key)[index]
    except IndexError:
      raise IOError()

  def _GetKeys(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type.__name__ == "VFSDirectory":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)

  def EnumValue(self, key, index):
    try:
      subkey = self._GetValues(key)[index]
      value, value_type = self.QueryValueEx(key, subkey)
      return subkey, value, value_type
    except IndexError:
      raise IOError()

  def _GetValues(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type.__name__ == "VFSFile":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)


class RegistryVFSStubber(object):
  """Stubber helper for tests that have to emulate registry VFS handler."""

  def __enter__(self):
    self.Start()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.Stop()

  def Start(self):
    """Install the stubs."""

    modules = {
        "_winreg": mock.MagicMock(),
        "ctypes": mock.MagicMock(),
        "ctypes.wintypes": mock.MagicMock(),
        # Requires mocking because exceptions.WindowsError does not exist
        "exceptions": mock.MagicMock(),
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable= g-import-not-at-top
    from grr_response_client.vfs_handlers import registry
    import exceptions
    import _winreg
    # pylint: enable=g-import-not-at-top

    fixture = RegistryFake()

    self.stubber = utils.MultiStubber(
        (registry, "KeyHandle", RegistryFake.FakeKeyHandle),
        (registry, "OpenKey", fixture.OpenKey), (registry, "QueryValueEx",
                                                 fixture.QueryValueEx),
        (registry, "QueryInfoKey",
         fixture.QueryInfoKey), (registry, "EnumValue",
                                 fixture.EnumValue), (registry, "EnumKey",
                                                      fixture.EnumKey))
    self.stubber.Start()

    # Add the Registry handler to the vfs.
    vfs.VFSInit().Run()
    _winreg.HKEY_USERS = "HKEY_USERS"
    _winreg.HKEY_LOCAL_MACHINE = "HKEY_LOCAL_MACHINE"
    exceptions.WindowsError = IOError

  def Stop(self):
    """Uninstall the stubs."""

    self.module_patcher.stop()
    self.stubber.Stop()
