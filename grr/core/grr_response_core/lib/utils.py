#!/usr/bin/env python
"""This file contains various utility classes used by GRR."""

from collections.abc import Iterable
import errno
import functools
import getpass
import gzip
import io
import os
import pathlib
import queue
import random
import re
import shlex
import shutil
import socket
import struct
import tarfile
import tempfile
import threading
import time
from typing import Generic, Optional, TypeVar
import weakref
import zipfile

import psutil

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


class TempDirectory:
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

  def __init__(
      self,
      target=None,
      args=None,
      kwargs=None,
      sleep_time=10,
      name: Optional[str] = None,
      **kw,
  ):
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
    super().__init__(name=name, **kw)
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
      while time and not self.exit and now() < self.last_run + self.sleep_time:
        sleep(1)


class Node:
  """An entry to a linked list."""

  next = None
  prev = None
  data = None

  def __init__(self, key, data):
    self.data = data
    self.key = key

  def __str__(self):
    return "Node %s: %s" % (self.key, self.data)

  def __repr__(self):
    return str(self)


# TODO(user):pytype: self.next and self.prev are assigned to self but then
# are used in AppendNode in a very different way. Should be redesigned.
# pytype: disable=attribute-error
class LinkedList:
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
    return "[" + ", ".join(map(str, self)) + "]"

  def Print(self):
    p = self.next
    while p is not self:
      print("%s: prev %r next %r\n" % (p.data, p.prev, p.next))
      p = p.next


# pytype: enable=attribute-error


class FastStore:
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
    return iter([(key, n.data) for key, n in self._hash.items()])

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


_T = TypeVar("_T")


class TimeBasedCacheEntry(Generic[_T]):

  def __init__(self, timestamp: float, value: _T):
    self.timestamp = timestamp
    self.value: _T = value


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
    super().__init__(max_size)
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
          for node in list(cache._hash.values()):
            # Expire the object if it is too old.
            if node.data.timestamp + cache.max_age < now:
              cache.KillObject(node.data)

              cache._age.Unlink(node)
              cache._hash.pop(node.key, None)
          # pylint: enable=protected-access

    if not TimeBasedCache.house_keeper_thread:
      TimeBasedCache.active_caches = weakref.WeakSet()
      # This thread is designed to never finish.
      TimeBasedCache.house_keeper_thread = InterruptableThread(
          name="HouseKeeperThread", target=HouseKeeper
      )
      TimeBasedCache.house_keeper_thread.start()
    TimeBasedCache.active_caches.add(self)

  @Synchronized
  def Get(self, key):
    now = time.time()
    stored = super().Get(key)
    if stored.timestamp + self.max_age < now:
      raise KeyError("Expired")

    # This updates the timestamp in place to keep the object alive
    stored.timestamp = now

    return stored.value

  def Put(self, key, obj):
    super().Put(key, TimeBasedCacheEntry(time.time(), obj))


class AgeBasedCache(TimeBasedCache):
  """A cache which holds objects for a maximum length of time.

  This differs from the TimeBasedCache which keeps the objects alive as long as
  they are accessed.
  """

  @Synchronized
  def Get(self, key):
    now = time.time()
    stored = FastStore.Get(self, key)
    if stored.timestamp + self.max_age < now:
      raise KeyError("Expired")

    return stored.value


class Struct:
  """A baseclass for parsing binary Structs."""

  # Derived classes must initialize this into an array of (format,
  # name) tuples.
  _fields: list[tuple[str, str]]

  def __init__(self, data):
    """Parses ourselves from data."""
    format_str = "".join([x[0] for x in self._fields])
    self.size = struct.calcsize(format_str)

    try:
      parsed_data = struct.unpack(format_str, data[: self.size])

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


def SmartUnicode(string):
  """Returns a unicode object.

  This function will always return a unicode object. It should be used to
  guarantee that something is always a unicode object.

  Args:
    string: The string to convert.

  Returns:
    a unicode object.
  """
  if isinstance(string, str):
    return string

  if isinstance(string, bytes):
    return string.decode("utf-8", "ignore")

  return str(string)


def Xor(bytestr, key):
  """Returns a `bytes` object where each byte has been xored with key."""
  precondition.AssertType(bytestr, bytes)
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


def FormatAsTimestamp(timestamp: int) -> str:
  if not timestamp:
    return "-"

  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp))


def NormalizePath(path: str, sep: str = "/") -> str:
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
  precondition.AssertType(path, str)
  precondition.AssertType(sep, str)

  if not path:
    return sep

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

    # If we didn't alter the path so far we can quit
    if len(path_list) == list_len:
      return sep + sep.join(path_list)


