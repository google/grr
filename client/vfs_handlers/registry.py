#!/usr/bin/env python
"""Implement access to the windows registry."""


import ctypes
import ctypes.wintypes
import exceptions
import os
import stat
import StringIO
import _winreg

from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import utils


# Difference between 1 Jan 1601 and 1 Jan 1970.
WIN_UNIX_DIFF_MSECS = 11644473600

# KEY_READ = STANDARD_RIGHTS_READ | KEY_QUERY_VALUE |
#            KEY_ENUMERATE_SUB_KEYS | KEY_NOTIFY
# Also see: http://msdn.microsoft.com/en-us/library/windows/desktop/
# ms724878(v=vs.85).aspx
KEY_READ = 0x20019


def CanonicalPathToLocalPath(path):
  path = path.replace("/", "\\")

  return path.strip("\\")


# _winreg is broken on Python 2.x and doesn't support unicode registry values.
# We provide some replacement functions here.

advapi32 = ctypes.windll.advapi32

LPDWORD = ctypes.POINTER(ctypes.wintypes.DWORD)
LPBYTE = ctypes.POINTER(ctypes.wintypes.BYTE)

ERROR_SUCCESS = 0
ERROR_MORE_DATA = 234


class FileTime(ctypes.Structure):
  _fields_ = [("dwLowDateTime", ctypes.wintypes.DWORD),
              ("dwHighDateTime", ctypes.wintypes.DWORD)]


RegCloseKey = advapi32.RegCloseKey  # pylint: disable=g-bad-name
RegCloseKey.restype = ctypes.c_long
RegCloseKey.argtypes = [ctypes.c_void_p]

RegEnumKeyEx = advapi32.RegEnumKeyExW  # pylint: disable=g-bad-name
RegEnumKeyEx.restype = ctypes.c_long
RegEnumKeyEx.argtypes = [ctypes.c_void_p, ctypes.wintypes.DWORD,
                         ctypes.c_wchar_p, LPDWORD,
                         LPDWORD, ctypes.c_wchar_p, LPDWORD,
                         ctypes.POINTER(FileTime)]

RegEnumValue = advapi32.RegEnumValueW  # pylint: disable=g-bad-name
RegEnumValue.restype = ctypes.c_long
RegEnumValue.argtypes = [ctypes.c_void_p, ctypes.wintypes.DWORD,
                         ctypes.c_wchar_p, LPDWORD, LPDWORD, LPDWORD, LPBYTE,
                         LPDWORD]

RegOpenKeyEx = advapi32.RegOpenKeyExW  # pylint: disable=g-bad-name
RegOpenKeyEx.restype = ctypes.c_long
RegOpenKeyEx.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong,
                         ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)]

RegQueryInfoKey = advapi32.RegQueryInfoKeyW  # pylint: disable=g-bad-name
RegQueryInfoKey.restype = ctypes.c_long
RegQueryInfoKey.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, LPDWORD, LPDWORD,
                            LPDWORD, LPDWORD, LPDWORD, LPDWORD,
                            LPDWORD, LPDWORD, LPDWORD,
                            ctypes.POINTER(FileTime)]

RegQueryValueEx = advapi32.RegQueryValueExW  # pylint: disable=g-bad-name
RegQueryValueEx.restype = ctypes.c_long
RegQueryValueEx.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, LPDWORD, LPDWORD,
                            LPBYTE, LPDWORD]


class KeyHandle(object):
  """A wrapper class for a registry key handle."""

  def __init__(self, value=0):
    if value:
      self.handle = ctypes.c_void_p(value)
    else:
      self.handle = ctypes.c_void_p()

  def __enter__(self):
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    self.Close()
    return False

  def Close(self):
    if not self.handle:
      return
    if RegCloseKey is None:
      return  # Globals become None during exit.
    rc = RegCloseKey(self.handle)
    self.handle = ctypes.c_void_p()
    if rc != ERROR_SUCCESS:
      raise ctypes.WinError(2)

  def __del__(self):
    self.Close()


