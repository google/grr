#!/usr/bin/env python
"""Interface to Objective C libraries on OS X."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import ctypes.util
import logging
import subprocess


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import string_types
from past.builtins import long

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


def SetCTypesForLibrary(libname, fn_table):
  """Set function argument types and return types for an ObjC library.

  Args:
    libname: Library name string
    fn_table: List of (function, [arg types], return types) tuples
  Returns:
    ctypes.CDLL with types set according to fn_table
  Raises:
    ErrorLibNotFound: Can't find specified lib
  """
  libpath = ctypes.util.find_library(libname)
  if not libpath:
    raise ErrorLibNotFound('Library %s not found' % libname)

  lib = ctypes.cdll.LoadLibrary(libpath)

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
  def LoadLibrary(cls, libname, cftable):
    # Cache the library to only load it once.
    if cls.dll is None:
      cls.dll = SetCTypesForLibrary(libname, cftable)

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

    self.LoadLibrary('Foundation', self.cftable)

  def CFStringToPystring(self, value):
    length = (self.dll.CFStringGetLength(value) * 4) + 1
    buff = ctypes.create_string_buffer(length)
    self.dll.CFStringGetCString(value, buff, length * 4, UTF8)
    return unicode(buff.value, 'utf8')

  def IntToCFNumber(self, num):
    if not isinstance(num, (int, long)):
      raise TypeError('CFNumber can only be created from int or long')
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
    super(SystemConfiguration, self).__init__()
    self.cftable.append(('SCDynamicStoreCopyProxies', [ctypes.c_void_p],
                         ctypes.c_void_p))

    self.dll = SetCTypesForLibrary('SystemConfiguration', self.cftable)


class ServiceManagement(Foundation):
  """ServiceManagement Framework wrapper.

  Apple doco:
    http://goo.gl/qVHSd
  """

  def __init__(self):
    super(ServiceManagement, self).__init__()
    self.cftable.append(
        # Only available 10.6 and later
        ('SMCopyAllJobDictionaries', [ctypes.c_void_p], ctypes.c_void_p),)

    self.dll = SetCTypesForLibrary('ServiceManagement', self.cftable)

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
    super(CFType, self).__init__()
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
    super(CFBoolean, self).__init__(ptr)

  @property
  def value(self):
    bool_const = self.dll.CFBooleanGetValue(self)
    if bool_const == 0:
      return False
    else:
      return True

  def __bool__(self):
    return self.value

  def __nonzero__(self):
    return self.value

  def __repr__(self):
    return str(self.value)


class CFNumber(CFType):
  """Wrapper class for CoreFoundation CFNumber to behave like a python int."""

  def __init__(self, obj=0):
    if isinstance(obj, ctypes.c_void_p):
      super(CFNumber, self).__init__(obj)
      self.dll.CFRetain(obj)
    elif isinstance(obj, (int, long)):
      super(CFNumber, self).__init__(None)
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
      super(CFString, self).__init__(obj)
      self.dll.CFRetain(obj)
    elif isinstance(obj, string_types):
      super(CFString, self).__init__(None)
      self.ref = self.PyStringToCFString(obj)
    else:
      raise TypeError('CFString initializer must be python or objc string.')

  @property
  def value(self):
    return self.CFStringToPystring(self)

  def __len__(self):
    return self.dll.CFArrayGetCount(self.ref)

  def __unicode__(self):
    return unicode(self.value)

  def __repr__(self):
    return self.value


class CFArray(CFType):
  """Wrapper class for CFArray to behave like a python list."""

  def __init__(self, ptr):
    super(CFArray, self).__init__(ptr)
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
    super(CFDictionary, self).__init__(ptr)
    self.dll.CFRetain(ptr)

  def __contains__(self, key):
    value = self.__getitem__(key)
    return value is not None

  def __len__(self):
    return self.dll.CFArrayGetCount(self)

  def __getitem__(self, key):
    if isinstance(key, CFType):
      cftype_key = key
    if isinstance(key, string_types):
      cftype_key = CFString(key)
    elif isinstance(key, (int, long)):
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

  def iteritems(self):
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
    for key, value in iteritems(self):
      representation += '{0}:{1},'.format(str(key), str(value))
    representation += '}'
    return representation


class KextManager(Foundation):
  """Loads and unloads kernel extensions.

  Apple documentations:
    http://goo.gl/HukWV
  """

  def __init__(self):
    super(KextManager, self).__init__()
    self.kext_functions = [
        # Only available 10.6 and later
        ('KextManagerLoadKextWithURL', [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p),
        # Only available 10.7 and later
        ('KextManagerUnloadKextWithIdentifier', [ctypes.c_void_p],
         ctypes.c_void_p)
    ]
    self.iokit = self.SafeLoadKextManager(self.kext_functions)

  def SafeLoadKextManager(self, fn_table):
    """Load the kextmanager, replacing unavailable symbols."""
    dll = None
    try:
      dll = SetCTypesForLibrary('IOKit', fn_table)
    except AttributeError as ae:
      if 'KextManagerUnloadKextWithIdentifier' in str(ae):
        # Try without this symbol, as it is not available on 10.6
        logging.debug('Using legacy kextunload')
        dll = self.SafeLoadKextManager(
            FilterFnTable(fn_table, 'KextManagerUnloadKextWithIdentifier'))
        dll.KextManagerUnloadKextWithIdentifier = self.LegacyKextunload
      elif 'KextManagerLoadKextWithURL' in str(ae):
        logging.debug('Using legacy kextload')
        dll = self.SafeLoadKextManager(
            FilterFnTable(fn_table, 'KextManagerLoadKextWithURL'))
        dll.KextManagerLoadKextWithURL = self.LegacyKextload
      else:
        raise OSError('Can\'t resolve KextManager symbols:{0}'.format(str(ae)))

    return dll

  def LegacyKextload(self, cf_bundle_url, dependency_kext):
    """Load a kext by forking into kextload."""
    _ = dependency_kext
    error_code = OS_SUCCESS
    cf_path = self.dll.CFURLCopyFileSystemPath(cf_bundle_url, POSIX_PATH_STYLE)
    path = self.CFStringToPystring(cf_path)
    self.dll.CFRelease(cf_path)
    try:
      subprocess.check_call(['/sbin/kextload', path])
    except subprocess.CalledProcessError as cpe:
      logging.debug('failed to load %s:%s', path, str(cpe))
      error_code = -1
    return error_code

  def LegacyKextunload(self, cf_bundle_identifier):
    """Unload a kext by forking into kextunload."""
    error_code = OS_SUCCESS
    bundle_identifier = self.CFStringToPystring(cf_bundle_identifier)
    try:
      subprocess.check_call(['/sbin/kextunload', '-b', bundle_identifier])
    except subprocess.CalledProcessError as cpe:
      logging.debug('failed to unload %s:%s', bundle_identifier, str(cpe))
      error_code = -1
    return error_code