# TODO(hanuszczak): The linter complains for a reason here, the signature of
# this function should be fixed as soon as possible.
def JoinPath(stem: str = "", *parts: str) -> str:  # pylint: disable=keyword-arg-before-vararg
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
  precondition.AssertIterableType(parts, str)
  precondition.AssertType(stem, str)

  result = (stem + NormalizePath("/".join(parts))).replace("//", "/")
  result = result.rstrip("/")

  return result or "/"


def ShellQuote(value):
  """Escapes the string for the safe use inside shell command line."""
  return shlex.quote(SmartUnicode(value))


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


def GeneratePassphrase(length=20):
  """Create a 20 char passphrase with easily typeable chars."""
  valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  valid_chars += "0123456789 ,-_&$#"
  return "".join(random.choice(valid_chars) for i in range(length))


def PassphraseCallback(
    verify=False, prompt1="Enter passphrase:", prompt2="Verify passphrase:"
):
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
  return p1.encode("utf-8")


def FormatNumberAsString(num):
  """Return a large number in human readable form."""
  for suffix in ["b", "KB", "MB", "GB"]:
    if num < 1024.0:
      return "%3.2f%s" % (num, suffix)
    num /= 1024.0
  return "%3.1f%s" % (num, "TB")


class NotAValue:
  pass


class HeartbeatQueue(queue.Queue):
  """A queue that periodically calls a provided callback while waiting."""

  def __init__(self, *args, callback=None, **kw):
    queue.Queue.__init__(self, *args, **kw)
    self.callback = callback or (lambda: None)

  def get(self, poll_interval=5):
    while True:
      try:
        message = queue.Queue.get(self, block=True, timeout=poll_interval)
        break

      except queue.Empty:
        self.callback()

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
          "Attempting to get a value from a closed stream."
      )

    value = self._stream.getvalue()
    self._stream.seek(0)
    self._stream.truncate()

    return value


class ArchiveAlreadyClosedError(Error):
  pass


# TODO(hanuszczak): Typings for `ZipFile` are ill-typed.
# pytype: disable=attribute-error,wrong-arg-types
class StreamingZipGenerator(object):
  """A streaming zip generator that can archive file-like objects."""

  def __init__(self, compression=zipfile.ZIP_STORED):
    self._compression = compression
    self._stream = RollingMemoryStream()
    self._zipfile = zipfile.ZipFile(
        self._stream, mode="w", compression=compression, allowZip64=True
    )

    self._zipopen = None

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.
    return self.Close()

  def __del__(self):
    if self._zipopen is not None:
      self._zipopen.__exit__(None, None, None)
      self._zipopen = None

  # TODO(hanuszczak): Because we have to use `ZipFile::open`, there is no way to
  # specify per-file compression and write custom stat entry (but it should be
  # relevant only for dates). Once we remove this class and switch back to the
  # native implementation, it should be possible to fill this information again.
  def WriteFileHeader(self, arcname=None, compress_type=None, st=None):
    del compress_type, st  # Unused.

    if not self._stream:
      raise ArchiveAlreadyClosedError()

    self._zipopen = self._zipfile.open(arcname, mode="w")
    self._zipopen.__enter__()

    return self._stream.GetValueAndReset()

  def WriteFileChunk(self, chunk):
    precondition.AssertType(chunk, bytes)

    if not self._stream:
      raise ArchiveAlreadyClosedError()

    self._zipopen.write(chunk)

    return self._stream.GetValueAndReset()

  def WriteFileFooter(self):
    if not self._stream:
      raise ArchiveAlreadyClosedError()

    self._zipopen.__exit__(None, None, None)
    self._zipopen = None

    return self._stream.GetValueAndReset()

  def Close(self):
    if self._zipopen is not None:
      self._zipopen.__exit__(None, None, None)
      self._zipopen = None

    self._zipfile.close()

    value = self._stream.GetValueAndReset()
    self._stream.close()
    return value

  def WriteFromFD(self, src_fd, arcname=None, compress_type=None, st=None):
    """A convenience method for adding an entire file to the ZIP archive."""
    yield self.WriteFileHeader(
        arcname=arcname, compress_type=compress_type, st=st
    )

    while True:
      buf = src_fd.read(1024 * 1024)
      if not buf:
        break

      yield self.WriteFileChunk(buf)

    yield self.WriteFileFooter()

  @property
  def is_file_write_in_progress(self) -> bool:
    return bool(self._zipopen)

  @property
  def output_size(self):
    return self._stream.tell()


# pytype: enable=attribute-error,wrong-arg-types


