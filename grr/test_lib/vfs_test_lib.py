#!/usr/bin/env python
"""VFS-related test classes."""

from collections.abc import Iterable
import os
import time
from unittest import mock

from absl.testing import absltest

from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import precondition
from grr_response_server import client_fixture
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects

# pylint: mode=test


class VFSOverrider(object):
  """A context to temporarily change VFS handlers."""

  def __init__(self, vfs_type, temp_handler):
    self._vfs_type = vfs_type
    self._temp_handler = temp_handler

  def __enter__(self):
    self.Start()

  def Start(self):
    if not vfs.VFS_HANDLERS:
      # Initialize VFS if not yet done, otherwise VFS will not initialize
      # correctly when it is used for the first time in testing code.
      vfs.Init()
    self._old_vfs_handler = vfs.VFS_HANDLERS.get(self._vfs_type)
    self._old_direct_handler = vfs.VFS_HANDLERS_DIRECT.get(self._vfs_type)
    self._old_sandbox_handler = vfs.VFS_HANDLERS_SANDBOX.get(self._vfs_type)
    vfs.VFS_HANDLERS[self._vfs_type] = self._temp_handler
    vfs.VFS_HANDLERS_DIRECT[self._vfs_type] = self._temp_handler
    vfs.VFS_HANDLERS_SANDBOX[self._vfs_type] = self._temp_handler

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    if self._old_vfs_handler:
      vfs.VFS_HANDLERS[self._vfs_type] = self._old_vfs_handler
    else:
      del vfs.VFS_HANDLERS[self._vfs_type]

    if self._old_direct_handler:
      vfs.VFS_HANDLERS_DIRECT[self._vfs_type] = self._old_direct_handler
    else:
      del vfs.VFS_HANDLERS_DIRECT[self._vfs_type]

    if self._old_sandbox_handler:
      vfs.VFS_HANDLERS_SANDBOX[self._vfs_type] = self._old_sandbox_handler
    else:
      del vfs.VFS_HANDLERS_SANDBOX[self._vfs_type]


class FakeTestDataVFSOverrider(VFSOverrider):
  """A context to temporarily change VFS handler to `FakeTestDataVFSHandler`."""

  def __init__(self):
    super(FakeTestDataVFSOverrider, self).__init__(
        rdf_paths.PathSpec.PathType.OS, FakeTestDataVFSHandler
    )

  def __enter__(self):
    super().__enter__()

    def Open(path, *args, **kwagrs):
      path = FakeTestDataVFSHandler.FakeRootPath(path)
      return self._os_open(path, *args, **kwagrs)

    self._os_open = os.open
    os.open = Open

  def __exit__(self, exc_type, exc_value, trace):
    super().__exit__(exc_type, exc_value, trace)
    os.open = self._os_open


