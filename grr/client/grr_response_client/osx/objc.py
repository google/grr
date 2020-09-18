#!/usr/bin/env python
# Lint as: python3
"""Interface to Objective C libraries on OS X."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import ctypes.util
from typing import Text

# kCFStringEncodingUTF8
UTF8 = 134217984

# kCFNumberSInt32Type
INT32 = 3

# kCFNumberSInt64Type
INT64 = 4

# Objective C BOOL is a signed byte
BOOL = ctypes.c_byte

# kCFAllocatorDefault
CF_DEFAULT_ALLOCATOR = None

# kCFURLPOSIXPathStyle
POSIX_PATH_STYLE = 0

# kOSReturnSuccess
OS_SUCCESS = None


class Error(Exception):
  """Base error class."""


class ErrorLibNotFound(Error):
  """Couldn't find specified library."""


def FilterFnTable(fn_table, symbol):
  """Remove a specific symbol from a fn_table."""
  new_table = list()
  for entry in fn_table:
    # symbol[0] is a str with the symbol name
    if entry[0] != symbol:
      new_table.append(entry)
  return new_table


def LoadLibrary(libname: str) -> ctypes.CDLL:
  """Loads a CDLL by searching for the library name in well-known locations."""
  # First, attempt to load the library from the path returned by find_library.
  # This works up to macOS 11 (see https://bugs.python.org/issue41179). As
  # fallback, try to load the library directly from well-known locations to
  # work around the macOS 11 bug.
  paths = [
      ctypes.util.find_library(libname) or libname,
      '/System/Library/Frameworks/{0}.framework/{0}',
      '/usr/lib/{0}.dylib',
  ]

  for libpath in paths:
    try:
      return ctypes.cdll.LoadLibrary(libpath.format(libname))
    except OSError:
      pass

  raise ErrorLibNotFound('Library {} not found'.format(libname))


def _SetCTypesForLibrary(libname, fn_table):
  """Set function argument types and return types for an ObjC library.

  Args:
    libname: Library name string
    fn_table: List of (function, [arg types], return types) tuples
  Returns:
    ctypes.CDLL with types set according to fn_table
  Raises:
    ErrorLibNotFound: Can't find specified lib
  """
  lib = LoadLibrary(libname)

  # We need to define input / output parameters for all functions we use
  for (function, args, result) in fn_table:
    f = getattr(lib, function)
    f.argtypes = args
    f.restype = result

  return lib