class StreamingTarGenerator(object):
  """A streaming tar generator that can archive file-like objects."""

  FILE_CHUNK_SIZE = 1024 * 1024 * 4

  def __init__(self):
    super().__init__()

    self._stream = RollingMemoryStream()
    self._stream_gzip = gzip.GzipFile(mode="wb", fileobj=self._stream)

    self._ResetState()

  def _ResetState(self):
    self.cur_file_size = 0
    self.cur_info = None

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def Close(self):
    self._stream_gzip.close()

    value = self._stream.GetValueAndReset()
    self._stream.close()

    return value

  def WriteFileHeader(self, arcname=None, st=None):
    """Writes file header."""
    precondition.AssertType(arcname, str)

    if st is None:
      raise ValueError("Stat object can't be None.")

    self.cur_file_size = 0

    self.cur_info = tarfile.TarInfo()
    self.cur_info.type = tarfile.REGTYPE
    self.cur_info.name = arcname
    self.cur_info.size = st.st_size
    self.cur_info.mode = st.st_mode
    self.cur_info.mtime = st.st_mtime or time.time()

    self._stream_gzip.write(self.cur_info.tobuf(encoding="utf-8"))

    return self._stream.GetValueAndReset()

  def WriteFileChunk(self, chunk):
    """Writes file chunk."""

    self._stream_gzip.write(chunk)
    self.cur_file_size += len(chunk)
    return self._stream.GetValueAndReset()

  def WriteFileFooter(self):
    """Writes file footer (finishes the file)."""
    if self.cur_info is None:
      raise ValueError("WriteFileHeader() must be called first.")

    if self.cur_file_size != self.cur_info.size:
      raise IOError(
          "Incorrect file size: st_size=%d, but written %d bytes."
          % (self.cur_info.size, self.cur_file_size)
      )

    remainder = self.cur_file_size % tarfile.BLOCKSIZE
    if remainder > 0:
      self._stream_gzip.write(tarfile.NUL * (tarfile.BLOCKSIZE - remainder))

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


class Stubber:
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


def MergeDirectories(src: str, dst: str) -> None:
  """Merges the src directory tree into the dst directory tree."""
  src_dir = pathlib.Path(src)
  dst_dir = pathlib.Path(dst)
  for path in src_dir.glob("**/*"):
    if path.is_dir():
      continue
    relative_path = path.relative_to(src_dir)
    dst_path = dst_dir / relative_path
    EnsureDirExists(str(dst_path.parent))
    shutil.copy(str(path), str(dst_path))


def ResolveHostnameToIP(host, port):
  """Resolves a hostname to an IP address."""
  ip_addrs = socket.getaddrinfo(
      host, port, socket.AF_UNSPEC, 0, socket.IPPROTO_TCP
  )
  # getaddrinfo returns tuples (family, socktype, proto, canonname, sockaddr).
  # We are interested in sockaddr which is in turn a tuple
  # (address, port) for IPv4 or (address, port, flow info, scope id)
  # for IPv6. In both cases, we want the first element, the address.
  return ip_addrs[0][4][0]


# TODO: This module is way too big right now. It should be split
# into several smaller ones (such as `util.paths`, `util.collections` etc.).


def ProcessIdString():
  return "%s@%s:%d" % (
      psutil.Process().name(),
      socket.gethostname(),
      os.getpid(),
  )


def RegexListDisjunction(regex_list: Iterable[bytes]):
  precondition.AssertIterableType(regex_list, bytes)
  return b"(" + b")|(".join(regex_list) + b")"


def ReadFileBytesAsUnicode(file_obj):
  data = file_obj.read()
  precondition.AssertType(data, bytes)

  return data.decode("utf-8")


def RunOnce(fn):
  """Returns a decorated function that will only pass through the first call.

  At first execution, the return value or raised Exception is passed through and
  cached. Further calls will not be passed to `fn` and will return or raise
  the result of the first call.

  Be cautious when returning an Iterator, Generator or mutable value, since the
  result is shared by reference among all calls.

  Args:
    fn: The function to be decorated.

  Returns:
    A decorated function that will pass through only the first call.
  """

  @functools.wraps(fn)
  def _OneTimeFunction(*args, **kwargs):
    """Wrapper function that only passes through the first call."""
    if not _OneTimeFunction.executed:
      _OneTimeFunction.executed = True
      try:
        _OneTimeFunction.result = fn(*args, **kwargs)
      except BaseException as e:  # pylint: disable=broad-except
        _OneTimeFunction.exception = e
        raise  # Preserve original stack trace during first invocation.

    if _OneTimeFunction.exception is None:
      return _OneTimeFunction.result
    else:
      raise _OneTimeFunction.exception

  _OneTimeFunction.executed = False
  _OneTimeFunction.exception = None
  _OneTimeFunction.result = None
  return _OneTimeFunction