class ClientVFSHandlerFixtureBase(vfs.VFSHandler):
  """A base class for VFSHandlerFixtures."""

  def ListNames(self):
    for stat in self.ListFiles():
      yield os.path.basename(stat.pathspec.path)

  def IsDirectory(self):
    return bool(self.ListFiles())

  def _FakeDirStat(self, vfs_name=None):
    for path in self.pathspec:
      path.path = self._NormalizeCaseForPath(self.path, vfs_name=vfs_name)

    return rdf_client_fs.StatEntry(
        pathspec=self.pathspec,
        st_mode=16877,
        st_size=12288,
        st_atime=1319796280,
        st_dev=1,
    )


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

  def __init__(
      self,
      base_fd=None,
      prefix=None,
      handlers=None,
      pathspec=None,
      progress_callback=None,
  ):
    super().__init__(
        base_fd,
        handlers=handlers,
        pathspec=pathspec,
        progress_callback=progress_callback,
    )

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
    for path, (vfs_name, attributes) in client_fixture.VFS:
      if not path.startswith(self.prefix):
        continue

      path = utils.NormalizePath(path[len(self.prefix) :])
      if path == "/":
        continue

      stat = rdf_client_fs.StatEntry()
      args = {"client_id": "C.1234"}
      attrs = attributes.get("stat")

      if attrs:
        attrs %= args  # Remove any %% and interpolate client_id.
        stat = rdf_client_fs.StatEntry.FromTextFormat(attrs)

      stat.pathspec = rdf_paths.PathSpec(
          pathtype=self.supported_pathtype, path=path
      )

      # TODO(user): Once we add tests around not crossing device boundaries,
      # we need to be smarter here, especially for the root entry.
      stat.st_dev = 1
      path = self._NormalizeCaseForPath(path, vfs_name)
      self.paths[path] = (vfs_name, stat)

    self.BuildIntermediateDirectories()

  def _NormalizeCaseForPath(self, path, vfs_name):
    """Handle casing differences for different filesystems."""
    # Special handling for case sensitivity of registry keys.
    # This mimics the behavior of the operating system.
    if self.supported_pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
      self.path = self.path.replace("\\", "/")
      parts = path.split("/")
      if vfs_name == "File":
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
    for dirname, (_, stat) in list(self.paths.items()):
      pathspec = stat.pathspec
      while 1:
        dirname = os.path.dirname(dirname)

        new_pathspec = pathspec.Copy()
        new_pathspec.path = os.path.dirname(pathspec.path)
        pathspec = new_pathspec

        if dirname == "/" or dirname in self.paths:
          break

        self.paths[dirname] = (
            "Directory",
            rdf_client_fs.StatEntry(
                st_mode=16877, st_size=1, st_dev=1, pathspec=new_pathspec
            ),
        )

  def ListFiles(self, ext_attrs=None):
    del ext_attrs  # Unused.

    # First return exact matches
    for k, (_, stat) in self.paths.items():
      dirname = os.path.dirname(k)
      if dirname == self._NormalizeCaseForPath(self.path, None):
        yield stat

  def Read(self, length):
    result = self.paths.get(self._NormalizeCaseForPath(self.path, "File"))
    if not result:
      raise IOError("File not found")

    result = result[1]  # We just want the stat.
    data = b""
    if result.HasField("resident"):
      data = result.resident
    elif result.HasField("registry_type"):
      data = str(result.registry_data.GetValue()).encode("utf-8")

    data = data[self.offset : self.offset + length]

    self.offset += len(data)
    return data

  def Stat(
      self,
      ext_attrs: bool = False,
      follow_symlink: bool = True,
  ) -> rdf_client_fs.StatEntry:
    """Get Stat for self.path."""
    del ext_attrs, follow_symlink  # Unused.
    stat_data = self.paths.get(self._NormalizeCaseForPath(self.path, None))
    if (
        not stat_data
        and self.supported_pathtype == rdf_paths.PathSpec.PathType.REGISTRY
    ):
      # Check in case it is a registry value. Unfortunately our API doesn't let
      # the user specify if they are after a value or a key, so we have to try
      # both.
      stat_data = self.paths.get(self._NormalizeCaseForPath(self.path, "File"))
    if stat_data:
      return stat_data[1]  # Strip the vfs_name.
    else:
      return self._FakeDirStat("File")


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

  def __init__(
      self,
      base_fd=None,
      handlers=None,
      prefix=None,
      pathspec=None,
      progress_callback=None,
  ):
    super().__init__(
        base_fd,
        handlers=handlers,
        pathspec=pathspec,
        progress_callback=progress_callback,
    )
    # This should not really be done since there might be more information
    # in the pathspec than the path but here in the test is ok.
    if not base_fd:
      self.pathspec = pathspec
    else:
      self.pathspec.last.path = os.path.join(
          self.pathspec.last.path, pathspec.CollapsePath().lstrip("/")
      )
    self.path = self.pathspec.CollapsePath()
    if pathspec.file_size_override:
      self.size = pathspec.file_size_override

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

    data = open(test_data_path, "rb").read()[self.offset : self.offset + length]

    self.offset += len(data)
    return data

  def Stat(
      self,
      ext_attrs: bool = False,
      follow_symlink: bool = True,
  ) -> rdf_client_fs.StatEntry:
    """Get Stat for self.path."""
    del follow_symlink  # Unused.

    return client_utils.StatEntryFromPath(
        self._AbsPath(), self.pathspec, ext_attrs=ext_attrs
    )

  def ListFiles(self, ext_attrs=None):
    for f in os.listdir(self._AbsPath()):
      ps = self.pathspec.Copy()
      ps.last.path = os.path.join(ps.last.path, f)
      yield client_utils.StatEntryFromPath(
          self._AbsPath(f), ps, ext_attrs=ext_attrs
      )


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
        utils.Join(*[p.lower() for p in parts[:-1]] + parts[-1:]),
        res.lower(),
    ]:
      if not cache_key.startswith("/"):
        cache_key = "/" + cache_key
      if cache_key in self.cache[self.prefix]:
        return self.__class__.FakeKeyHandle(cache_key)

    raise OSError()

  def QueryValueEx(self, key, value_name):
    res = key.value.replace("\\", "/").rstrip("/")
    parts = res.split("/")
    full_key = utils.Join(*[p.lower() for p in parts[:-1]] + parts[-1:])
    try:
      stat_entry = self.cache[self.prefix][full_key][1]
      data = stat_entry.registry_data.GetValue()
      if data:
        return data, str
    except KeyError:
      pass

    raise OSError()

  def QueryInfoKey(self, key):
    num_keys = len(self._GetKeys(key))
    num_vals = len(self._GetValues(key))
    for path in self.cache[self.prefix]:
      if path == key.value:
        _, stat_entry = self.cache[self.prefix][path]
        modification_time = stat_entry.st_mtime
        if modification_time:
          return num_keys, num_vals, modification_time

    modification_time = int(time.time())
    return num_keys, num_vals, modification_time

  def EnumKey(self, key, index):
    try:
      return self._GetKeys(key)[index]
    except IndexError as exc:
      raise OSError() from exc

  def _GetKeys(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type == "Directory":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)

  def EnumValue(self, key, index):
    try:
      subkey = self._GetValues(key)[index]
      value, value_type = self.QueryValueEx(key, subkey)
      return subkey, value, value_type
    except IndexError as exc:
      raise OSError() from exc

  def _GetValues(self, key):
    res = []
    for path in self.cache[self.prefix]:
      if os.path.dirname(path) == key.value:
        sub_type, stat_entry = self.cache[self.prefix][path]
        if sub_type == "File":
          res.append(os.path.basename(stat_entry.pathspec.path))
    return sorted(res)


