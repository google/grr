#!/usr/bin/env python
"""This file contains various utility classes used by GRR."""


import __builtin__
import base64
import os
import pipes
import Queue
import random
import re
import shlex
import socket
import shutil
import struct
import tarfile
import tempfile
import threading
import time
import zipfile
import zlib



class IPInfo(object):
  UNKNOWN = 0
  INTERNAL = 1
  EXTERNAL = 2
  VPN = 3


def RetrieveIPInfo(ip):
  if not ip:
    return (IPInfo.UNKNOWN, "No ip information.")
  ip = SmartStr(ip)
  if ":" in ip:
    return RetrieveIP6Info(ip)
  return RetrieveIP4Info(ip)

def RetrieveIP4Info(ip):
  """Retrieves information for an IP4 address."""
  if ip.startswith("192"):
    return (IPInfo.INTERNAL, "Internal IP address.")
  try:
    # It's an external IP, let's try to do a reverse lookup.
    res = socket.gethostbyaddr(ip)
    return (IPInfo.EXTERNAL, res[0])
  except (socket.herror, socket.gaierror):
    return (IPInfo.EXTERNAL, "Unknown IP address.")

def RetrieveIP6Info(ip):
  """Retrieves information for an IP6 address."""
  return (IPInfo.INTERNAL, "Internal IP6 address.")


def Proxy(f):
  """A helper to create a proxy method in a class."""

  def Wrapped(self, *args):
    return getattr(self, f)(*args)
  return Wrapped


class TempDirectory(object):
  """A self cleaning temporary directory."""

  def __enter__(self):
    self.name = tempfile.mkdtemp()

    return self.name

  def __exit__(self, exc_type, exc_value, traceback):
    shutil.rmtree(self.name, True)


# This is a synchronize decorator.
def Synchronized(f):
  """Synchronization decorator."""

  def NewFunction(self, *args, **kw):
    with self.lock:
      return f(self, *args, **kw)

  return NewFunction


class InterruptableThread(threading.Thread):
  """A class which exits once the main thread exits."""

  def __init__(self, target=None, args=None, kwargs=None, sleep_time=10, **kw):
    self.exit = False
    self.last_run = 0
    self.target = target
    self.args = args or ()
    self.kwargs = kwargs or {}
    self.sleep_time = sleep_time
    super(InterruptableThread, self).__init__(**kw)

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
      print "%s: prev %r next %r\n" % (p.data, p.prev, p.next)
      p = p.next


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
    return iter([(key, n.data) for key, n in self._hash.iteritems()])

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

  @Synchronized
  def __getstate__(self):
    """When pickled the cache is flushed."""
    self.Flush()
    return dict(max_size=self._limit)

  def __setstate__(self, state):
    self.__init__(max_size=state.get("max_size", 10))

  def __len__(self):
    return len(self._hash)


class TimeBasedCache(FastStore):
  """A Cache which expires based on time."""

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

      # Only expunge while holding the lock on the data store.
      with self.lock:
        # We need to take a copy of the value list because we are changing this
        # dict during the iteration.
        for node in self._hash.values():
          timestamp, obj = node.data

          # Expire the object if it is too old.
          if timestamp + self.max_age < now:
            self.KillObject(obj)

            self._age.Unlink(node)
            self._hash.pop(node.key, None)

    # This thread is designed to never finish
    self.house_keeper_thread = InterruptableThread(target=HouseKeeper)
    self.house_keeper_thread.start()

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

  @Synchronized
  def __getstate__(self):
    """When pickled the cache is flushed."""
    self.Flush()
    return dict(max_size=self._limit, max_age=self.max_age)

  def __setstate__(self, state):
    self.__init__(max_size=state["max_size"], max_age=state["max_age"])


class PickleableLock(object):
  """A lock which is safe to pickle."""

  lock = None

  def __getstate__(self):
    return {}

  def __setstate__(self, _):
    pass

  def __enter__(self):
    if self.lock is None:
      self.lock = threading.RLock()

    return self.lock.__enter__()

  def __exit__(self, exc_type, exc_value, traceback):
    if self.lock is None:
      self.lock = threading.RLock()

    return self.lock.__exit__(exc_type, exc_value, traceback)


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
      raise RuntimeError("Unable to parse")

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


def GroupBy(items, key):
  """A generator that groups all items by a key.

  Args:
    items:  A list of items or a single item.
    key: A function which given each item will return the key.

  Returns:
    A dict with keys being each unique key and values being a list of items of
    that key.
  """
  key_map = {}

  # Make sure we are given a sequence of items here.
  try:
    item_iter = iter(items)
  except TypeError:
    item_iter = [items]

  for item in item_iter:
    key_id = key(item)
    key_map.setdefault(key_id, []).append(item)

  return key_map


