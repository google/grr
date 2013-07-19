#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""This file contains various utility classes used by GRR."""



import base64
import os
import random
import re
import socket
import shutil
import struct
import tempfile
import threading
import time



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

  # Class wide constant
  exit = False
  threads = []

  def __init__(self, target=None, args=None, kwargs=None, sleep_time=10, **kw):
    self.target = target
    self.args = args or ()
    self.kwargs = kwargs or {}
    self.sleep_time = sleep_time

    super(InterruptableThread, self).__init__(**kw)
    # Do not hold up program exit
    self.daemon = True

  def Iterate(self):
    """This will be repeatedly called between sleeps."""

  def run(self):
    while not self.exit:
      if self.target:
        self.target(*self.args, **self.kwargs)
      else:
        self.Iterate()

      # During shutdown range can disappear leaving ugly error messages.
      if not range:
        self.exit = True
        continue

      for _ in range(self.sleep_time):
        if self.exit:
          break
        try:
          if time:
            time.sleep(1)
          else:
            self.exit = True
            break
        except (AttributeError, TypeError):
          # When the main thread exits, time might be already None. We should
          # just ignore that and exit as well.
          self.exit = True
          break


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
    """When pickled the cache is fushed."""
    self.Flush()
    return dict(max_size=self._limit)

  def __setstate__(self, state):
    self.__init__(max_size=state["max_size"])


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


class PickleableStore(FastStore):
  """A Cache which can be pickled."""

  @Synchronized
  def __getstate__(self):
    to_pickle = self.__dict__.copy()
    to_pickle["lock"] = None
    return to_pickle

  def __setstate__(self, state):
    self.__dict__ = state
    self.lock = threading.RLock()


# TODO(user): Eventually slot in Volatility parsing system in here
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
    Generator of tuples of (unique keys, list of items) where all items have the
    same key.  session id.
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

  return key_map.iteritems()


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


def JoinPath(*parts):
  """A sane version of os.path.join.

  The intention here is to append the stem to the path. The standard module
  removes the path if the stem begins with a /.

  Args:
     *parts: parts of the path to join. The first arg is always the root and
        directory traversal is not allowed.

  Returns:
     a normalized path.
  """
  # Ensure all path components are unicode
  parts = [SmartUnicode(path) for path in parts]

  return NormalizePath(u"/".join(parts))


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
  return base64.urlsafe_b64decode(SmartStr(reason))


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

  random_list_ushort = None
  random_list_ulong = None

  @classmethod
  def GetUShort(cls):
    if not cls.random_list_ushort:
      PRNG.random_list_ushort = list(
          struct.unpack("=" + "H" * 1000,
                        os.urandom(struct.calcsize("=H") * 1000)))

    return cls.random_list_ushort.pop()

  @classmethod
  def GetULong(cls):
    if not cls.random_list_ulong:
      PRNG.random_list_ulong = list(
          struct.unpack("=" + "L" * 1000,
                        os.urandom(struct.calcsize("=L") * 1000)))

    return cls.random_list_ulong.pop()


def FormatNumberAsString(num):
  """Return a large number in human readable form."""
  for suffix in ["b", "KB", "MB", "GB"]:
    if num < 1024.0:
      return "%3.2f%s" % (num, suffix)
    num /= 1024.0
  return "%3.1f%s" % (num, "TB")


class NotAValue(object):
  pass