class Foundation(object):
  """ObjC Foundation library wrapper."""

  dll = None

  @classmethod
  def _LoadLibrary(cls, libname, cftable):
    # Cache the library to only load it once.
    if cls.dll is None:
      cls.dll = _SetCTypesForLibrary(libname, cftable)

  def __init__(self):
    self.cftable = [
        ('CFArrayGetCount', [ctypes.c_void_p], ctypes.c_int32),
        ('CFArrayGetValueAtIndex', [ctypes.c_void_p, ctypes.c_int32],
         ctypes.c_void_p),
        ('CFDictionaryGetCount', [ctypes.c_void_p], ctypes.c_long),
        ('CFDictionaryGetCountOfKey', [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_int32),
        ('CFDictionaryGetValue', [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p),
        ('CFDictionaryGetKeysAndValues',
         [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p], None),
        ('CFNumberCreate', [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p),
        ('CFNumberGetValue', [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p],
         ctypes.c_int32),
        ('CFNumberGetTypeID', [], ctypes.c_ulong),
        ('CFStringCreateWithCString',
         [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32], ctypes.c_void_p),
        ('CFStringGetCString',
         [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32, ctypes.c_int32],
         ctypes.c_int32),
        ('CFStringGetLength', [ctypes.c_void_p], ctypes.c_int32),
        ('CFStringGetTypeID', [], ctypes.c_ulong),
        ('CFBooleanGetValue', [ctypes.c_void_p], ctypes.c_byte),
        ('CFBooleanGetTypeID', [], ctypes.c_ulong),
        ('CFRelease', [ctypes.c_void_p], None),
        ('CFRetain', [ctypes.c_void_p], ctypes.c_void_p),
        ('CFGetTypeID', [ctypes.c_void_p], ctypes.c_ulong),
        ('CFURLCreateWithFileSystemPath',
         [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int],
         ctypes.c_long),
        ('CFURLCopyFileSystemPath', [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p)
    ]  # pyformat: disable

    self._LoadLibrary('Foundation', self.cftable)

  def CFStringToPystring(self, value) -> Text:
    length = (self.dll.CFStringGetLength(value) * 4) + 1
    buff = ctypes.create_string_buffer(length)
    self.dll.CFStringGetCString(value, buff, length * 4, UTF8)
    return buff.value.decode('utf-8')

  def IntToCFNumber(self, num):
    if not isinstance(num, int):
      raise TypeError('CFNumber can only be created from int')
    c_num = ctypes.c_int64(num)
    cf_number = self.dll.CFNumberCreate(CF_DEFAULT_ALLOCATOR, INT64,
                                        ctypes.byref(c_num))
    return cf_number

  def CFNumToInt32(self, num):
    tmp = ctypes.c_int32(0)
    result_ptr = ctypes.pointer(tmp)
    self.dll.CFNumberGetValue(num, INT32, result_ptr)
    return result_ptr[0]

  def CFNumToInt64(self, num):
    tmp = ctypes.c_int64(0)
    result_ptr = ctypes.pointer(tmp)
    self.dll.CFNumberGetValue(num, INT64, result_ptr)
    return result_ptr[0]

  def CFDictRetrieve(self, dictionary, key):
    ptr = ctypes.c_void_p.in_dll(self.dll, key)
    return self.dll.CFDictionaryGetValue(dictionary, ptr)

  def PyStringToCFString(self, pystring):
    return self.dll.CFStringCreateWithCString(CF_DEFAULT_ALLOCATOR,
                                              pystring.encode('utf8'), UTF8)

  def WrapCFTypeInPython(self, obj):
    """Package a CoreFoundation object in a Python wrapper.

    Args:
      obj: The CoreFoundation object.
    Returns:
      One of CFBoolean, CFNumber, CFString, CFDictionary, CFArray.
    Raises:
      TypeError: If the type is not supported.
    """
    obj_type = self.dll.CFGetTypeID(obj)
    if obj_type == self.dll.CFBooleanGetTypeID():
      return CFBoolean(obj)
    elif obj_type == self.dll.CFNumberGetTypeID():
      return CFNumber(obj)
    elif obj_type == self.dll.CFStringGetTypeID():
      return CFString(obj)
    elif obj_type == self.dll.CFDictionaryGetTypeID():
      return CFDictionary(obj)
    elif obj_type == self.dll.CFArrayGetTypeID():
      return CFArray(obj)
    else:
      raise TypeError('Unknown type for object: {0}'.format(obj))


class SystemConfiguration(Foundation):
  """SystemConfiguration Framework wrapper.

  Apple doco:
    http://goo.gl/NGRj9
  """

  def __init__(self):
    super().__init__()
    self.cftable.append(('SCDynamicStoreCopyProxies', [ctypes.c_void_p],
                         ctypes.c_void_p))

    self.dll = _SetCTypesForLibrary('SystemConfiguration', self.cftable)


class ServiceManagement(Foundation):
  """ServiceManagement Framework wrapper.

  Apple doco:
    http://goo.gl/qVHSd
  """

  def __init__(self):
    super().__init__()
    self.cftable.append(
        # Only available 10.6 and later
        ('SMCopyAllJobDictionaries', [ctypes.c_void_p], ctypes.c_void_p),)

    self.dll = _SetCTypesForLibrary('ServiceManagement', self.cftable)

  def SMGetJobDictionaries(self, domain='kSMDomainSystemLaunchd'):
    """Copy all Job Dictionaries from the ServiceManagement.

    Args:
      domain: The name of a constant in Foundation referencing the domain.
              Will copy all launchd services by default.

    Returns:
      A marshalled python list of dicts containing the job dictionaries.
    """
    cfstring_launchd = ctypes.c_void_p.in_dll(self.dll, domain)
    return CFArray(self.dll.SMCopyAllJobDictionaries(cfstring_launchd))


class CFType(Foundation):
  """Wrapper class for Core Foundation Types."""

  def __init__(self, ref):
    super().__init__()
    self.ref = ref

  def __del__(self):
    # Now it can be deleted, as we don't use it any more
    self.dll.CFRelease(self.ref)

  def __repr__(self):
    return '{0}:{1}'.format(self.__class__.__name__, self.ref)

  @property
  def _as_parameter_(self):
    """Ctypes used this value when passed as parameter to a function."""
    return self.ref


class CFBoolean(CFType):
  """Readonly Wrapper class for CoreFoundation CFBoolean."""

  def __init__(self, obj=0):
    if isinstance(obj, (ctypes.c_void_p, int)):
      ptr = obj
    else:
      raise TypeError('CFBoolean initializer must be objc Boolean')
    super().__init__(ptr)

  @property
  def value(self):
    bool_const = self.dll.CFBooleanGetValue(self)
    if bool_const == 0:
      return False
    else:
      return True

  def __bool__(self):
    return self.value

  # TODO: Remove after support for Python 2 is dropped.
  __nonzero__ = __bool__

  def __repr__(self):
    return str(self.value)


class CFNumber(CFType):
  """Wrapper class for CoreFoundation CFNumber to behave like a python int."""

  def __init__(self, obj=0):
    if isinstance(obj, ctypes.c_void_p):
      super().__init__(obj)
      self.dll.CFRetain(obj)
    elif isinstance(obj, int):
      super().__init__(None)
      self.ref = ctypes.c_void_p(self.IntToCFNumber(obj))
    else:
      raise TypeError(
          'CFNumber initializer must be python int or objc CFNumber.')

  def __int__(self):
    return self.value

  @property
  def value(self):
    return self.CFNumToInt32(self.ref)

  def __repr__(self):
    return str(self.value)


class CFString(CFType):
  """Wrapper class for CFString to behave like a python string."""

  def __init__(self, obj=''):
    """Can initialize CFString with python or objc strings."""
    if isinstance(obj, (ctypes.c_void_p, int)):
      super().__init__(obj)
      self.dll.CFRetain(obj)
    elif isinstance(obj, str):
      super().__init__(None)
      self.ref = self.PyStringToCFString(obj)
    else:
      raise TypeError('CFString initializer must be python or objc string.')

  @property
  def value(self) -> Text:
    return self.CFStringToPystring(self)

  def __len__(self):
    return self.dll.CFArrayGetCount(self.ref)

  def __str__(self) -> Text:
    return self.value

  def __repr__(self):
    return self.value


class CFArray(CFType):
  """Wrapper class for CFArray to behave like a python list."""

  def __init__(self, ptr):
    super().__init__(ptr)
    self.dll.CFRetain(ptr)

  def __len__(self):
    return self.dll.CFArrayGetCount(self.ref)

  def __getitem__(self, index):
    if not isinstance(index, int):
      raise TypeError('index must be an integer')
    if (index < 0) or (index >= len(self)):
      raise IndexError('index must be between {0} and {1}'.format(
          0,
          len(self) - 1))
    obj = self.dll.CFArrayGetValueAtIndex(self.ref, index)
    return self.WrapCFTypeInPython(obj)

  def __repr__(self):
    return str(list(self))


class CFDictionary(CFType):
  """Wrapper class for CFDictionary to behave like a python dict."""

  def __init__(self, ptr):
    super().__init__(ptr)
    self.dll.CFRetain(ptr)

  def __contains__(self, key):
    value = self.__getitem__(key)
    return value is not None

  def __len__(self):
    return self.dll.CFArrayGetCount(self)

  def __getitem__(self, key):
    if isinstance(key, CFType):
      cftype_key = key
    if isinstance(key, str):
      cftype_key = CFString(key)
    elif isinstance(key, int):
      cftype_key = CFNumber(key)
    elif isinstance(key, ctypes.c_void_p):
      cftype_key = key
    else:
      raise TypeError(
          'CFDictionary wrapper only supports string, int and objc values')
    obj = ctypes.c_void_p(self.dll.CFDictionaryGetValue(self, cftype_key))

    # Detect null pointers and avoid crashing WrapCFTypeInPython
    if not obj:
      obj = None
    else:
      try:
        obj = self.WrapCFTypeInPython(obj)
      except TypeError:
        obj = None
    return obj

  # pylint: disable=g-bad-name
  def get(self, key, default='', stringify=True):
    """Returns dictionary values or default.

    Args:
      key: string. Dictionary key to look up.
      default: string. Return this value if key not found.
      stringify: bool. Force all return values to string for compatibility
                 reasons.
    Returns:
      python-wrapped CF object or default if not found.
    """
    obj = self.__getitem__(key)
    if obj is None:
      obj = default
    elif stringify:
      obj = str(obj)
    return obj

  def items(self):
    size = len(self)
    keys = (ctypes.c_void_p * size)()
    values = (ctypes.c_void_p * size)()
    self.dll.CFDictionaryGetKeysAndValues(self.ref, keys, values)
    for index in range(size):
      key = self.WrapCFTypeInPython(keys[index])
      value = self.WrapCFTypeInPython(values[index])
      yield key, value

  # pylint: enable=g-bad-name

  def __repr__(self):
    representation = '{'
    for key, value in self.items():
      representation += '{0}:{1},'.format(str(key), str(value))
    representation += '}'
    return representation