def OpenKey(key, sub_key):
  """This calls the Windows OpenKeyEx function in a Unicode safe way."""
  new_key = KeyHandle()
  # Don't use KEY_WOW64_64KEY (0x100) since it breaks on Windows 2000
  rc = RegOpenKeyEx(key.handle, sub_key, 0, KEY_READ,
                    ctypes.cast(ctypes.byref(new_key.handle),
                                ctypes.POINTER(ctypes.c_void_p)))
  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)

  return new_key


def CloseKey(key):
  rc = RegCloseKey(key)
  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)


def QueryInfoKey(key):
  """This calls the Windows RegQueryInfoKey function in a Unicode safe way."""
  null = LPDWORD()
  num_sub_keys = ctypes.wintypes.DWORD()
  num_values = ctypes.wintypes.DWORD()
  ft = FileTime()
  rc = RegQueryInfoKey(key.handle, ctypes.c_wchar_p(), null, null,
                       ctypes.byref(num_sub_keys), null, null,
                       ctypes.byref(num_values), null, null, null,
                       ctypes.byref(ft))
  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)

  return (num_sub_keys.value, num_values.value,
          ft.dwLowDateTime | (ft.dwHighDateTime << 32))


def QueryValueEx(key, value_name):
  """This calls the Windows QueryValueEx function in a Unicode safe way."""
  size = 256
  data_type = ctypes.wintypes.DWORD()
  while True:
    tmp_size = ctypes.wintypes.DWORD(size)
    buf = ctypes.create_string_buffer(size)
    rc = RegQueryValueEx(key.handle, value_name, LPDWORD(),
                         ctypes.byref(data_type),
                         ctypes.cast(buf, LPBYTE), ctypes.byref(tmp_size))
    if rc != ERROR_MORE_DATA:
      break

    # We limit the size here to ~10 MB so the response doesn't get too big.
    if size > 10 * 1024 * 1024:
      raise exceptions.WindowsError("Value too big to be read by GRR.")

    size *= 2

  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)

  return (Reg2Py(buf, tmp_size.value, data_type.value), data_type.value)


def EnumKey(key, index):
  """This calls the Windows RegEnumKeyEx function in a Unicode safe way."""
  buf = ctypes.create_unicode_buffer(257)
  length = ctypes.wintypes.DWORD(257)
  rc = RegEnumKeyEx(key.handle, index,
                    ctypes.cast(buf, ctypes.c_wchar_p),
                    ctypes.byref(length),
                    LPDWORD(), ctypes.c_wchar_p(), LPDWORD(),
                    ctypes.POINTER(FileTime)())
  if rc != 0:
    raise ctypes.WinError(2)

  return ctypes.wstring_at(buf, length.value).rstrip(u"\x00")


def EnumValue(key, index):
  """This calls the Windows RegEnumValue function in a Unicode safe way."""
  null = ctypes.POINTER(ctypes.wintypes.DWORD)()
  value_size = ctypes.wintypes.DWORD()
  data_size = ctypes.wintypes.DWORD()
  rc = RegQueryInfoKey(key.handle, ctypes.c_wchar_p(), null, null, null,
                       null, null, null,
                       ctypes.byref(value_size), ctypes.byref(data_size),
                       null, ctypes.POINTER(FileTime)())
  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)

  value_size.value += 1
  data_size.value += 1

  value = ctypes.create_unicode_buffer(value_size.value)

  while True:
    data = ctypes.create_string_buffer(data_size.value)

    tmp_value_size = ctypes.wintypes.DWORD(value_size.value)
    tmp_data_size = ctypes.wintypes.DWORD(data_size.value)
    data_type = ctypes.wintypes.DWORD()
    rc = RegEnumValue(key.handle, index,
                      ctypes.cast(value, ctypes.c_wchar_p),
                      ctypes.byref(tmp_value_size), null,
                      ctypes.byref(data_type),
                      ctypes.cast(data, LPBYTE),
                      ctypes.byref(tmp_data_size))

    if rc != ERROR_MORE_DATA:
      break

    data_size.value *= 2

  if rc != ERROR_SUCCESS:
    raise ctypes.WinError(2)

  return (value.value, Reg2Py(data, tmp_data_size.value, data_type.value),
          data_type.value)