def SmartStr(string):
  """Returns a string or encodes a unicode object.

  This function essentially will always return an encoded string. It should be
  used on an interface to the system which must accept a string and not unicode.

  Args:
    string: The string to convert.

  Returns:
    an encoded string.
  """
  if type(string) == unicode:
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
  if type(string) != unicode:
    try:
      return string.__unicode__()
    except (AttributeError, UnicodeError):
      return str(string).decode("utf8", "ignore")

  return string


def Xor(string, key):
  """Returns a string where each character has been xored with key."""
  return "".join([chr(c ^ key) for c in bytearray(string)])


def XorByteArray(array, key):
  """Xors every item in the array with key and returns it."""
  for i in xrange(len(array)):
    array[i] ^= key
  return array


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
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp))


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


def JoinPath(stem, *parts):
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


def GuessWindowsFileNameFromString(str_in):
  """Take a commandline string and guess the file path.

  Commandline strings can be space separated and contain options.
  e.g. C:\\Program Files\\ACME Corporation\\wiz.exe /quiet /blah

  See here for microsoft doco on commandline parsing:
  http://msdn.microsoft.com/en-us/library/windows/desktop/ms682425(v=vs.85).aspx

  Args:
    str_in: commandline string
  Returns:
    list of candidate filename strings.
  """
  guesses = []
  current_str = ""

  # If paths are quoted as recommended, just use that path.
  if str_in.startswith(("\"", "'")):
    guesses = [shlex.split(str_in)[0]]
  else:
    for component in str_in.split(" "):
      if current_str:
        current_str = " ".join((current_str, component))
      else:
        current_str = component
      guesses.append(current_str)

  return guesses


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


def Grouper(iterable, n):
  """Group iterable into lists of size n. Last list will be short."""
  items = []
  for count, item in enumerate(iterable):
    items.append(item)
    if (count + 1) % n == 0:
      yield items
      items = []
  if items:
    yield items


def EncodeReasonString(reason):
  return base64.urlsafe_b64encode(SmartStr(reason))


def DecodeReasonString(reason):
  return SmartUnicode(base64.urlsafe_b64decode(SmartStr(reason)))


# Regex chars that should not be in a regex
disallowed_chars = re.compile(r"[[\](){}+*?.$^\\]")


def EscapeRegex(string):
  return re.sub(disallowed_chars,
                lambda x: "\\" + x.group(0),
                SmartUnicode(string))


def GeneratePassphrase(length=20):
  """Create a 20 char passphrase with easily typeable chars."""
  valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  valid_chars += "0123456789 ,-_&$#"
  return "".join(random.choice(valid_chars) for i in range(length))


class PRNG(object):
  """An optimized PRNG."""

  random_list = []

  @classmethod
  def GetUShort(cls):
    return cls.GetULong() & 0xFFFF

  @classmethod
  def GetULong(cls):
    while True:
      try:
        return cls.random_list.pop()
      except IndexError:
        PRNG.random_list = list(
            struct.unpack("=" + "L" * 1000,
                          os.urandom(struct.calcsize("=L") * 1000)))


def FormatNumberAsString(num):
  """Return a large number in human readable form."""
  for suffix in ["b", "KB", "MB", "GB"]:
    if num < 1024.0:
      return "%3.2f%s" % (num, suffix)
    num /= 1024.0
  return "%3.1f%s" % (num, "TB")


class NotAValue(object):
  pass


def issubclass(obj, cls):    # pylint: disable=redefined-builtin,g-bad-name
  """A sane implementation of issubclass.

  See http://bugs.python.org/issue10569

  Python bare issubclass must be protected by an isinstance test first since it
  can only work on types and raises when provided something which is not a type.

  Args:
    obj: Any object or class.
    cls: The class to check against.

  Returns:
    True if obj is a subclass of cls and False otherwise.
  """
  return isinstance(obj, type) and __builtin__.issubclass(obj, cls)


class HeartbeatQueue(Queue.Queue):
  """A queue that periodically calls a provided callback while waiting."""

  def __init__(self, callback=None, fast_poll_time=60, *args, **kw):
    Queue.Queue.__init__(self, *args, **kw)
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
          message = Queue.Queue.get(self, block=True, timeout=poll_interval)
        else:
          time.sleep(poll_interval)
          message = Queue.Queue.get(self, block=False)
        break

      except Queue.Empty:
        self.callback()

    self.last_item_time = time.time()
    return message


