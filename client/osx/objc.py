#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Interface to Objective C libraries on OS X."""



import ctypes
import ctypes.util


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


class Error(Exception):
  """Base error class."""


class ErrorLibNotFound(Error):
  """Couldn't find specified library."""


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
        ('CFArrayGetCount',
         [ctypes.c_void_p],
         ctypes.c_int32),
        ('CFArrayGetValueAtIndex',
         [ctypes.c_void_p, ctypes.c_int32],
         ctypes.c_void_p),
        ('CFDictionaryGetCount',
         [ctypes.c_void_p],
         ctypes.c_long),
        ('CFDictionaryGetCountOfKey',
         [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_int32),
        ('CFDictionaryGetValue',
         [ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p),
        ('CFDictionaryGetKeysAndValues',
         [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
         None),
        ('CFNumberCreate',
         [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
         ctypes.c_void_p),
        ('CFNumberGetValue',
         [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p],
         ctypes.c_int32),
        ('CFNumberGetTypeID',
         [],
         ctypes.c_ulong),
        ('CFStringCreateWithCString',
         [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32],
         ctypes.c_void_p),
        ('CFStringGetCString',
         [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32, ctypes.c_int32],
         ctypes.c_int32),
        ('CFStringGetLength',
         [ctypes.c_void_p],
         ctypes.c_int32),
        ('CFStringGetTypeID',
         [],
         ctypes.c_ulong),
        ('CFBooleanGetValue',
         [ctypes.c_void_p],
         ctypes.c_byte),
        ('CFBooleanGetTypeID',
         [],
         ctypes.c_ulong),
        ('CFRelease',
         [ctypes.c_void_p],
         None),
        ('CFRetain',
         [ctypes.c_void_p],
         ctypes.c_void_p),
        ('CFGetTypeID',
         [ctypes.c_void_p],
         ctypes.c_ulong)
    ]

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
    cf_number = self.dll.CFNumberCreate(
        CF_DEFAULT_ALLOCATOR, INT64, ctypes.byref(c_num))
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
                                              pystring.encode('utf8'),
                                              UTF8)

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
    self.cftable.append(
        ('SCDynamicStoreCopyProxies',
         [ctypes.c_void_p],
         ctypes.c_void_p)
    )

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
        ('SMCopyAllJobDictionaries',
         [ctypes.c_void_p],
         ctypes.c_void_p),
    )

    self.dll = SetCTypesForLibrary('ServiceManagement', self.cftable)

  def SMGetJobDictionaries(self, domain='kSMDomainSystemLaunchd'):
    """Copy all Job Dictionaries from the ServiceManagement.

    Args:
      domain: The name of a constant in Foundation referencing the domain.
              Will copy all launchd services by default.

    Returns:
      A marshalled python list of dicts containing the job dictionaries.
    """
    cfstring_launchd = ctypes.c_void_p.in_dll(
        self.dll, domain)
    return CFArray(
        self.dll.SMCopyAllJobDictionaries(cfstring_launchd))


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
      raise TypeError(
          'CFBoolean initializer must be objc Boolean')
    super(CFBoolean, self).__init__(ptr)

  @property
  def value(self):
    bool_const = self.dll.CFBooleanGetValue(self)
    if bool_const == 0:
      return False
    else:
      return True

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
    elif isinstance(obj, basestring):
      super(CFString, self).__init__(None)
      self.ref = self.PyStringToCFString(obj)
    else:
      raise TypeError('CFString initializer must be python or objc string.')

  @property
  def value(self):
    return self.CFStringToPystring(self)

  def __len__(self):
    return self.dll.CFArrayGetCount(self.ref)

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
      raise IndexError(
          'index must be between {0} and {1}'.format(0, len(self) - 1))
    obj = self.dll.CFArrayGetValueAtIndex(self.ref, index)
    return self.WrapCFTypeInPython(obj)

  def __repr__(self):
    return str(list(self))


class CFDictionary(CFType):
  """Wrapper class for CFDictionary to behave like a python dict."""

  def __init__(self, ptr):
    super(CFDictionary, self).__init__(ptr)
    self.dll.CFRetain(ptr)

  def __len__(self):
    return self.dll.CFArrayGetCount(self)

  def __getitem__(self, key):
    if isinstance(key, CFType):
      cftype_key = key
    if isinstance(key, basestring):
      cftype_key = CFString(key)
    elif isinstance(key, (int, long)):
      cftype_key = CFNumber(key)
    elif isinstance(key, ctypes.c_void_p):
      cftype_key = key
    else:
      raise TypeError(
          'CFDictionary wrapper only supports string, int and objc values')
    obj = ctypes.c_void_p(
        self.dll.CFDictionaryGetValue(self, cftype_key))
    try:
      obj = self.WrapCFTypeInPython(obj)
    except TypeError:
      obj = None
    return obj

  def get(self, key, default=''):
    """For compability reasons this methods returns stringified values."""
    obj = self.__getitem__(key)
    if obj is None:
      obj = default
    return str(obj)

  def __repr__(self):
    representation = '{'
    size = len(self)
    keys = (ctypes.c_void_p * size)()
    values = (ctypes.c_void_p * size)()
    self.dll.CFDictionaryGetKeysAndValues(self.ref, keys, values)
    for index in xrange(size):
      key = self.WrapCFTypeInPython(keys[index])
      value = self.WrapCFTypeInPython(values[index])
      representation += '{0}:{1},'.format(str(key), str(value))
    representation += '}'
    return representation
