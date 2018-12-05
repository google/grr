#!/usr/bin/env python
"""This file contains various utility classes used by GRR."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import array
import base64
import collections
import errno
import functools
import getpass
import io
import os
import pipes
import platform
import random
import re
import shutil
import socket
import stat
import struct
import tarfile
import tempfile
import threading
import time
import weakref
import zipfile
import zlib


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
import psutil
import queue

from typing import Any, Optional, Text

from grr_response_core.lib.util import precondition


class Error(Exception):
  pass


class ParsingError(Error):
  pass


def Proxy(f):
  """A helper to create a proxy method in a class."""

  def Wrapped(self, *args):
    return getattr(self, f)(*args)

  return Wrapped


class TempDirectory(object):
  """A self cleaning temporary directory.

  Do not use this function for any client related temporary files! Use
  the functionality provided by client_actions/tempfiles.py instead.
  """

  def __enter__(self):
    self.name = tempfile.mkdtemp()

    return self.name

  def __exit__(self, exc_type, exc_value, traceback):
    shutil.rmtree(self.name, True)


# This is a synchronize decorator.
def Synchronized(f):
  """Synchronization decorator."""

  @functools.wraps(f)
  def NewFunction(self, *args, **kw):
    with self.lock:
      return f(self, *args, **kw)

  return NewFunction


class InterruptableThread(threading.Thread):
  """A class which exits once the main thread exits."""

  def __init__(self,
               target=None,
               args=None,
               kwargs=None,
               sleep_time=10,
               name = None,
               **kw):
    self.exit = False
    self.last_run = 0
    self.target = target
    self.args = args or ()
    self.kwargs = kwargs or {}
    self.sleep_time = sleep_time
    if name is None:
      raise ValueError("Please name your threads.")

    # TODO(hanuszczak): Incorrect type specification for the `name` param.
    # pytype: disable=wrong-arg-count
    super(InterruptableThread, self).__init__(name=name, **kw)
    # pytype: enable=wrong-arg-count

    # Do not hold up program exit
    self.daemon = True

  def Iterate(self):
    """This will be repeatedly called between sleeps."""

  def Stop(self):
    self.exit = True

  def run(self):
    # When the main thread exits, the time module might disappear and be already
    # None. We take a local reference to the functions we need.
    sleep = time.sleep
    now = time.time

    while not self.exit:
      if self.target:
        self.target(*self.args, **self.kwargs)
      else:
        self.Iterate()

      # Implement interruptible sleep here.
      self.last_run = now()

      # Exit if the main thread disappears.
      while (time and not self.exit and
             now() < self.last_run + self.sleep_time):
        sleep(1)


class Node(object):
  """An entry to a linked list."""
  next = None
  prev = None
  data = None

  def __init__(self, key, data):
    self.data = data
    self.key = key

  def __str__(self):
    return "Node %s: %s" % (self.key, SmartStr(self.data))

  def __repr__(self):
    return SmartStr(self)


# TODO(user):pytype: self.next and self.prev are assigned to self but then
# are used in AppendNode in a very different way. Should be redesigned.
# pytype: disable=attribute-error
class LinkedList(object):
  """A simple doubly linked list used for fast caches."""

  def __init__(self):
    # We are the head node.
    self.next = self.prev = self
    self.size = 0

  def AppendNode(self, node):
    self.size += 1
    last_node = self.prev

    last_node.next = node
    node.prev = last_node
    node.next = self
    self.prev = node

  def PopLeft(self):
    """Returns the head node and removes it from the list."""
    if self.next is self:
      raise IndexError("Pop from empty list.")

    first_node = self.next
    self.Unlink(first_node)
    return first_node

  def Pop(self):
    """Returns the tail node and removes it from the list."""
    if self.prev is self:
      raise IndexError("Pop from empty list.")

    last_node = self.prev
    self.Unlink(last_node)
    return last_node

  def Unlink(self, node):
    """Removes a given node from the list."""
    self.size -= 1

    node.prev.next = node.next
    node.next.prev = node.prev
    node.next = node.prev = None

  def __iter__(self):
    p = self.next
    while p is not self:
      yield p
      p = p.next

  def __len__(self):
    return self.size

  def __str__(self):
    p = self.next
    s = []
    while p is not self:
      s.append(str(p.data))
      p = p.next

    return "[" + ", ".join(s) + "]"

  def Print(self):
    p = self.next
    while p is not self:
      print("%s: prev %r next %r\n" % (p.data, p.prev, p.next))
      p = p.next


# pytype: enable=attribute-error


class FastStore(object):
  """This is a cache which expires objects in oldest first manner.

  This implementation first appeared in PyFlag.
  """

  def __init__(self, max_size=10):
    """Constructor.

    Args:
       max_size: The maximum number of objects held in cache.
    """
    # This class implements a LRU cache which needs fast updates of the LRU
    # order for random elements. This is usually implemented by using a
    # dict for fast lookups and a linked list for quick deletions / insertions.
    self._age = LinkedList()
    self._hash = {}
    self._limit = max_size
    self.lock = threading.RLock()

  def KillObject(self, obj):
    """Perform cleanup on objects when they expire.

    Should be overridden by classes which need to perform special cleanup.
    Args:
      obj: The object which was stored in the cache and is now expired.
    """

  @Synchronized
  def __iter__(self):
    return iter([(key, n.data) for key, n in iteritems(self._hash)])

  @Synchronized
  def Expire(self):
    """Expires old cache entries."""
    while len(self._age) > self._limit:
      node = self._age.PopLeft()
      self._hash.pop(node.key, None)
      self.KillObject(node.data)

  @Synchronized
  def Put(self, key, obj):
    """Add the object to the cache."""
    # Remove the old entry if it is there.
    node = self._hash.pop(key, None)
    if node:
      self._age.Unlink(node)

    # Make a new node and insert it.
    node = Node(key=key, data=obj)
    self._hash[key] = node
    self._age.AppendNode(node)

    self.Expire()

    return key

  @Synchronized
  def ExpireObject(self, key):
    """Expire a specific object from cache."""
    node = self._hash.pop(key, None)
    if node:
      self._age.Unlink(node)
      self.KillObject(node.data)

      return node.data

  @Synchronized
  def ExpireRegEx(self, regex):
    """Expire all the objects with the key matching the regex."""
    reg = re.compile(regex)
    for key in list(self._hash):
      if reg.match(key):
        self.ExpireObject(key)

  @Synchronized
  def ExpirePrefix(self, prefix):
    """Expire all the objects with the key having a given prefix."""
    for key in list(self._hash):
      if key.startswith(prefix):
        self.ExpireObject(key)

  @Synchronized
  def Pop(self, key):
    """Remove the object from the cache completely."""
    node = self._hash.get(key)

    if node:
      del self._hash[key]
      self._age.Unlink(node)

      return node.data

  @Synchronized
  def Get(self, key):
    """Fetch the object from cache.

    Objects may be flushed from cache at any time. Callers must always
    handle the possibility of KeyError raised here.

    Args:
      key: The key used to access the object.

    Returns:
      Cached object.

    Raises:
      KeyError: If the object is not present in the cache.
    """
    if key not in self._hash:
      raise KeyError(key)

    node = self._hash[key]

    self._age.Unlink(node)
    self._age.AppendNode(node)

    return node.data

  @Synchronized
  def __contains__(self, obj):
    return obj in self._hash

  @Synchronized
  def __getitem__(self, key):
    return self.Get(key)

  @Synchronized
  def Flush(self):
    """Flush all items from cache."""
    while self._age:
      node = self._age.PopLeft()
      self.KillObject(node.data)

    self._hash = dict()

  def __len__(self):
    return len(self._hash)


class TimeBasedCache(FastStore):
  """A Cache which expires based on time."""

  active_caches = None
  house_keeper_thread = None

  def __init__(self, max_size=10, max_age=600):
    """Constructor.

    This cache will refresh the age of the cached object as long as they are
    accessed within the allowed age. The age refers to the time since it was
    last touched.

    Args:
      max_size: The maximum number of objects held in cache.
      max_age: The maximum length of time an object is considered alive.
    """
    super(TimeBasedCache, self).__init__(max_size)
    self.max_age = max_age

    def HouseKeeper():
      """A housekeeper thread which expunges old objects."""
      if not time:
        # This might happen when the main thread exits, we don't want to raise.
        return

      now = time.time()

      for cache in TimeBasedCache.active_caches:
        # Only expunge while holding the lock on the data store.
        with cache.lock:
          # pylint: disable=protected-access
          # We need to take a copy of the value list because we are changing
          # this dict during the iteration.
          for node in list(itervalues(cache._hash)):
            timestamp, obj = node.data

            # Expire the object if it is too old.
            if timestamp + cache.max_age < now:
              cache.KillObject(obj)

              cache._age.Unlink(node)
              cache._hash.pop(node.key, None)
          # pylint: enable=protected-access

    if not TimeBasedCache.house_keeper_thread:
      TimeBasedCache.active_caches = weakref.WeakSet()
      # This thread is designed to never finish.
      TimeBasedCache.house_keeper_thread = InterruptableThread(
          name="HouseKeeperThread", target=HouseKeeper)
      TimeBasedCache.house_keeper_thread.start()
    TimeBasedCache.active_caches.add(self)

  @Synchronized
  def Get(self, key):
    now = time.time()
    stored = super(TimeBasedCache, self).Get(key)
    if stored[0] + self.max_age < now:
      raise KeyError("Expired")

    # This updates the timestamp in place to keep the object alive
    stored[0] = now

    return stored[1]

  def Put(self, key, obj):
    super(TimeBasedCache, self).Put(key, [time.time(), obj])


class AgeBasedCache(TimeBasedCache):
  """A cache which holds objects for a maximum length of time.

  This differs from the TimeBasedCache which keeps the objects alive as long as
  they are accessed.
  """

  @Synchronized
  def Get(self, key):
    now = time.time()
    stored = FastStore.Get(self, key)
    if stored[0] + self.max_age < now:
      raise KeyError("Expired")

    return stored[1]


class Struct(object):
  """A baseclass for parsing binary Structs."""

  # Derived classes must initialize this into an array of (format,
  # name) tuples.
  _fields = None

  def __init__(self, data):
    """Parses ourselves from data."""
    format_str = "".join([x[0] for x in self._fields])
    self.size = struct.calcsize(format_str)

    try:
      parsed_data = struct.unpack(format_str, data[:self.size])

    except struct.error:
      raise ParsingError("Unable to parse")

    for i in range(len(self._fields)):
      setattr(self, self._fields[i][1], parsed_data[i])

  def __repr__(self):
    """Produce useful text representation of the Struct."""
    dat = []
    for _, name in self._fields:
      dat.append("%s=%s" % (name, getattr(self, name)))
    return "%s(%s)" % (self.__class__.__name__, ", ".join(dat))

  @classmethod
  def GetSize(cls):
    """Calculate the size of the struct."""
    format_str = "".join([x[0] for x in cls._fields])
    return struct.calcsize(format_str)


def SmartStr(string):
  """Returns a string or encodes a unicode object.

  This function essentially will always return an encoded string. It should be
  used on an interface to the system which must accept a string and not unicode.

  Args:
    string: The string to convert.

  Returns:
    an encoded string.
  """
  if type(string) == unicode:  # pylint: disable=unidiomatic-typecheck
    return string.encode("utf8", "ignore")

  return str(string)


def SmartUnicode(string):
  """Returns a unicode object.

  This function will always return a unicode object. It should be used to
  guarantee that something is always a unicode object.

  Args:
    string: The string to convert.

  Returns:
    a unicode object.
  """
  if type(string) != unicode:  # pylint: disable=unidiomatic-typecheck
    try:
      return string.__unicode__()  # pytype: disable=attribute-error
    except (AttributeError, UnicodeError):
      return str(string).decode("utf8", "ignore")

  return string


def Xor(bytestr, key):
  """Returns a `bytes` object where each byte has been xored with key."""
  # TODO(hanuszczak): Remove this import when string migration is done.
  # pytype: disable=import-error
  from builtins import bytes  # pylint: disable=redefined-builtin, g-import-not-at-top
  # pytype: enable=import-error
  precondition.AssertType(bytestr, bytes)

  # TODO(hanuszczak): This seemingly no-op operation actually changes things.
  # In Python 2 this function receives a `str` object which has different
  # iterator semantics. So we use a `bytes` wrapper from the `future` package to
  # get the Python 3 behaviour. In Python 3 this should be indeed a no-op. Once
  # the migration is completed and support for Python 2 is dropped, this line
  # can be removed.
  bytestr = bytes(bytestr)

  return bytes([byte ^ key for byte in bytestr])


def FormatAsHexString(num, width=None, prefix="0x"):
  """Takes an int and returns the number formatted as a hex string."""
  # Strip "0x".
  hex_str = hex(num)[2:]
  # Strip "L" for long values.
  hex_str = hex_str.replace("L", "")
  if width:
    hex_str = hex_str.rjust(width, "0")
  return "%s%s" % (prefix, hex_str)


def FormatAsTimestamp(timestamp):
  if not timestamp:
    return "-"

  # TODO(hanuszczak): Remove these string conversion functions once support for
  # Python 2 is dropped.
  fmt = str("%Y-%m-%d %H:%M:%S")
  return unicode(time.strftime(fmt, time.gmtime(timestamp)))


def NormalizePath(path, sep="/"):
  """A sane implementation of os.path.normpath.

  The standard implementation treats leading / and // as different leading to
  incorrect normal forms.

  NOTE: Its ok to use a relative path here (without leading /) but any /../ will
  still be removed anchoring the path at the top level (e.g. foo/../../../../bar
  => bar).

  Args:
     path: The path to normalize.
     sep: Separator used.

  Returns:
     A normalized path. In this context normalized means that all input paths
     that would result in the system opening the same physical file will produce
     the same normalized path.
  """
  if not path:
    return sep
  path = SmartUnicode(path)

  path_list = path.split(sep)

  # This is a relative path and the first element is . or ..
  if path_list[0] in [".", "..", ""]:
    path_list.pop(0)

  # Deliberately begin at index 1 to preserve a single leading /
  i = 0

  while True:
    list_len = len(path_list)

    # We begin at the last known good position so we never iterate over path
    # elements which are already examined
    for i in range(i, len(path_list)):
      # Remove /./ form
      if path_list[i] == "." or not path_list[i]:
        path_list.pop(i)
        break

      # Remove /../ form
      elif path_list[i] == "..":
        path_list.pop(i)
        # Anchor at the top level
        if (i == 1 and path_list[0]) or i > 1:
          i -= 1
          path_list.pop(i)
        break

    # If we didnt alter the path so far we can quit
    if len(path_list) == list_len:
      return sep + sep.join(path_list)


def JoinPath(stem="", *parts):
  """A sane version of os.path.join.

  The intention here is to append the stem to the path. The standard module
  removes the path if the stem begins with a /.

  Args:
     stem: The stem to join to.
     *parts: parts of the path to join. The first arg is always the root and
       directory traversal is not allowed.

  Returns:
     a normalized path.
  """
  # Ensure all path components are unicode
  parts = [SmartUnicode(path) for path in parts]

  result = (stem + NormalizePath(u"/".join(parts))).replace("//", "/")
  result = result.rstrip("/")

  return result or "/"


def ShellQuote(value):
  """Escapes the string for the safe use inside shell command line."""
  # TODO(user): replace pipes.quote with shlex.quote when time comes.
  return pipes.quote(SmartUnicode(value))


def Join(*parts):
  """Join (AFF4) paths without normalizing.

  A quick join method that can be used to express the precondition that
  the parts are already normalized.

  Args:
    *parts: The parts to join

  Returns:
    The joined path.
  """

  return "/".join(parts)


def EncodeReasonString(reason):
  return base64.urlsafe_b64encode(SmartStr(reason))


def DecodeReasonString(reason):
  return SmartUnicode(base64.urlsafe_b64decode(SmartStr(reason)))


# Regex chars that should not be in a regex
disallowed_chars = re.compile(r"[[\](){}+*?.$^\\]")


def EscapeRegex(string):
  return re.sub(disallowed_chars, lambda x: "\\" + x.group(0),
                SmartUnicode(string))


def GeneratePassphrase(length=20):
  """Create a 20 char passphrase with easily typeable chars."""
  valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  valid_chars += "0123456789 ,-_&$#"
  return "".join(random.choice(valid_chars) for i in range(length))


def PassphraseCallback(verify=False,
                       prompt1="Enter passphrase:",
                       prompt2="Verify passphrase:"):
  """A utility function to read a passphrase from stdin."""
  while 1:
    try:
      p1 = getpass.getpass(prompt1)
      if verify:
        p2 = getpass.getpass(prompt2)
        if p1 == p2:
          break
      else:
        break
    except KeyboardInterrupt:
      return None
  return p1


def FormatNumberAsString(num):
  """Return a large number in human readable form."""
  for suffix in ["b", "KB", "MB", "GB"]:
    if num < 1024.0:
      return "%3.2f%s" % (num, suffix)
    num /= 1024.0
  return "%3.1f%s" % (num, "TB")


class NotAValue(object):
  pass


class HeartbeatQueue(queue.Queue):
  """A queue that periodically calls a provided callback while waiting."""

  def __init__(self, callback=None, fast_poll_time=60, *args, **kw):
    queue.Queue.__init__(self, *args, **kw)
    self.callback = callback or (lambda: None)
    self.last_item_time = time.time()
    self.fast_poll_time = fast_poll_time

  def get(self, poll_interval=5):
    while True:
      try:
        # Using Queue.get() with a timeout is really expensive - Python uses
        # busy waiting that wakes up the process every 50ms - so we switch
        # to a more efficient polling method if there is no activity for
        # <fast_poll_time> seconds.
        if time.time() - self.last_item_time < self.fast_poll_time:
          message = queue.Queue.get(self, block=True, timeout=poll_interval)
        else:
          time.sleep(poll_interval)
          message = queue.Queue.get(self, block=False)
        break

      except queue.Empty:
        self.callback()

    self.last_item_time = time.time()
    return message


class RollingMemoryStream(object):
  """Append-only memory stream that allows writing data in chunks."""

  def __init__(self):
    self._stream = io.BytesIO()
    self._offset = 0

  def write(self, b):  # pylint: disable=invalid-name
    if not self._stream:
      raise ArchiveAlreadyClosedError("Attempting to write to a closed stream.")

    self._stream.write(b)
    self._offset += len(b)

  def flush(self):  # pylint: disable=invalid-name
    pass

  def tell(self):  # pylint: disable=invalid-name
    return self._offset

  def close(self):  # pylint: disable=invalid-name
    self._stream = None

  def GetValueAndReset(self):
    """Gets stream buffer since the last GetValueAndReset() call."""
    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to get a value from a closed stream.")

    value = self._stream.getvalue()
    self._stream.seek(0)
    self._stream.truncate()

    return value


class ArchiveAlreadyClosedError(Error):
  pass


# TODO(user):pytype: we use a lot of zipfile internals that type checker is
# not aware of.
# pytype: disable=attribute-error,wrong-arg-types
class StreamingZipGenerator(object):
  """A streaming zip generator that can archive file-like objects."""

  FILE_CHUNK_SIZE = 1024 * 1024 * 4

  def __init__(self, compression=zipfile.ZIP_STORED):
    self._stream = RollingMemoryStream()
    self._zip_fd = zipfile.ZipFile(
        self._stream, mode="w", compression=compression, allowZip64=True)
    self._compression = compression

    self._ResetState()

  def _ResetState(self):
    self.cur_zinfo = None
    self.cur_file_size = 0
    self.cur_compress_size = 0
    self.cur_cmpr = None
    self.cur_crc = 0

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def _GenerateZipInfo(self, arcname=None, compress_type=None, st=None):
    """Generate ZipInfo instance for the given name, compression and stat.

    Args:
      arcname: The name in the archive this should take.
      compress_type: Compression type (zipfile.ZIP_DEFLATED, or ZIP_STORED)
      st: An optional stat object to be used for setting headers.

    Returns:
      ZipInfo instance.

    Raises:
      ValueError: If arcname is not provided.
    """
    # Fake stat response.
    if st is None:
      # TODO(user):pytype: stat_result typing is not correct.
      # pytype: disable=wrong-arg-count
      st = os.stat_result((0o100644, 0, 0, 0, 0, 0, 0, 0, 0, 0))
      # pytype: enable=wrong-arg-count

    mtime = time.localtime(st.st_mtime or time.time())
    date_time = mtime[0:6]
    # Create ZipInfo instance to store file information
    if arcname is None:
      raise ValueError("An arcname must be provided.")

    zinfo = zipfile.ZipInfo(arcname, date_time)
    zinfo.external_attr = (st[0] & 0xFFFF) << 16  # Unix attributes

    if compress_type is None:
      zinfo.compress_type = self._compression
    else:
      zinfo.compress_type = compress_type

    zinfo.file_size = 0
    zinfo.compress_size = 0
    zinfo.flag_bits = 0x08  # Setting data descriptor flag.
    zinfo.CRC = 0x08074b50  # Predefined CRC for archives using data
    # descriptors.
    # This fills an empty Info-ZIP Unix extra field.
    zinfo.extra = struct.pack(
        "<HHIIHH",
        0x5855,
        12,
        0,  # time of last access (UTC/GMT)
        0,  # time of last modification (UTC/GMT)
        0,  # user ID
        0)  # group ID
    return zinfo

  def WriteSymlink(self, src_arcname, dst_arcname):
    """Writes a symlink into the archive."""
    # Inspired by:
    # http://www.mail-archive.com/python-list@python.org/msg34223.html

    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to write to a ZIP archive that was already closed.")

    src_arcname = SmartStr(src_arcname)
    dst_arcname = SmartStr(dst_arcname)

    zinfo = zipfile.ZipInfo(dst_arcname)
    # This marks a symlink.
    zinfo.external_attr = (0o644 | 0o120000) << 16
    # This marks create_system as UNIX.
    zinfo.create_system = 3

    # This fills the ASi UNIX extra field, see:
    # http://www.opensource.apple.com/source/zip/zip-6/unzip/unzip/proginfo/extra.fld
    zinfo.extra = struct.pack(
        "<HHIHIHHs",
        0x756e,
        len(src_arcname) + 14,
        0,  # CRC-32 of the remaining data
        0o120000,  # file permissions
        0,  # target file size
        0,  # user ID
        0,  # group ID
        src_arcname)

    self._zip_fd.writestr(zinfo, src_arcname)

    return self._stream.GetValueAndReset()

  def WriteFileHeader(self, arcname=None, compress_type=None, st=None):
    """Writes a file header."""

    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to write to a ZIP archive that was already closed.")

    self.cur_zinfo = self._GenerateZipInfo(
        arcname=arcname, compress_type=compress_type, st=st)
    self.cur_file_size = 0
    self.cur_compress_size = 0

    if self.cur_zinfo.compress_type == zipfile.ZIP_DEFLATED:
      self.cur_cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                                       zlib.DEFLATED, -15)
    else:
      self.cur_cmpr = None

    self.cur_crc = 0

    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to write to a ZIP archive that was already closed.")

    self.cur_zinfo.header_offset = self._stream.tell()
    # Call _writeCheck(self.cur_zinfo) to do sanity checking on zinfo structure
    # that we've constructed.
    self._zip_fd._writecheck(self.cur_zinfo)  # pylint: disable=protected-access
    # Mark ZipFile as dirty. We have to keep self._zip_fd's internal state
    # coherent so that it behaves correctly when close() is called.
    self._zip_fd._didModify = True  # pylint: disable=protected-access

    # Write FileHeader now. It's incomplete, but CRC and uncompressed/compressed
    # sized will be written later in data descriptor.
    self._stream.write(self.cur_zinfo.FileHeader())

    return self._stream.GetValueAndReset()

  def WriteFileChunk(self, chunk):
    """Writes file chunk."""

    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to write to a ZIP archive that was already closed.")

    self.cur_file_size += len(chunk)
    # TODO(user):pytype: crc32 is not visible outside of zipfile.
    # pytype: disable=module-attr
    self.cur_crc = zipfile.crc32(chunk, self.cur_crc) & 0xffffffff
    # pytype: enable=module-attr

    if self.cur_cmpr:
      chunk = self.cur_cmpr.compress(chunk)
      self.cur_compress_size += len(chunk)

    self._stream.write(chunk)
    return self._stream.GetValueAndReset()

  def WriteFileFooter(self):
    """Writes the file footer (finished the file)."""

    if not self._stream:
      raise ArchiveAlreadyClosedError(
          "Attempting to write to a ZIP archive that was already closed.")

    if self.cur_cmpr:
      buf = self.cur_cmpr.flush()
      self.cur_compress_size += len(buf)
      self.cur_zinfo.compress_size = self.cur_compress_size

      self._stream.write(buf)
    else:
      self.cur_zinfo.compress_size = self.cur_file_size

    self.cur_zinfo.CRC = self.cur_crc
    self.cur_zinfo.file_size = self.cur_file_size

    # The zip footer has a 8 bytes limit for sizes so if we compress a
    # file larger than 4 GB, the code below will not work. The ZIP64
    # convention is to write 0xffffffff for compressed and
    # uncompressed size in those cases. The actual size is written by
    # the library for us anyways so those fields are redundant.
    cur_file_size = min(0xffffffff, self.cur_file_size)
    cur_compress_size = min(0xffffffff, self.cur_compress_size)

    # Writing data descriptor ZIP64-way by default. We never know how large
    # the archive may become as we're generating it dynamically.
    #
    # crc-32                          8 bytes (little endian)
    # compressed size                 8 bytes (little endian)
    # uncompressed size               8 bytes (little endian)
    self._stream.write(
        struct.pack("<LLL", self.cur_crc, cur_compress_size, cur_file_size))

    # Register the file in the zip file, so that central directory gets
    # written correctly.
    self._zip_fd.filelist.append(self.cur_zinfo)
    self._zip_fd.NameToInfo[self.cur_zinfo.filename] = self.cur_zinfo

    self._ResetState()

    return self._stream.GetValueAndReset()

  @property
  def is_file_write_in_progress(self):
    return self.cur_zinfo

  def WriteFromFD(self, src_fd, arcname=None, compress_type=None, st=None):
    """Write a zip member from a file like object.

    Args:
      src_fd: A file like object, must support seek(), tell(), read().
      arcname: The name in the archive this should take.
      compress_type: Compression type (zipfile.ZIP_DEFLATED, or ZIP_STORED)
      st: An optional stat object to be used for setting headers.

    Raises:
      ArchiveAlreadyClosedError: If the zip if already closed.

    Yields:
      Chunks of binary data.
    """
    yield self.WriteFileHeader(
        arcname=arcname, compress_type=compress_type, st=st)
    while 1:
      buf = src_fd.read(1024 * 1024)
      if not buf:
        break

      yield self.WriteFileChunk(buf)

    yield self.WriteFileFooter()

  def Close(self):
    self._zip_fd.close()

    value = self._stream.GetValueAndReset()
    self._stream.close()

    return value

  @property
  def output_size(self):
    return self._stream.tell()


# pytype: enable=attribute-error,wrong-arg-types


class StreamingTarGenerator(object):
  """A streaming tar generator that can archive file-like objects."""

  FILE_CHUNK_SIZE = 1024 * 1024 * 4

  def __init__(self):
    super(StreamingTarGenerator, self).__init__()

    self._stream = RollingMemoryStream()
    # TODO(user):pytype: self._stream should be a valid IO object.
    # pytype: disable=wrong-arg-types
    self._tar_fd = tarfile.open(
        mode="w:gz", fileobj=self._stream, encoding="utf-8")
    # pytype: enable=wrong-arg-types

    self._ResetState()

  def _ResetState(self):
    self.cur_file_size = 0
    self.cur_info = None

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def Close(self):
    self._tar_fd.close()

    value = self._stream.GetValueAndReset()
    self._stream.close()

    return value

  def WriteSymlink(self, src_arcname, dst_arcname):
    """Writes a symlink into the archive."""

    info = self._tar_fd.tarinfo()
    info.tarfile = self._tar_fd
    info.name = SmartStr(dst_arcname)
    info.size = 0
    info.mtime = time.time()
    info.type = tarfile.SYMTYPE
    info.linkname = SmartStr(src_arcname)

    self._tar_fd.addfile(info)
    return self._stream.GetValueAndReset()

  def WriteFileHeader(self, arcname=None, st=None):
    """Writes file header."""

    if st is None:
      raise ValueError("Stat object can't be None.")

    self.cur_file_size = 0

    self.cur_info = self._tar_fd.tarinfo()
    self.cur_info.tarfile = self._tar_fd
    self.cur_info.type = tarfile.REGTYPE
    self.cur_info.name = SmartStr(arcname)
    self.cur_info.size = st.st_size
    self.cur_info.mode = st.st_mode
    self.cur_info.mtime = st.st_mtime or time.time()

    self._tar_fd.addfile(self.cur_info)

    return self._stream.GetValueAndReset()

  def WriteFileChunk(self, chunk):
    """Writes file chunk."""

    self._tar_fd.fileobj.write(chunk)
    self.cur_file_size += len(chunk)
    return self._stream.GetValueAndReset()

  def WriteFileFooter(self):
    """Writes file footer (finishes the file)."""

    if self.cur_file_size != self.cur_info.size:
      raise IOError("Incorrect file size: st_size=%d, but written %d bytes." %
                    (self.cur_info.size, self.cur_file_size))

    # TODO(user):pytype: BLOCKSIZE/NUL constants are not visible to type
    # checker.
    # pytype: disable=module-attr
    blocks, remainder = divmod(self.cur_file_size, tarfile.BLOCKSIZE)
    if remainder > 0:
      self._tar_fd.fileobj.write(tarfile.NUL * (tarfile.BLOCKSIZE - remainder))
      blocks += 1
    self._tar_fd.offset += blocks * tarfile.BLOCKSIZE
    # pytype: enable=module-attr

    self._ResetState()

    return self._stream.GetValueAndReset()

  @property
  def is_file_write_in_progress(self):
    return self.cur_info

  def WriteFromFD(self, src_fd, arcname=None, st=None):
    """Write an archive member from a file like object.

    Args:
      src_fd: A file like object, must support seek(), tell(), read().
      arcname: The name in the archive this should take.
      st: A stat object to be used for setting headers.

    Raises:
      ValueError: If st is omitted.
      ArchiveAlreadyClosedError: If the archive was already closed.
      IOError: if file size reported in st is different from the one that
          was actually read from the src_fd.

    Yields:
      Chunks of binary data.
    """

    yield self.WriteFileHeader(arcname=arcname, st=st)

    while 1:
      buf = src_fd.read(1024 * 1024)
      if not buf:
        break
      yield self.WriteFileChunk(buf)

    yield self.WriteFileFooter()

  @property
  def output_size(self):
    return self._stream.tell()


class Stubber(object):
  """A context manager for doing simple stubs."""

  def __init__(self, module, target_name, stub):
    self.target_name = target_name
    self.module = module
    self.stub = stub

  def __enter__(self):
    self.Start()

  def Stop(self):
    setattr(self.module, self.target_name, self.old_target)

  def Start(self):
    self.old_target = getattr(self.module, self.target_name, None)
    try:
      self.stub.old_target = self.old_target
    except AttributeError:
      pass
    setattr(self.module, self.target_name, self.stub)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()


class MultiStubber(object):
  """A context manager for doing simple stubs."""

  def __init__(self, *args):
    self.stubbers = [Stubber(*x) for x in args]

  def Start(self):
    for x in self.stubbers:
      x.Start()

  def Stop(self):
    for x in self.stubbers:
      x.Stop()

  def __enter__(self):
    self.Start()

  def __exit__(self, t, value, traceback):
    self.Stop()


def EnsureDirExists(path):
  """Equivalent of makedir -p."""
  try:
    os.makedirs(path)
  except OSError as exc:
    # Necessary so we don't hide other errors such as permission denied.
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise


def ResolveHostnameToIP(host, port):
  ip_addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, 0,
                                socket.IPPROTO_TCP)
  # getaddrinfo returns tuples (family, socktype, proto, canonname, sockaddr).
  # We are interested in sockaddr which is in turn a tuple
  # (address, port) for IPv4 or (address, port, flow info, scope id)
  # for IPv6. In both cases, we want the first element, the address.
  return ip_addrs[0][4][0]


# TODO(hanuszczak): This module is way too big right now. It should be split
# into several smaller ones (such as `util.paths`, `util.collections` etc.).


class Stat(object):
  """A wrapper around standard `os.[l]stat` function.

  The standard API for using `stat` results is very clunky and unpythonic.
  This is an attempt to create a more familiar and consistent interface to make
  the code look cleaner.

  Moreover, standard `stat` does not properly support extended flags - even
  though the documentation mentions that `stat.st_flags` should work on macOS
  and Linux it works only on macOS and raises an error on Linux (and Windows).
  This class handles that and fetches these flags lazily (as it can be costly
  operation on Linux).

  Args:
    path: A path to the file to perform `stat` on.
    follow_symlink: True if `stat` of a symlink should be returned instead of a
      file that it points to. For non-symlinks this setting has no effect.
  """

  def __init__(self, path, follow_symlink=True):
    self._path = path
    if not follow_symlink:
      self._stat = os.lstat(path)
    else:
      self._stat = os.stat(path)

    self._flags_linux = None
    self._flags_osx = None

  def GetRaw(self):
    return self._stat

  def GetPath(self):
    return self._path

  def GetLinuxFlags(self):
    if self._flags_linux is None:
      self._flags_linux = self._FetchLinuxFlags()
    return self._flags_linux

  def GetOsxFlags(self):
    if self._flags_osx is None:
      self._flags_osx = self._FetchOsxFlags()
    return self._flags_osx

  def GetSize(self):
    return self._stat.st_size

  def GetAccessTime(self):
    return self._stat.st_atime

  def GetModificationTime(self):
    return self._stat.st_mtime

  def GetChangeTime(self):
    return self._stat.st_ctime

  def GetDevice(self):
    return self._stat.st_dev

  def IsDirectory(self):
    return stat.S_ISDIR(self._stat.st_mode)

  def IsRegular(self):
    return stat.S_ISREG(self._stat.st_mode)

  def IsSocket(self):
    return stat.S_ISSOCK(self._stat.st_mode)

  def IsSymlink(self):
    return stat.S_ISLNK(self._stat.st_mode)

  # http://manpages.courier-mta.org/htmlman2/ioctl_list.2.html
  FS_IOC_GETFLAGS = 0x80086601

  def _FetchLinuxFlags(self):
    """Fetches Linux extended file flags."""
    if platform.system() != "Linux":
      return 0

    # Since we open a file in the next step we do not want to open a symlink.
    # `lsattr` returns an error when trying to check flags of a symlink, so we
    # assume that symlinks cannot have them.
    if self.IsSymlink():
      return 0

    # Some files (e.g. sockets) cannot be opened. For these we do not really
    # care about extended flags (they should have none). `lsattr` does not seem
    # to support such cases anyway. It is also possible that a file has been
    # deleted (because this method is used lazily).
    try:
      fd = os.open(self._path, os.O_RDONLY)
    except (IOError, OSError):
      return 0

    try:
      # This import is Linux-specific.
      import fcntl  # pylint: disable=g-import-not-at-top
      # TODO(hanuszczak): On Python 2.7.6 `array.array` accepts only bytestrings
      # as an argument. On Python 2.7.12 and 2.7.13 unicodes are supported as
      # well. On Python 3, only unicode strings are supported. This is why, as
      # a temporary hack, we wrap the literal with `str` call that will convert
      # it to whatever is the default on given Python version. This should be
      # changed to raw literal once support for Python 2 is dropped.
      buf = array.array(str("l"), [0])
      # TODO(user):pytype: incorrect type spec for fcntl.ioctl
      # pytype: disable=wrong-arg-types
      fcntl.ioctl(fd, self.FS_IOC_GETFLAGS, buf)
      # pytype: enable=wrong-arg-types
      return buf[0]
    except (IOError, OSError):
      # File system does not support extended attributes.
      return 0
    finally:
      os.close(fd)

  def _FetchOsxFlags(self):
    """Fetches macOS extended file flags."""
    if platform.system() != "Darwin":
      return 0

    return self._stat.st_flags


class StatCache(object):
  """An utility class for avoiding unnecessary syscalls to `[l]stat`.

  This class is useful in situations where manual bookkeeping of stat results
  in order to prevent extra system calls becomes tedious and complicates control
  flow. This class makes sure that no unnecessary system calls are made and is
  smart enough to cache symlink results when a file is not a symlink.
  """

  _Key = collections.namedtuple("_Key", ("path", "follow_symlink"))  # pylint: disable=invalid-name

  def __init__(self):
    self._cache = {}

  def Get(self, path, follow_symlink=True):
    """Stats given file or returns a cached result if available.

    Args:
      path: A path to the file to perform `stat` on.
      follow_symlink: True if `stat` of a symlink should be returned instead of
        a file that it points to. For non-symlinks this setting has no effect.

    Returns:
      `Stat` object corresponding to the given path.
    """
    key = self._Key(path=path, follow_symlink=follow_symlink)
    try:
      return self._cache[key]
    except KeyError:
      value = Stat(path, follow_symlink=follow_symlink)
      self._cache[key] = value

      # If we are not following symlinks and the file is a not symlink then
      # the stat result for this file stays the same even if we want to follow
      # symlinks.
      if not follow_symlink and not value.IsSymlink():
        self._cache[self._Key(path=path, follow_symlink=True)] = value

      return value


def ProcessIdString():
  return "%s@%s:%d" % (psutil.Process().name(), socket.gethostname(),
                       os.getpid())


def IterValuesInSortedKeysOrder(d):
  """Iterates dict's values in sorted keys order."""

  for key in sorted(iterkeys(d)):
    yield d[key]


def RegexListDisjunction(regex_list):
  return "(" + ")|(".join(regex_list) + ")"


def ReadFileBytesAsUnicode(file_obj):
  data = file_obj.read()
  precondition.AssertType(data, bytes)

  return data.decode("utf-8")