class FakeWinreg(object):
  """A class to replace the winreg module.

  winreg is only available on Windows so we use this class in tests instead.
  """

  REG_NONE = 0
  REG_SZ = 1
  REG_EXPAND_SZ = 2
  REG_BINARY = 3
  REG_DWORD = 4
  REG_DWORD_LITTLE_ENDIAN = 4
  REG_DWORD_BIG_ENDIAN = 5
  REG_LINK = 6
  REG_MULTI_SZ = 7

  HKEY_USERS = "HKEY_USERS"
  HKEY_LOCAL_MACHINE = "HKEY_LOCAL_MACHINE"


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
        "_winreg": FakeWinreg(),
        "winreg": FakeWinreg(),
        "ctypes": mock.MagicMock(),
        "ctypes.wintypes": mock.MagicMock(),
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable= g-import-not-at-top
    from grr_response_client.vfs_handlers import registry
    # pylint: enable=g-import-not-at-top

    self._supported_pathtype = registry.RegistryFile.supported_pathtype

    fixture = RegistryFake()

    self.stubber = utils.MultiStubber(
        (registry, "KeyHandle", RegistryFake.FakeKeyHandle),
        (registry, "OpenKey", fixture.OpenKey),
        (registry, "QueryValueEx", fixture.QueryValueEx),
        (registry, "QueryInfoKey", fixture.QueryInfoKey),
        (registry, "EnumValue", fixture.EnumValue),
        (registry, "EnumKey", fixture.EnumKey),
    )
    self.stubber.Start()

    # Add the Registry handler to the vfs.
    self._original_handler = vfs.VFS_HANDLERS.get(
        self._supported_pathtype, None
    )
    vfs.VFS_HANDLERS[self._supported_pathtype] = registry.RegistryFile

  def Stop(self):
    """Uninstall the stubs."""

    self.module_patcher.stop()
    self.stubber.Stop()

    # Remove the Registry handler from the vfs.
    del vfs.VFS_HANDLERS[self._supported_pathtype]
    if self._original_handler is not None:
      vfs.VFS_HANDLERS[self._supported_pathtype] = self._original_handler