class StreamingZipWriter(object):
  """A streaming zip file writer which can copy from file like objects.

  The streaming writer should be capable of compressing files of arbitrary
  size without eating all the memory. It's built on top of Python's zipfile
  module, but has to use some hacks, as standard library doesn't provide
  all the necessary API to do streaming writes.
  """

  def __init__(self, fd_or_path, mode="w", compression=zipfile.ZIP_STORED):
    """Open streaming ZIP file with mode read "r", write "w" or append "a".

    Args:
      fd_or_path: Either the path to the file, or a file-like object.
                  If it is a path, the file will be opened and closed by
                  ZipFile.
      mode: The mode can be either read "r", write "w" or append "a".
      compression: ZIP_STORED (no compression) or ZIP_DEFLATED (requires zlib).
    """

    self.zip_fd = zipfile.ZipFile(fd_or_path, mode,
                                  compression=zipfile.ZIP_STORED,
                                  allowZip64=True)
    self.out_fd = self.zip_fd.fp
    self.compression = compression

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def Close(self):
    self.zip_fd.close()

  def GenerateZipInfo(self, arcname=None, compress_type=None, st=None):
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
      st = os.stat_result((0100644, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    mtime = time.localtime(st.st_mtime or time.time())
    date_time = mtime[0:6]
    # Create ZipInfo instance to store file information
    if arcname is None:
      raise ValueError("An arcname must be provided.")

    zinfo = zipfile.ZipInfo(arcname, date_time)
    zinfo.external_attr = (st[0] & 0xFFFF) << 16L      # Unix attributes

    if compress_type is None:
      zinfo.compress_type = self.compression
    else:
      zinfo.compress_type = compress_type

    zinfo.file_size = 0
    zinfo.compress_size = 0
    zinfo.flag_bits = 0x08  # Setting data descriptor flag.
    zinfo.CRC = 0x08074b50  # Predefined CRC for archives using data
                            # descriptors.
    # This fills an empty Info-ZIP Unix extra field.
    zinfo.extra = struct.pack("<HHIIHH", 0x5855, 12,
                              0,  # time of last access (UTC/GMT)
                              0,  # time of last modification (UTC/GMT)
                              0,  # user ID
                              0)  # group ID
    return zinfo

  def WriteSymlink(self, src_arcname, dst_arcname):
    """Writes a symlink into the archive."""
    # Inspired by:
    # http://www.mail-archive.com/python-list@python.org/msg34223.html

    src_arcname = SmartStr(src_arcname)
    dst_arcname = SmartStr(dst_arcname)

    zinfo = zipfile.ZipInfo(dst_arcname)
    # This marks a symlink.
    zinfo.external_attr = (0644 | 0120000) << 16
    # This marks create_system as UNIX.
    zinfo.create_system = 3

    # This fills the ASi UNIX extra field, see:
    # http://www.opensource.apple.com/source/zip/zip-6/unzip/unzip/proginfo/extra.fld
    zinfo.extra = struct.pack("<HHIHIHHs", 0x756e, len(src_arcname) + 14,
                              0,        # CRC-32 of the remaining data
                              0120000,  # file permissions
                              0,        # target file size
                              0,        # user ID
                              0,        # group ID
                              src_arcname)

    self.zip_fd.writestr(zinfo, src_arcname)

  def WriteFromFD(self, src_fd, arcname=None, compress_type=None, st=None):
    """Write a zip member from a file like object.

    Args:
      src_fd: A file like object, must support seek(), tell(), read().
      arcname: The name in the archive this should take.
      compress_type: Compression type (zipfile.ZIP_DEFLATED, or ZIP_STORED)
      st: An optional stat object to be used for setting headers.

    Raises:
      RuntimeError: If the zip if already closed.
    """
    zinfo = self.GenerateZipInfo(arcname=arcname, compress_type=compress_type,
                                 st=st)

    crc = 0
    compress_size = 0

    if not self.out_fd:
      raise RuntimeError(
          "Attempt to write to ZIP archive that was already closed")

    zinfo.header_offset = self.out_fd.tell()
    # Call _writeCheck(zinfo) to do sanity checking on zinfo structure that
    # we've constructed.
    self.zip_fd._writecheck(zinfo)  # pylint: disable=protected-access
    # Mark ZipFile as dirty. We have to keep self.zip_fd's internal state
    # coherent so that it behaves correctly when close() is called.
    self.zip_fd._didModify = True   # pylint: disable=protected-access

    # Write FileHeader now. It's incomplete, but CRC and uncompressed/compressed
    # sized will be written later in data descriptor.
    self.out_fd.write(zinfo.FileHeader())

    if zinfo.compress_type == zipfile.ZIP_DEFLATED:
      cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                              zlib.DEFLATED, -15)
    else:
      cmpr = None

    file_size = 0
    while 1:
      buf = src_fd.read(1024 * 8)
      if not buf:
        break
      file_size += len(buf)
      crc = zipfile.crc32(buf, crc) & 0xffffffff

      if cmpr:
        buf = cmpr.compress(buf)
        compress_size += len(buf)
      self.out_fd.write(buf)

    if cmpr:
      buf = cmpr.flush()
      compress_size += len(buf)
      zinfo.compress_size = compress_size
      self.out_fd.write(buf)
    else:
      zinfo.compress_size = file_size

    zinfo.CRC = crc
    zinfo.file_size = file_size
    if file_size > zipfile.ZIP64_LIMIT or compress_size > zipfile.ZIP64_LIMIT:
      # Writing data descriptor ZIP64-way:
      # crc-32                          8 bytes (little endian)
      # compressed size                 8 bytes (little endian)
      # uncompressed size               8 bytes (little endian)
      self.out_fd.write(struct.pack("<LLL", crc, compress_size, file_size))
    else:
      # Writing data descriptor non-ZIP64-way:
      # crc-32                          4 bytes (little endian)
      # compressed size                 4 bytes (little endian)
      # uncompressed size               4 bytes (little endian)
      self.out_fd.write(struct.pack("<III", crc, compress_size, file_size))

    # Register the file in the zip file, so that central directory gets
    # written correctly.
    self.zip_fd.filelist.append(zinfo)
    self.zip_fd.NameToInfo[zinfo.filename] = zinfo


class StreamingTarWriter(object):
  """A streaming tar file writer which can copy from file like objects.

  The streaming writer should be capable of compressing files of arbitrary
  size without eating all the memory. It's built on top of Python's tarfile
  module.
  """

  def __init__(self, fd_or_path, mode="w"):
    if hasattr(fd_or_path, "write"):
      self.tar_fd = tarfile.open(mode=mode, fileobj=fd_or_path,
                                 encoding="utf-8")
    else:
      self.tar_fd = tarfile.open(name=fd_or_path, mode=mode, encoding="utf-8")

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def Close(self):
    self.tar_fd.close()

  def WriteSymlink(self, src_arcname, dst_arcname):
    """Writes a symlink into the archive."""

    info = self.tar_fd.tarinfo()
    info.tarfile = self.tar_fd
    info.name = SmartStr(dst_arcname)
    info.size = 0
    info.mtime = time.time()
    info.type = tarfile.SYMTYPE
    info.linkname = SmartStr(src_arcname)

    self.tar_fd.addfile(info)

  def WriteFromFD(self, src_fd, arcname=None, st=None):
    """Write an archive member from a file like object.

    Args:
      src_fd: A file like object, must support seek(), tell(), read().
      arcname: The name in the archive this should take.
      st: A stat object to be used for setting headers.

    Raises:
      ValueError: If st is omitted.
    """

    if st is None:
      raise ValueError("Stat object can't be None.")

    info = self.tar_fd.tarinfo()
    info.tarfile = self.tar_fd
    info.type = tarfile.REGTYPE
    info.name = SmartStr(arcname)
    info.size = st.st_size
    info.mode = st.st_mode
    info.mtime = st.st_mtime or time.time()

    self.tar_fd.addfile(info, src_fd)


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


class DataObject(dict):
  """This class wraps a dict and provides easier access functions."""

  def Register(self, item, value=None):
    if item in self:
      raise AttributeError("Item %s already registered." % item)

    self[item] = value

  def __setattr__(self, item, value):
    self[item] = value

  def __getattr__(self, item):
    try:
      return self[item]
    except KeyError as e:
      raise AttributeError(e)

  def __dir__(self):
    return sorted(self.keys()) + dir(self.__class__)

  def __str__(self):
    result = []
    for k, v in self.items():
      tmp = "  %s = " % k
      try:
        for line in SmartUnicode(v).splitlines():
          tmp += "    %s\n" % line
      except Exception as e:  # pylint: disable=broad-except
        tmp += "Error: %s\n" % e

      result.append(tmp)

    return "{\n%s}\n" % "".join(result)