def Reg2Py(data, size, data_type):
  if data_type == _winreg.REG_DWORD:
    if size == 0:
      return 0
    return ctypes.cast(data, ctypes.POINTER(ctypes.c_int)).contents.value
  elif data_type == _winreg.REG_SZ or data_type == _winreg.REG_EXPAND_SZ:
    return ctypes.wstring_at(data, size // 2).rstrip(u"\x00")
  elif data_type == _winreg.REG_MULTI_SZ:
    return ctypes.wstring_at(data, size // 2).rstrip(u"\x00").split(u"\x00")
  else:
    if size == 0:
      return None
    return ctypes.string_at(data, size)


class RegistryFile(vfs.VFSHandler):
  """Emulate registry access through the VFS."""

  supported_pathtype = rdfvalue.PathSpec.PathType.REGISTRY
  auto_register = True

  value = None
  value_type = _winreg.REG_NONE
  hive = None
  last_modified = 0
  is_directory = True
  fd = None

  # Maps the registry types to protobuf enums
  registry_map = {
      _winreg.REG_NONE: rdfvalue.StatEntry.RegistryType.REG_NONE,
      _winreg.REG_SZ: rdfvalue.StatEntry.RegistryType.REG_SZ,
      _winreg.REG_EXPAND_SZ: rdfvalue.StatEntry.RegistryType.REG_EXPAND_SZ,
      _winreg.REG_BINARY: rdfvalue.StatEntry.RegistryType.REG_BINARY,
      _winreg.REG_DWORD: rdfvalue.StatEntry.RegistryType.REG_DWORD,
      _winreg.REG_DWORD_LITTLE_ENDIAN: (
          rdfvalue.StatEntry.RegistryType.REG_DWORD_LITTLE_ENDIAN),
      _winreg.REG_DWORD_BIG_ENDIAN: (
          rdfvalue.StatEntry.RegistryType.REG_DWORD_BIG_ENDIAN),
      _winreg.REG_LINK: rdfvalue.StatEntry.RegistryType.REG_LINK,
      _winreg.REG_MULTI_SZ: rdfvalue.StatEntry.RegistryType.REG_MULTI_SZ,
  }

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    super(RegistryFile, self).__init__(base_fd, pathspec=pathspec,
                                       progress_callback=progress_callback)

    if base_fd is None:
      self.pathspec.Append(pathspec)
    elif base_fd.IsDirectory():
      self.pathspec.last.path = utils.JoinPath(self.pathspec.last.path,
                                               pathspec.path)
    else:
      raise IOError("Registry handler can not be stacked on another handler.")

    path_components = filter(None, self.pathspec.last.path.split("/"))
    try:
      # The first component MUST be a hive
      self.hive = getattr(_winreg, path_components[0])
      self.hive = KeyHandle(self.hive)
    except AttributeError:
      raise IOError("Unknown hive name %s" % path_components[0])
    except IndexError:
      # A hive is not specified, we just list all the hives.
      return

    # Normalize the path casing if needed
    self.key_name = "/".join(path_components[1:])
    self.local_path = CanonicalPathToLocalPath(self.key_name)

    try:
      # Maybe its a value
      key_name, value_name = os.path.split(self.local_path)
      with OpenKey(self.hive, key_name) as key:
        self.value, self.value_type = QueryValueEx(key, value_name)

      # We are a value and therefore not a directory.
      self.is_directory = False
    except exceptions.WindowsError:
      try:
        # Try to get the default value for this key
        with OpenKey(self.hive, self.local_path) as key:

          # Check for default value.
          try:
            self.value, self.value_type = QueryValueEx(key, "")
          except exceptions.WindowsError:
            # Empty default value
            self.value = ""
            self.value_type = _winreg.REG_NONE

      except exceptions.WindowsError:
        raise IOError("Unable to open key %s" % self.key_name)

  def Stat(self):
    return self._Stat("", self.value, self.value_type)

  def _Stat(self, name, value, value_type):
    response = rdfvalue.StatEntry()
    response_pathspec = self.pathspec.Copy()

    # No matter how we got here, there is no need to do case folding from now on
    # since this is the exact filename casing.
    response_pathspec.path_options = rdfvalue.PathSpec.Options.CASE_LITERAL

    response_pathspec.last.path = utils.JoinPath(
        response_pathspec.last.path, name)
    response.pathspec = response_pathspec

    if self.IsDirectory():
      response.st_mode = stat.S_IFDIR
    else:
      response.st_mode = stat.S_IFREG

    response.st_mtime = self.last_modified
    response.st_size = len(utils.SmartStr(value))
    if value_type is not None:
      response.registry_type = self.registry_map.get(value_type, 0)
      response.registry_data = rdfvalue.DataBlob().SetValue(value)
    return response

  def ListNames(self):
    """List the names of all keys and values."""
    if not self.IsDirectory(): return

    # Handle the special case where no hive is specified and just list the hives
    if self.hive is None:
      for name in dir(_winreg):
        if name.startswith("HKEY_"):
          yield name

      return

    try:
      with OpenKey(self.hive, self.local_path) as key:
        (self.number_of_keys, self.number_of_values,
         self.last_modified) = QueryInfoKey(key)

        self.last_modified = self.last_modified / 10000000 - WIN_UNIX_DIFF_MSECS
        # First keys
        for i in range(self.number_of_keys):
          try:
            yield EnumKey(key, i)
          except exceptions.WindowsError:
            pass

        # Now Values
        for i in range(self.number_of_values):
          try:
            name, unused_value, unused_value_type = EnumValue(key, i)

            yield name
          except exceptions.WindowsError:
            pass

    except exceptions.WindowsError as e:
      raise IOError("Unable to list key %s: %s" % (self.key_name, e))

  def ListFiles(self):
    """A generator of all keys and values."""
    if not self.IsDirectory(): return

    if self.hive is None:
      for name in dir(_winreg):
        if name.startswith("HKEY_"):
          response = rdfvalue.StatEntry(
              st_mode=stat.S_IFDIR)
          response_pathspec = self.pathspec.Copy()
          response_pathspec.last.path = utils.JoinPath(
              response_pathspec.last.path, name)
          response.pathspec = response_pathspec

          yield response
      return

    try:
      with OpenKey(self.hive, self.local_path) as key:
        (self.number_of_keys, self.number_of_values,
         self.last_modified) = QueryInfoKey(key)

        self.last_modified = self.last_modified / 10000000 - WIN_UNIX_DIFF_MSECS
        # First keys - These will look like directories.
        for i in range(self.number_of_keys):
          try:
            name = EnumKey(key, i)
            key_name = utils.JoinPath(self.local_path, name)

            try:
              # Store the default value in the stat response for values.
              with OpenKey(self.hive, key_name) as subkey:
                value, value_type = QueryValueEx(subkey, "")
            except exceptions.WindowsError:
              value, value_type = None, None

            response = self._Stat(name, value, value_type)
            # Keys look like Directories in the VFS.
            response.st_mode = stat.S_IFDIR

            yield response
          except exceptions.WindowsError:
            pass

        # Now Values - These will look like files.
        for i in range(self.number_of_values):
          try:
            name, value, value_type = EnumValue(key, i)
            response = self._Stat(name, value, value_type)

            # Values look like files in the VFS.
            response.st_mode = stat.S_IFREG

            yield response

          except exceptions.WindowsError:
            pass
    except exceptions.WindowsError as e:
      raise IOError("Unable to list key %s: %s" % (self.key_name, e))

  def IsDirectory(self):
    return self.is_directory

  def Read(self, length):
    if not self.fd:
      self.fd = StringIO.StringIO(utils.SmartStr(self.value))
    return self.fd.read(length)

  def Seek(self, offset, whence=0):
    if not self.fd:
      self.fd = StringIO.StringIO(utils.SmartStr(self.value))
    return self.fd.seek(offset, whence)