def CreateFile(client_path, content=b""):
  """Creates a file in datastore-agnostic way.

  Args:
    client_path: A `ClientPath` instance specifying location of the file.
    content: A content to write to the file.
  """
  precondition.AssertType(client_path, db.ClientPath)
  precondition.AssertType(content, bytes)

  blob_id = models_blobs.BlobID.Of(content)

  stat_entry = rdf_client_fs.StatEntry(
      pathspec=rdf_paths.PathSpec(
          pathtype=rdf_objects.PathInfo.PathTypeToPathspecPathType(
              client_path.path_type
          ),
          path="/" + "/".join(client_path.components),
      ),
      st_mode=33206,
      st_size=len(content),
  )

  data_store.BLOBS.WriteBlobs({blob_id: content})
  blob_ref = rdf_objects.BlobReference(
      size=len(content), offset=0, blob_id=bytes(blob_id)
  )
  hash_id = file_store.AddFileWithUnknownHash(client_path, [blob_ref])

  path_info = rdf_objects.PathInfo()
  path_info.path_type = client_path.path_type
  path_info.components = client_path.components
  path_info.hash_entry.num_bytes = len(content)
  path_info.hash_entry.sha256 = hash_id.AsBytes()
  path_info.stat_entry = stat_entry

  data_store.REL_DB.WritePathInfos(
      client_path.client_id, [mig_objects.ToProtoPathInfo(path_info)]
  )


def CreateDirectory(client_path):
  """Creates a directory in datastore-agnostic way.

  Args:
    client_path: A `ClientPath` instance specifying location of the file.
  """
  precondition.AssertType(client_path, db.ClientPath)

  stat_entry = rdf_client_fs.StatEntry(
      pathspec=rdf_paths.PathSpec(
          pathtype=client_path.path_type, path="/".join(client_path.components)
      ),
      st_mode=16895,
  )

  path_info = rdf_objects.PathInfo()
  path_info.path_type = client_path.path_type
  path_info.components = client_path.components
  path_info.stat_entry = stat_entry
  path_info.directory = True

  data_store.REL_DB.WritePathInfos(
      client_path.client_id, [mig_objects.ToProtoPathInfo(path_info)]
  )


def GenerateBlobRefs(
    blob_size: int, contents: bytes
) -> tuple[Iterable[bytes], Iterable[rdf_objects.BlobReference]]:
  """Generates a series of blob data and references.

  Args:
    blob_size: size of each blob.
    contents: each blob will be generated by repeating a byte from "contents"
      blob_size times.

  Returns:
    A pair of blob data sequence and blob refs sequence. For each byte
    in contents there's an element at the corresponding index in blob data
    sequence with blob's data and in blob refs sequence with a
    corresponding blob reference.
  """
  blob_data = [(c * blob_size).encode("ascii") for c in contents]
  blob_refs = []
  offset = 0
  for data in blob_data:
    blob_id = models_blobs.BlobID.Of(data)
    blob_refs.append(
        rdf_objects.BlobReference(
            offset=offset, size=len(data), blob_id=bytes(blob_id)
        )
    )
    offset += len(data)
  return blob_data, blob_refs


def CreateFileWithBlobRefsAndData(
    client_path: db.ClientPath,
    blob_refs: Iterable[rdf_objects.BlobReference],
    blob_data: Iterable[bytes],
):
  """Writes a file with given data and blob refs to the data/blob store.

  Args:
    client_path: Client path of the file to write.
    blob_refs: Blob references corresponding to a file.
    blob_data: Blob data to be written to the blob store.
  """

  path_info = rdf_objects.PathInfo.OS(components=client_path.components)

  data_store.BLOBS.WriteBlobs(
      {models_blobs.BlobID.Of(bdata): bdata for bdata in blob_data}
  )

  hash_id = rdf_objects.SHA256HashID.FromData(b"".join(blob_data))
  blob_refs = list(map(mig_objects.ToProtoBlobReference, blob_refs))
  data_store.REL_DB.WriteHashBlobReferences({hash_id: blob_refs})

  path_info = rdf_objects.PathInfo(
      path_type=client_path.path_type, components=client_path.components
  )
  path_info.hash_entry.sha256 = hash_id.AsBytes()
  data_store.REL_DB.WritePathInfos(
      client_path.client_id, [mig_objects.ToProtoPathInfo(path_info)]
  )


class VfsTestCase(absltest.TestCase):
  """Mixin that resets VFS caches after tests."""

  def tearDown(self):
    super().tearDown()
    vfs.files.FlushHandleCache()
    vfs.sleuthkit.DEVICE_CACHE.Flush()
