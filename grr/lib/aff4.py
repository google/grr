#!/usr/bin/env python
"""AFF4 interface implementation.

This contains an AFF4 data model implementation.
"""

import __builtin__
import abc
import itertools
import StringIO
import time
import zlib


import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import lexer
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import grr_rdf
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs


# Factor to convert from seconds to microseconds
MICROSECONDS = 1000000


# Age specifications for opening AFF4 objects.
NEWEST_TIME = "NEWEST_TIME"
ALL_TIMES = "ALL_TIMES"

# Just something to write on an index attribute to make it exist.
EMPTY_DATA = "X"

AFF4_PREFIXES = set(["aff4:", "metadata:"])


class Error(Exception):
  pass


class LockError(Error):
  pass


class OversizedRead(Error, IOError):
  pass


class InstantiationError(Error, IOError):
  pass


class ChunkNotFoundError(IOError):
  pass


class BadGetAttributeError(Exception):
  pass


class DeletionPool(object):
  """Pool used to optimize deletion of large object hierarchies."""

  def __init__(self, token=None):
    super(DeletionPool, self).__init__()

    if token is None:
      raise ValueError("token can't be None")

    self._objects_cache = {}
    self._children_lists_cache = {}
    self._urns_for_deletion = set()

    self._token = token

  def _ObjectKey(self, urn, mode):
    return u"%s:%s" % (mode, utils.SmartUnicode(urn))

  def Open(self, urn, aff4_type=None, mode="r"):
    """Opens the named object.

    DeletionPool will only open the object if it's not in the pool already.
    Otherwise it will just return the cached version. Objects are cached
    based on their urn and mode. I.e. same object opened with mode="r" and
    mode="rw" will be actually opened two times and cached separately.

    DeletionPool's Open() also doesn't follow symlinks.

    Args:
      urn: The urn to open.
      aff4_type: If this parameter is set, we raise an IOError if
          the object is not an instance of this type.
      mode: The mode to open the file with.

    Returns:
      An AFF4Object instance.

    Raises:
      IOError: If the object is not of the required type.
    """
    key = self._ObjectKey(urn, mode)

    try:
      obj = self._objects_cache[key]
    except KeyError:
      obj = FACTORY.Open(urn, mode=mode, follow_symlinks=False,
                         token=self._token)
      self._objects_cache[key] = obj

    if (aff4_type is not None and
        not isinstance(obj, AFF4Object.classes[aff4_type])):
      raise InstantiationError(
          "Object %s is of type %s, but required_type is %s" % (
              urn, obj.__class__.__name__, aff4_type))

    return obj

  def MultiOpen(self, urns, aff4_type=None, mode="r"):
    """Opens many urns efficiently, returning cached objects when possible."""
    result = []
    not_opened_urns = []

    for urn in urns:
      key = self._ObjectKey(urn, mode)
      try:
        result.append(self._objects_cache[key])
      except KeyError:
        not_opened_urns.append(urn)

    if not_opened_urns:
      objs = FACTORY.MultiOpen(not_opened_urns, follow_symlinks=False,
                               mode=mode, token=self._token)
      for obj in objs:
        result.append(obj)

        key = self._ObjectKey(obj.urn, mode)
        self._objects_cache[key] = obj

    if aff4_type is not None:
      type_checked_result = []
      for obj in result:
        if isinstance(obj, AFF4Object.classes[aff4_type]):
          type_checked_result.append(obj)

      return type_checked_result
    else:
      return result

  def ListChildren(self, urn):
    """Lists children of a given urn. Resulting list is cached."""
    result = self.MultiListChildren([urn])
    try:
      return result[urn]
    except KeyError:
      return []

  def MultiListChildren(self, urns):
    """Lists children of a bunch of given urns. Results are cached."""
    result = {}
    not_listed_urns = []

    for urn in urns:
      try:
        result[urn] = self._children_lists_cache[urn]
      except KeyError:
        not_listed_urns.append(urn)

    if not_listed_urns:
      for urn, children in FACTORY.MultiListChildren(
          not_listed_urns, token=self._token):
        result[urn] = self._children_lists_cache[urn] = children

      for urn in not_listed_urns:
        self._children_lists_cache.setdefault(urn, [])
        result.setdefault(urn, [])

    return result

  def RecursiveMultiListChildren(self, urns):
    """Recursively lists given urns. Results are cached."""
    result = {}

    checked_urns = set()
    not_cached_urns = []
    urns_to_check = urns
    while True:
      found_children = []

      for urn in urns_to_check:
        try:
          children = result[urn] = self._children_lists_cache[urn]
          found_children.extend(children)
        except KeyError:
          not_cached_urns.append(urn)

      checked_urns.update(urns_to_check)
      urns_to_check = set(found_children) - checked_urns

      if not urns_to_check:
        break

    for urn, children in FACTORY.RecursiveMultiListChildren(
        not_cached_urns, token=self._token):
      result[urn] = self._children_lists_cache[urn] = children

    return result

  def MarkForDeletion(self, urn):
    """Marks object and all of its children for deletion."""
    self.MultiMarkForDeletion([urn])

  def MultiMarkForDeletion(self, urns):
    """Marks multiple urns (and their children) for deletion."""
    all_children_urns = self.RecursiveMultiListChildren(urns)

    urns += list(itertools.chain.from_iterable(all_children_urns.values()))
    for urn in urns:
      self._urns_for_deletion.add(urn)

    objs = self.MultiOpen(urns)
    for obj in objs:
      obj.OnDelete(deletion_pool=self)

  @property
  def root_urns_for_deletion(self):
    """Roots of the graph of urns marked for deletion."""
    roots = set()
    for urn in self._urns_for_deletion:
      new_root = True

      fake_roots = []
      for root in roots:
        str_root = utils.SmartUnicode(root)
        str_urn = utils.SmartUnicode(urn)

        if str_urn.startswith(str_root):
          new_root = False
          break
        elif str_root.startswith(str_urn):
          fake_roots.append(root)

      if new_root:
        roots -= set(fake_roots)
        roots.add(urn)

    return roots

  @property
  def urns_for_deletion(self):
    """Urns marked for deletion."""
    return self._urns_for_deletion


class Factory(object):
  """A central factory for AFF4 objects."""

  def __init__(self):
    # This is a relatively short lived cache of objects.
    self.cache = utils.AgeBasedCache(
        max_size=config_lib.CONFIG["AFF4.cache_max_size"],
        max_age=config_lib.CONFIG["AFF4.cache_age"])
    self.intermediate_cache = utils.AgeBasedCache(
        max_size=config_lib.CONFIG["AFF4.intermediate_cache_max_size"],
        max_age=config_lib.CONFIG["AFF4.intermediate_cache_age"])

    # Create a token for system level actions. This token is used by other
    # classes such as HashFileStore and NSRLFilestore to create entries under
    # aff4:/files, as well as to create top level paths like aff4:/foreman
    self.root_token = access_control.ACLToken(username="GRRSystem",
                                              reason="Maintenance").SetUID()

    self.notification_rules = []
    self.notification_rules_timestamp = 0

  @classmethod
  def ParseAgeSpecification(cls, age):
    """Parses an aff4 age and returns a datastore age specification."""
    try:
      return (0, int(age))
    except (ValueError, TypeError):
      pass

    if age == NEWEST_TIME:
      return data_store.DB.NEWEST_TIMESTAMP
    elif age == ALL_TIMES:
      return data_store.DB.ALL_TIMESTAMPS
    elif len(age) == 2:
      start, end = age

      return (int(start), int(end))

    raise RuntimeError("Unknown age specification: %s" % age)

  def GetAttributes(self, urns, ignore_cache=False, token=None,
                    age=NEWEST_TIME):
    """Retrieves all the attributes for all the urns."""
    urns = set([utils.SmartUnicode(u) for u in urns])
    if not ignore_cache:
      for subject in list(urns):
        key = self._MakeCacheInvariant(subject, token, age)

        try:
          yield subject, self.cache.Get(key)
          urns.remove(subject)
        except KeyError:
          pass

    # If there are any urns left we get them from the database.
    if urns:
      for subject, values in data_store.DB.MultiResolvePrefix(
          urns, AFF4_PREFIXES, timestamp=self.ParseAgeSpecification(age),
          token=token, limit=None):

        # Ensure the values are sorted.
        values.sort(key=lambda x: x[-1], reverse=True)

        key = self._MakeCacheInvariant(subject, token, age)
        self.cache.Put(key, values)

        yield utils.SmartUnicode(subject), values

  def SetAttributes(self, urn, attributes, to_delete, add_child_index=True,
                    mutation_pool=None, sync=False, token=None):
    """Sets the attributes in the data store and update the cache."""
    # Force a data_store lookup next.
    try:
      # Expire all entries in the cache for this urn (for all tokens, and
      # timestamps)
      self.cache.ExpirePrefix(utils.SmartStr(urn) + ":")
    except KeyError:
      pass

    attributes[AFF4Object.SchemaCls.LAST] = [
        rdfvalue.RDFDatetime().Now().SerializeToDataStore()]
    to_delete.add(AFF4Object.SchemaCls.LAST)
    if mutation_pool:
      mutation_pool.MultiSet(urn, attributes, replace=False,
                             to_delete=to_delete)
    else:
      data_store.DB.MultiSet(urn, attributes, token=token,
                             replace=False, sync=sync, to_delete=to_delete)

    if add_child_index:
      self._UpdateChildIndex(urn, token, mutation_pool=mutation_pool)

  def _UpdateChildIndex(self, urn, token, mutation_pool=None):
    """Update the child indexes.

    This function maintains the index for direct child relations. When we set
    an AFF4 path, we always add an attribute like
    index:dir/%(childname)s to its parent. This is written
    asynchronously to its parent.

    In order to query for all direct children of an AFF4 object, we then simple
    get the attributes which match the regex index:dir/.+ which are the
    direct children.

    Args:
      urn: The AFF4 object for which we update the index.
      token: The token to use.
      mutation_pool: An optional MutationPool object to write to. If not given,
                     the data_store is used directly.
    """
    try:
      # Create navigation aids by touching intermediate subject names.
      while urn.Path() != "/":
        basename = urn.Basename()
        dirname = rdfvalue.RDFURN(urn.Dirname())

        try:
          self.intermediate_cache.Get(urn)
          return
        except KeyError:
          attributes = {
              # This updates the directory index.
              "index:dir/%s" % utils.SmartStr(basename): [EMPTY_DATA],
          }
          # This is a performance optimization. On the root there is no point
          # setting the last access time since it gets accessed all the time.
          # TODO(user): Can we get rid of the index in the root node entirely?
          # It's too big to query anyways...
          if dirname != u"/":
            attributes[AFF4Object.SchemaCls.LAST] = [
                rdfvalue.RDFDatetime().Now().SerializeToDataStore()]

          if mutation_pool:
            mutation_pool.MultiSet(dirname, attributes, replace=True)
          else:
            data_store.DB.MultiSet(dirname, attributes,
                                   token=token, replace=True, sync=False)

          self.intermediate_cache.Put(urn, 1)

          urn = dirname

    except access_control.UnauthorizedAccess:
      pass

  def _DeleteChildFromIndex(self, urn, token):
    try:
      basename = urn.Basename()
      dirname = rdfvalue.RDFURN(urn.Dirname())

      try:
        self.intermediate_cache.ExpireObject(urn.Path())
      except KeyError:
        pass

      data_store.DB.DeleteAttributes(
          dirname, ["index:dir/%s" % utils.SmartStr(basename)], token=token,
          sync=False)
      data_store.DB.MultiSet(dirname, {
          AFF4Object.SchemaCls.LAST: [
              rdfvalue.RDFDatetime().Now().SerializeToDataStore()],
      }, token=token, replace=True, sync=False)

    except access_control.UnauthorizedAccess:
      pass

  def _ExpandURNComponents(self, urn, unique_urns):
    """This expands URNs.

    This method breaks the urn into all the urns from its path components and
    adds them to the set unique_urns.

    Args:
      urn: An RDFURN.
      unique_urns: A set to add the components of the urn to.
    """

    x = ROOT_URN
    for component in rdfvalue.RDFURN(urn).Path().split("/"):
      if component:
        x = x.Add(component)
        unique_urns.add(x)

  def _MakeCacheInvariant(self, urn, token, age):
    """Returns an invariant key for an AFF4 object.

    The object will be cached based on this key. This function is specifically
    extracted to ensure that we encapsulate all security critical aspects of the
    AFF4 object so that objects do not leak across security boundaries.

    Args:
       urn: The urn of the object.
       token: The access token used to receive the object.
       age: The age policy used to build this object. Should be one
            of ALL_TIMES, NEWEST_TIME or a range.

    Returns:
       A key into the cache.
    """
    return "%s:%s:%s" % (utils.SmartStr(urn), utils.SmartStr(token),
                         self.ParseAgeSpecification(age))

  def CreateWithLock(self, urn, aff4_type, token=None, age=NEWEST_TIME,
                     ignore_cache=False, force_new_version=True,
                     blocking=True, blocking_lock_timeout=10,
                     blocking_sleep_interval=1, lease_time=100):
    """Creates a new object and locks it.

    Similar to OpenWithLock below, this creates a locked object. The difference
    is that when you call CreateWithLock, the object does not yet have to exist
    in the data store.

    Args:
      urn: The object to create.
      aff4_type: The desired type for this object.
      token: The Security Token to use for opening this item.
      age: The age policy used to build this object. Only makes sense when mode
           has "r".
      ignore_cache: Bypass the aff4 cache.
      force_new_version: Forces the creation of a new object in the data_store.
      blocking: When True, wait and repeatedly try to grab the lock.
      blocking_lock_timeout: Maximum wait time when sync is True.
      blocking_sleep_interval: Sleep time between lock grabbing attempts. Used
          when blocking is True.
      lease_time: Maximum time the object stays locked. Lock will be considered
          released when this time expires.

    Returns:
      An AFF4 object of the desired type and mode.

    Raises:
      AttributeError: If the mode is invalid.
    """

    transaction = self._AcquireLock(
        urn, token=token, blocking=blocking,
        blocking_lock_timeout=blocking_lock_timeout,
        blocking_sleep_interval=blocking_sleep_interval,
        lease_time=lease_time)

    # Since we now own the data store subject, we can simply create the aff4
    # object in the usual way.
    return self.Create(
        urn, aff4_type, mode="rw", ignore_cache=ignore_cache,
        token=token, age=age, force_new_version=force_new_version,
        transaction=transaction)

  def OpenWithLock(self, urn, aff4_type=None, token=None,
                   age=NEWEST_TIME, blocking=True, blocking_lock_timeout=10,
                   blocking_sleep_interval=1, lease_time=100):
    """Open given urn and locks it.

    Opens an object and locks it for 'lease_time' seconds. OpenWithLock can
    only be used in 'with ...' statement. The lock is released when code
    execution leaves 'with ...' block.

    The urn is always opened in "rw" mode. Symlinks are not followed in
    OpenWithLock() due to possible race conditions.

    Args:
      urn: The urn to open.
      aff4_type: If this optional parameter is set, we raise an
          InstantiationError if the object exists and is not an instance of this
          type. This check is important when a different object can be stored in
          this location.
      token: The Security Token to use for opening this item.
      age: The age policy used to build this object. Should be one of
         NEWEST_TIME, ALL_TIMES or a time range given as a tuple (start, end) in
         microseconds since Jan 1st, 1970.
      blocking: When True, wait and repeatedly try to grab the lock.
      blocking_lock_timeout: Maximum wait time when sync is True.
      blocking_sleep_interval: Sleep time between lock grabbing attempts. Used
          when blocking is True.
      lease_time: Maximum time the object stays locked. Lock will be considered
          released when this time expires.

    Raises:
      ValueError: The URN passed in is None.

    Returns:
      Context manager to be used in 'with ...' statement.
    """

    transaction = self._AcquireLock(
        urn, token=token, blocking=blocking,
        blocking_lock_timeout=blocking_lock_timeout,
        blocking_sleep_interval=blocking_sleep_interval,
        lease_time=lease_time)

    # Since we now own the data store subject, we can simply read the aff4
    # object in the usual way.
    return self.Open(urn, aff4_type=aff4_type, mode="rw", ignore_cache=True,
                     token=token, age=age, follow_symlinks=False,
                     transaction=transaction)

  def _AcquireLock(self, urn, token=None, blocking=None,
                   blocking_lock_timeout=None, lease_time=None,
                   blocking_sleep_interval=None):
    """This actually acquires the lock for a given URN."""
    timestamp = time.time()

    if token is None:
      token = data_store.default_token

    if urn is None:
      raise ValueError("URN cannot be None")

    urn = rdfvalue.RDFURN(urn)

    # Try to get a transaction object on this subject. Note that if another
    # transaction object exists, this will raise TransactionError, and we will
    # keep retrying until we can get the lock.
    while True:
      try:
        transaction = data_store.DB.Transaction(urn, lease_time=lease_time,
                                                token=token)
        break
      except data_store.TransactionError as e:
        if not blocking or time.time() - timestamp > blocking_lock_timeout:
          raise LockError(e)
        else:
          time.sleep(blocking_sleep_interval)

    return transaction

  def Copy(self, old_urn, new_urn, age=NEWEST_TIME, token=None, limit=None,
           sync=False):
    """Make a copy of one AFF4 object to a different URN."""
    if token is None:
      token = data_store.default_token

    values = {}
    for predicate, value, ts in data_store.DB.ResolvePrefix(
        old_urn, AFF4_PREFIXES,
        timestamp=self.ParseAgeSpecification(age),
        token=token, limit=limit):
      values.setdefault(predicate, []).append((value, ts))

    if values:
      data_store.DB.MultiSet(new_urn, values,
                             token=token, replace=False,
                             sync=sync)

  def Open(self, urn, aff4_type=None, mode="r", ignore_cache=False,
           token=None, local_cache=None, age=NEWEST_TIME, follow_symlinks=True,
           transaction=None):
    """Opens the named object.

    This instantiates the object from the AFF4 data store.
    Note that the root aff4:/ object is a container for all other
    objects. Opening it for reading will instantiate a AFF4Volume instance, even
    if the row does not exist.

    The mode parameter specifies, how the object should be opened. A read only
    mode will raise when calling Set() on it, while a write only object will
    never read from the data store. Note that its impossible to open an object
    with pure write support (since we have no idea what type it should be
    without reading the data base) - use Create() instead for purely write mode.

    Args:
      urn: The urn to open.

      aff4_type: If this parameter is set, we raise an IOError if
          the object is not an instance of this type. This check is important
          when a different object can be stored in this location. If mode is
          "w", this parameter will determine the type of the object and is
          mandatory.

      mode: The mode to open the file with.
      ignore_cache: Forces a data store read.
      token: The Security Token to use for opening this item.
      local_cache: A dict containing a cache as returned by GetAttributes. If
                   set, this bypasses the factory cache.

      age: The age policy used to build this object. Should be one of
         NEWEST_TIME, ALL_TIMES or a time range given as a tuple (start, end) in
         microseconds since Jan 1st, 1970.

      follow_symlinks: If object opened is a symlink, follow it.
      transaction: A transaction in case this object is opened under lock.

    Returns:
      An AFF4Object instance.

    Raises:
      IOError: If the object is not of the required type.
      AttributeError: If the requested mode is incorrect.
    """
    if mode not in ["w", "r", "rw"]:
      raise AttributeError("Invalid mode %s" % mode)

    if mode == "w":
      if aff4_type is None:
        raise AttributeError("Need a type to open in write only mode.")
      return self.Create(urn, aff4_type, mode=mode, token=token, age=age,
                         ignore_cache=ignore_cache, force_new_version=False,
                         transaction=transaction)

    urn = rdfvalue.RDFURN(urn)

    if token is None:
      token = data_store.default_token

    if "r" in mode and (local_cache is None or urn not in local_cache):
      # Warm up the cache. The idea is to prefetch all the path components in
      # the same round trip and make sure this data is in cache, so that as each
      # AFF4 object is instantiated it can read attributes from cache rather
      # than round tripping to the data store.
      unique_urn = set()
      self._ExpandURNComponents(urn, unique_urn)
      local_cache = dict(
          self.GetAttributes(unique_urn,
                             age=age, ignore_cache=ignore_cache,
                             token=token))

    # Read the row from the table. We know the object already exists if there is
    # some data in the local_cache already for this object.
    result = AFF4Object(urn, mode=mode, token=token, local_cache=local_cache,
                        age=age, follow_symlinks=follow_symlinks,
                        aff4_type=aff4_type,
                        object_exists=bool(local_cache.get(urn)),
                        transaction=transaction)

    # Now we have a AFF4Object, turn it into the type it is currently supposed
    # to be as specified by Schema.TYPE.
    existing_type = result.Get(result.Schema.TYPE, default="AFF4Volume")
    if existing_type:
      result = result.Upgrade(existing_type)

    if (aff4_type is not None and
        not isinstance(result, AFF4Object.classes[aff4_type])):
      raise InstantiationError(
          "Object %s is of type %s, but required_type is %s" % (
              urn, result.__class__.__name__, aff4_type))

    return result

  def MultiOpen(self, urns, mode="rw", ignore_cache=False, token=None,
                aff4_type=None, age=NEWEST_TIME, follow_symlinks=True):
    """Opens a bunch of urns efficiently."""

    if token is None:
      token = data_store.default_token

    if mode not in ["w", "r", "rw"]:
      raise RuntimeError("Invalid mode %s" % mode)

    symlinks = {}
    for urn, values in self.GetAttributes(urns, token=token, age=age):
      try:
        obj = self.Open(urn, mode=mode, ignore_cache=ignore_cache, token=token,
                        local_cache={urn: values}, age=age,
                        follow_symlinks=False)
        # We can't pass aff4_type to Open since it will raise on AFF4Symlinks.
        # Setting it here, if needed, so that BadGetAttributeError checking
        # works.
        if aff4_type:
          obj.aff4_type = aff4_type

        if follow_symlinks and isinstance(obj, AFF4Symlink):
          target = obj.Get(obj.Schema.SYMLINK_TARGET)
          if target is not None:
            symlinks[target] = obj.urn
        elif aff4_type:
          if isinstance(obj, AFF4Object.classes[aff4_type]):
            yield obj
        else:
          yield obj
      except IOError:
        pass

    if symlinks:
      for obj in self.MultiOpen(symlinks, mode=mode, ignore_cache=ignore_cache,
                                token=token, aff4_type=aff4_type, age=age):
        obj.symlink_urn = symlinks[obj.urn]
        yield obj

  def OpenDiscreteVersions(self, urn, mode="r", ignore_cache=False, token=None,
                           local_cache=None, age=ALL_TIMES,
                           follow_symlinks=True):
    """Returns all the versions of the object as AFF4 objects.

    Args:
      urn: The urn to open.
      mode: The mode to open the file with.
      ignore_cache: Forces a data store read.
      token: The Security Token to use for opening this item.
      local_cache: A dict containing a cache as returned by GetAttributes. If
                   set, this bypasses the factory cache.

      age: The age policy used to build this object. Should be one of
         ALL_TIMES or a time range
      follow_symlinks: If object opened is a symlink, follow it.

    Yields:
      An AFF4Object for each version.

    Raises:
      IOError: On bad open or wrong time range specified.

    This iterates through versions of an object, returning the newest version
    first, then each older version until the beginning of time.

    Note that versions are defined by changes to the TYPE attribute, and this
    takes the version between two TYPE attributes.
    In many cases as a user you don't want this, as you want to be returned an
    object with as many attributes as possible, instead of the subset of them
    that were Set between these two times.
    """
    if age == NEWEST_TIME or len(age) == 1:
      raise IOError("Bad age policy NEWEST_TIME for OpenDiscreteVersions.")
    if len(age) == 2:
      oldest_age = age[1]
    else:
      oldest_age = 0
    aff4object = FACTORY.Open(urn, mode=mode, ignore_cache=ignore_cache,
                              token=token, local_cache=local_cache, age=age,
                              follow_symlinks=follow_symlinks)

    # TYPE is always written last so we trust it to bound the version.
    # Iterate from newest to oldest.
    type_iter = aff4object.GetValuesForAttribute(aff4object.Schema.TYPE)
    version_list = [(t.age, str(t)) for t in type_iter]
    version_list.append((oldest_age, None))

    for i in range(0, len(version_list) - 1):
      age_range = (version_list[i + 1][0], version_list[i][0])
      # Create a subset of attributes for use in the new object that represents
      # this version.
      clone_attrs = {}
      for k, values in aff4object.synced_attributes.iteritems():
        reduced_v = []
        for v in values:
          if v.age > age_range[0] and v.age <= age_range[1]:
            reduced_v.append(v)
        clone_attrs.setdefault(k, []).extend(reduced_v)

      obj_cls = AFF4Object.classes[version_list[i][1]]
      new_obj = obj_cls(urn, mode=mode, parent=aff4object.parent,
                        clone=clone_attrs, token=token, age=age_range,
                        local_cache=local_cache,
                        follow_symlinks=follow_symlinks)
      new_obj.Initialize()  # This is required to set local attributes.
      yield new_obj

  def Stat(self, urns, token=None):
    """Returns metadata about all urns.

    Currently the metadata include type, and last update time.

    Args:
      urns: The urns of the objects to open.
      token: The token to use.

    Yields:
      A dict of metadata.

    Raises:
      RuntimeError: A string was passed instead of an iterable.
    """
    if token is None:
      token = data_store.default_token

    if isinstance(urns, basestring):
      raise RuntimeError("Expected an iterable, not string.")
    for subject, values in data_store.DB.MultiResolvePrefix(
        urns, ["aff4:type", "metadata:last"], token=token):
      res = dict(urn=rdfvalue.RDFURN(subject))
      for v in values:
        if v[0] == "aff4:type":
          res["type"] = v
        elif v[0] == "metadata:last":
          res["last"] = rdfvalue.RDFDatetime(v[1])
      yield res

  def Create(self, urn, aff4_type, mode="w", token=None, age=NEWEST_TIME,
             ignore_cache=False, force_new_version=True,
             object_exists=False, mutation_pool=None, transaction=None):
    """Creates the urn if it does not already exist, otherwise opens it.

    If the urn exists and is of a different type, this will also promote it to
    the specified type.

    Args:
      urn: The object to create.
      aff4_type: The desired type for this object.
      mode: The desired mode for this object.
      token: The Security Token to use for opening this item.
      age: The age policy used to build this object. Only makes sense when mode
           has "r".
      ignore_cache: Bypass the aff4 cache.
      force_new_version: Forces the creation of a new object in the data_store.
      object_exists: If we know the object already exists we can skip index
                     creation.
      mutation_pool: An optional MutationPool object to write to. If not given,
                     the data_store is used directly.
      transaction: For locked objects, a transaction is passed to the object.

    Returns:
      An AFF4 object of the desired type and mode.

    Raises:
      AttributeError: If the mode is invalid.
    """
    if mode not in ["w", "r", "rw"]:
      raise AttributeError("Invalid mode %s" % mode)

    if token is None:
      token = data_store.default_token

    if urn is not None:
      urn = rdfvalue.RDFURN(urn)

    if "r" in mode:
      # Check to see if an object already exists.
      try:
        existing = self.Open(
            urn, mode=mode, token=token, age=age,
            ignore_cache=ignore_cache, transaction=transaction)

        result = existing.Upgrade(aff4_type)

        # We can't pass aff4_type into the Open call since it will raise with a
        # type mismatch. We set it like this so BadGetAttributeError checking
        # works.
        if aff4_type:
          result.aff4_type = aff4_type

        if force_new_version and existing.Get(result.Schema.TYPE) != aff4_type:
          result.ForceNewVersion()
        return result
      except IOError:
        pass

    # Object does not exist, just make it.
    cls = AFF4Object.classes[str(aff4_type)]
    result = cls(urn, mode=mode, token=token, age=age, aff4_type=aff4_type,
                 object_exists=object_exists, mutation_pool=mutation_pool,
                 transaction=transaction)
    result.Initialize()
    if force_new_version:
      result.ForceNewVersion()

    return result

  def MultiDelete(self, urns, token=None):
    """Drop all the information about given objects.

    DANGEROUS! This recursively deletes all objects contained within the
    specified URN.

    Args:
      urns: Urns of objects to remove.
      token: The Security Token to use for opening this item.
    Raises:
      RuntimeError: If one of the urns is too short. This is a safety check to
      ensure the root is not removed.
    """
    urns = [rdfvalue.RDFURN(urn) for urn in urns]

    if token is None:
      token = data_store.default_token

    for urn in urns:
      if urn.Path() == "/":
        raise RuntimeError("Can't delete root URN. Please enter a valid URN")

    deletion_pool = DeletionPool(token=token)
    for urn in urns:
      deletion_pool.MarkForDeletion(urn)

    marked_root_urns = deletion_pool.root_urns_for_deletion
    marked_urns = deletion_pool.urns_for_deletion

    logging.debug(
        u"Found %d objects to remove when removing %s",
        len(marked_urns), urns)

    logging.debug(
        u"Removing %d root objects when removing %s: %s",
        len(marked_root_urns), urns, marked_root_urns)

    for root in marked_root_urns:
      # Only the index of the parent object should be updated. Everything
      # below the target object (along with indexes) is going to be
      # deleted.
      self._DeleteChildFromIndex(root, token)

    for urn_to_delete in marked_urns:
      try:
        self.intermediate_cache.ExpireObject(urn_to_delete.Path())
      except KeyError:
        pass

      data_store.DB.DeleteSubject(urn_to_delete, token=token, sync=False)
      logging.debug(u"%s deleted from data store", urn_to_delete)

    # Ensure this is removed from the cache as well.
    self.Flush()

    logging.debug("Removed %d objects", len(marked_urns))

  def Delete(self, urn, token=None):
    """Drop all the information about this object.

    DANGEROUS! This recursively deletes all objects contained within the
    specified URN.

    Args:
      urn: The object to remove.
      token: The Security Token to use for opening this item.
    Raises:
      RuntimeError: If the urn is too short. This is a safety check to ensure
      the root is not removed.
    """
    self.MultiDelete([urn], token=token)

  def RDFValue(self, name):
    return rdfvalue.RDFValue.classes.get(name)

  def AFF4Object(self, name):
    return AFF4Object.classes.get(name)

  def Merge(self, first, second):
    """Merge two AFF4 objects and return a new object.

    Args:
      first: The first object (Can be None).
      second: The second object (Can be None).

    Returns:
      A new object with the type of the latest object, but with both first and
      second's attributes.
    """
    if first is None: return second
    if second is None: return first

    # Make first the most recent object, and second the least recent:
    if first.Get("type").age < second.Get("type").age:
      first, second = second, first

    # Merge the attributes together.
    for k, v in second.synced_attributes.iteritems():
      first.synced_attributes.setdefault(k, []).extend(v)

    for k, v in second.new_attributes.iteritems():
      first.new_attributes.setdefault(k, []).extend(v)

    return first

  def MultiListChildren(self, urns, token=None, limit=None, age=NEWEST_TIME):
    """Lists bunch of directories efficiently.

    Args:
      urns: List of urns to list children.
      token: Security token.
      limit: Max number of children to list (NOTE: this is per urn).
      age: The age of the items to retrieve. Should be one of ALL_TIMES,
           NEWEST_TIME or a range.

    Yields:
       Tuples of Subjects and a list of children urns of a given subject.
    """
    checked_subjects = set()

    index_prefix = "index:dir/"
    for subject, values in data_store.DB.MultiResolvePrefix(
        urns, index_prefix, token=token,
        timestamp=Factory.ParseAgeSpecification(age),
        limit=limit):

      checked_subjects.add(subject)

      subject_result = []
      for predicate, _, timestamp in values:
        urn = rdfvalue.RDFURN(subject).Add(predicate[len(index_prefix):])
        urn.age = rdfvalue.RDFDatetime(timestamp)
        subject_result.append(urn)

      yield subject, subject_result

    for subject in set(urns) - checked_subjects:
      yield subject, []

  def ListChildren(self, urn, token=None, limit=None, age=NEWEST_TIME):
    """Lists bunch of directories efficiently.

    Args:
      urn: Urn to list children.
      token: Security token.
      limit: Max number of children to list.
      age: The age of the items to retrieve. Should be one of ALL_TIMES,
           NEWEST_TIME or a range.

    Returns:
      RDFURNs instances of each child.
    """
    _, children_urns = list(self.MultiListChildren(
        [urn], token=token, limit=limit, age=age))[0]
    return children_urns

  def RecursiveMultiListChildren(self, urns, token=None, limit=None,
                                 age=NEWEST_TIME):
    """Recursively lists bunch of directories.

    Args:
      urns: List of urns to list children.
      token: Security token.
      limit: Max number of children to list (NOTE: this is per urn).
      age: The age of the items to retrieve. Should be one of ALL_TIMES,
           NEWEST_TIME or a range.

    Yields:
       (subject<->children urns) tuples. RecursiveMultiListChildren will fetch
       children lists for initial set of urns and then will fetch children's
       children, etc.

       For example, for the following objects structure:
       a->
          b -> c
            -> d

       RecursiveMultiListChildren(['a']) will return:
       [('a', ['b']), ('b', ['c', 'd'])]
    """

    checked_urns = set()
    urns_to_check = urns
    while True:
      found_children = []

      for subject, values in self.MultiListChildren(
          urns_to_check, token=token, limit=limit, age=age):

        found_children.extend(values)
        yield subject, values

      checked_urns.update(urns_to_check)

      urns_to_check = set(found_children) - checked_urns
      if not urns_to_check:
        break

  def Flush(self):
    data_store.DB.Flush()
    self.cache.Flush()
    self.intermediate_cache.Flush()


class Attribute(object):
  """AFF4 schema attributes are instances of this class."""

  description = ""

  # A global registry of attributes by name. This ensures we do not accidentally
  # define the same attribute with conflicting types.
  PREDICATES = {}

  # A human readable name to be used in filter queries.
  NAMES = {}

  def __init__(self, predicate, attribute_type=rdfvalue.RDFString,
               description="", name=None, _copy=False, default=None, index=None,
               versioned=True, lock_protected=False,
               creates_new_object_version=True):
    """Constructor.

    Args:
       predicate: The name of this attribute - must look like a URL
             (e.g. aff4:contains). Will be used to store the attribute.
       attribute_type: The RDFValue type of this attributes.
       description: A one line description of what this attribute represents.
       name: A human readable name for the attribute to be used in filters.
       _copy: Used internally to create a copy of this object without
          registering.
       default: A default value will be returned if the attribute is not set on
          an object. This can be a constant or a callback which receives the fd
          itself as an arg.
       index: The name of the index to use for this attribute. If None, the
          attribute will not be indexed.
       versioned: Should this attribute be versioned? Non-versioned attributes
          always overwrite other versions of the same attribute.
       lock_protected: If True, this attribute may only be set if the object was
          opened via OpenWithLock().
       creates_new_object_version: If this is set, a write to this attribute
          will also write a new version of the parent attribute. This should be
          False for attributes where lots of entries are collected like logs.
    """
    self.name = name
    self.predicate = predicate
    self.attribute_type = attribute_type
    self.description = description
    self.default = default
    self.index = index
    self.versioned = versioned
    self.lock_protected = lock_protected
    self.creates_new_object_version = creates_new_object_version

    # Field names can refer to a specific component of an attribute
    self.field_names = []

    if not _copy:
      # Check the attribute registry for conflicts
      try:
        old_attribute = Attribute.PREDICATES[predicate]
        if old_attribute.attribute_type != attribute_type:
          msg = "Attribute %s defined with conflicting types (%s, %s)" % (
              predicate, old_attribute.attribute_type.__class__.__name__,
              attribute_type.__class__.__name__)
          logging.error(msg)
          raise RuntimeError(msg)
      except KeyError:
        pass

      # Register
      self.PREDICATES[predicate] = self
      if name:
        self.NAMES[name] = self

  def Copy(self):
    """Return a copy without registering in the attribute registry."""
    return Attribute(self.predicate, self.attribute_type, self.description,
                     self.name, _copy=True)

  def __call__(self, semantic_value=None, **kwargs):
    """A shortcut allowing us to instantiate a new type from an attribute."""
    result = semantic_value

    if semantic_value is None:
      result = self.attribute_type(**kwargs)

    # Coerce the value into the required type if needed.
    elif not isinstance(semantic_value, self.attribute_type):
      result = self.attribute_type(semantic_value, **kwargs)

    # We try to reuse the provided value and tag it as belonging to this
    # attribute. However, if the value is reused, we must make a copy.
    if getattr(result, "attribute_instance", None):
      result = result.Copy()

    result.attribute_instance = self

    return result

  def __str__(self):
    return self.predicate

  def __repr__(self):
    return "<Attribute(%s, %s)>" % (self.name, self.predicate)

  def __hash__(self):
    return hash(self.predicate)

  def __eq__(self, other):
    return str(self.predicate) == str(other)

  def __ne__(self, other):
    return str(self.predicate) != str(other)

  def __getitem__(self, item):
    result = self.Copy()
    result.field_names = item.split(".")

    return result

  def __len__(self):
    return len(self.field_names)

  def Fields(self):
    return self.attribute_type.Fields()

  @classmethod
  def GetAttributeByName(cls, name):
    # Support attribute names with a . in them:
    try:
      if "." in name:
        name, field = name.split(".", 1)
        return cls.NAMES[name][field]

      return cls.NAMES[name]
    except KeyError:
      raise AttributeError("Invalid attribute %s" % name)

  def GetRDFValueType(self):
    """Returns this attribute's RDFValue class."""
    result = self.attribute_type
    for field_name in self.field_names:
      # Support the new semantic protobufs.
      if issubclass(result, rdf_structs.RDFProtoStruct):
        try:
          result = result.type_infos.get(field_name).type
        except AttributeError:
          raise AttributeError("Invalid attribute %s" % field_name)
      else:
        # TODO(user): Remove and deprecate.
        # Support for the old RDFProto.
        result = result.rdf_map.get(field_name, rdfvalue.RDFString)

    return result

  def _GetSubField(self, value, field_names):
    for field_name in field_names:
      if value.HasField(field_name):
        value = getattr(value, field_name, None)
      else:
        value = None
        break

    if value is not None:
      yield value

  def GetSubFields(self, fd, field_names):
    """Gets all the subfields indicated by field_names.

    This resolves specifications like "Users.special_folders.app_data" where for
    each entry in the Users protobuf the corresponding app_data folder entry
    should be returned.

    Args:
      fd: The base RDFValue or Array.
      field_names: A list of strings indicating which subfields to get.
    Yields:
      All the subfields matching the field_names specification.
    """

    if isinstance(fd, rdf_protodict.RDFValueArray):
      for value in fd:
        for res in self._GetSubField(value, field_names):
          yield res
    else:
      for res in self._GetSubField(fd, field_names):
        yield res

  def GetValues(self, fd):
    """Return the values for this attribute as stored in an AFF4Object."""
    result = None
    for result in fd.new_attributes.get(self, []):
      # We need to interpolate sub fields in this rdfvalue.
      if self.field_names:
        for x in self.GetSubFields(result, self.field_names):
          yield x

      else:
        yield result

    for result in fd.synced_attributes.get(self, []):
      result = result.ToRDFValue()

      # We need to interpolate sub fields in this rdfvalue.
      if result is not None:
        if self.field_names:
          for x in self.GetSubFields(result, self.field_names):
            yield x

        else:
          yield result

    if result is None:
      default = self.GetDefault(fd)
      if default is not None:
        yield default

  def GetDefault(self, fd=None, default=None):
    """Returns a default attribute if it is not set."""
    if callable(self.default):
      return self.default(fd)

    if self.default is not None:
      # We can't return mutable objects here or the default might change for all
      # objects of this class.
      if isinstance(self.default, rdfvalue.RDFValue):
        default = self.default.Copy()
        default.attribute_instance = self
        return self(default)
      else:
        return self(self.default)

    if isinstance(default, rdfvalue.RDFValue):
      default = default.Copy()
      default.attribute_instance = self

    return default


class SubjectAttribute(Attribute):
  """An attribute which virtualises the subject."""

  def __init__(self):
    Attribute.__init__(self, "aff4:subject",
                       rdfvalue.Subject, "A subject pseudo attribute",
                       "subject")

  def GetValues(self, fd):
    return [rdfvalue.Subject(fd.urn)]


class AFF4Attribute(rdfvalue.RDFString):
  """An AFF4 attribute name."""

  def Validate(self):
    try:
      Attribute.GetAttributeByName(self._value)
    except (AttributeError, KeyError):
      raise type_info.TypeValueError(
          "Value %s is not an AFF4 attribute name" % self._value)


class ClassProperty(property):
  """A property which comes from the class object."""

  def __get__(self, _, owner):
    return self.fget.__get__(None, owner)()


class ClassInstantiator(property):
  """A property which instantiates the class on getting."""

  def __get__(self, _, owner):
    return self.fget()


class LazyDecoder(object):
  """An object which delays serialize and unserialize as late as possible.

  The current implementation requires the proxied object to be immutable.
  """

  def __init__(self, rdfvalue_cls=None, serialized=None, age=None,
               decoded=None):
    self.rdfvalue_cls = rdfvalue_cls
    self.serialized = serialized
    self.age = age
    self.decoded = decoded

  def ToRDFValue(self):
    if self.decoded is None:
      try:
        self.decoded = self.rdfvalue_cls(initializer=self.serialized,
                                         age=self.age)
      except rdfvalue.DecodeError:
        return None

    return self.decoded

  def FromRDFValue(self):
    return self.serialized


class AFF4Object(object):
  """Base class for all objects."""

  # We are a registered class.
  __metaclass__ = registry.MetaclassRegistry
  include_plugins_as_attributes = True

  # This property is used in GUIs to define behaviours. These can take arbitrary
  # values as needed. Behaviours are read only and set in the class definition.
  _behaviours = frozenset()

  # Should this object be synced back to the data store.
  _dirty = False

  # The data store transaction this object uses while it is being locked.
  transaction = None

  @property
  def locked(self):
    """Is this object currently locked?"""
    return self.transaction is not None

  @ClassProperty
  @classmethod
  def behaviours(cls):  # pylint: disable=g-bad-name
    return cls._behaviours

  # URN of the index for labels for generic AFF4Objects.
  labels_index_urn = rdfvalue.RDFURN("aff4:/index/labels/generic")

  # We define the parts of the schema for each AFF4 Object as an internal
  # class. As new objects extend this, they can add more attributes to their
  # schema by extending their parents. Note that the class must be named
  # SchemaCls.
  class SchemaCls(object):
    """The standard AFF4 schema."""

    # We use child indexes to navigate the direct children of an object.
    # If the additional storage requirements for the indexes are not worth it
    # then ADD_CHILD_INDEX should be False. Note however that it will no longer
    # be possible to find all the children of the parent object.
    ADD_CHILD_INDEX = True

    TYPE = Attribute("aff4:type", rdfvalue.RDFString,
                     "The name of the AFF4Object derived class.", "type")

    SUBJECT = SubjectAttribute()

    STORED = Attribute("aff4:stored", rdfvalue.RDFURN,
                       "The AFF4 container inwhich this object is stored.")

    LAST = Attribute("metadata:last", rdfvalue.RDFDatetime,
                     "The last time any attribute of this object was written.",
                     creates_new_object_version=False)

    # Note labels should not be Set directly but should be manipulated via
    # the AddLabels method.
    DEPRECATED_LABEL = Attribute("aff4:labels", grr_rdf.LabelList,
                                 "DEPRECATED: used LABELS instead.",
                                 "DEPRECATED_Labels",
                                 creates_new_object_version=False,
                                 versioned=False)

    LABELS = Attribute("aff4:labels_list", aff4_rdfvalues.AFF4ObjectLabelsList,
                       "Any object can have labels applied to it.", "Labels",
                       creates_new_object_version=False, versioned=False)

    LEASED_UNTIL = Attribute("aff4:lease", rdfvalue.RDFDatetime,
                             "The time until which the object is leased by a "
                             "particular caller.", versioned=False,
                             creates_new_object_version=False)

    LAST_OWNER = Attribute("aff4:lease_owner", rdfvalue.RDFString,
                           "The owner of the lease.", versioned=False,
                           creates_new_object_version=False)

    def __init__(self, aff4_type=None):
      """Init.

      Args:
        aff4_type: aff4 type string e.g. "VFSGRRClient" if specified by the user
          when the aff4 object was created. Or None.
      """
      self.aff4_type = aff4_type

    @classmethod
    def ListAttributes(cls):
      for attr in dir(cls):
        attr = getattr(cls, attr)
        if isinstance(attr, Attribute):
          yield attr

    @classmethod
    def GetAttribute(cls, name):
      for i in cls.ListAttributes():
        # Attributes are accessible by predicate or name
        if i.name == name or i.predicate == name:
          return i

    def __getattr__(self, attr):
      """Handle unknown attributes.

      Often the actual object returned is not the object that is expected. In
      those cases attempting to retrieve a specific named attribute would
      normally raise, e.g.:

      fd = aff4.FACTORY.Open(urn)
      fd.Get(fd.Schema.DOESNTEXIST, default_value)

      In this case we return None to ensure that the default is chosen.

      However, if the caller specifies a specific aff4_type, they expect the
      attributes of that object. If they are referencing a non-existent
      attribute this is an error and we should raise, e.g.:

      fd = aff4.FACTORY.Open(urn, aff4_type="something")
      fd.Get(fd.Schema.DOESNTEXIST, default_value)

      Args:
        attr: Some ignored attribute.
      Raises:
        BadGetAttributeError: if the object was opened with a specific type
      """
      if self.aff4_type:
        raise BadGetAttributeError(
            "Attribute %s does not exist on object opened with aff4_type %s" % (
                utils.SmartStr(attr), self.aff4_type))

      return None

  # Make sure that when someone references the schema, they receive an instance
  # of the class.
  @property
  def Schema(self):  # pylint: disable=g-bad-name
    return self.SchemaCls(self.aff4_type)

  def __init__(self, urn, mode="r", parent=None, clone=None, token=None,
               local_cache=None, age=NEWEST_TIME, follow_symlinks=True,
               aff4_type=None, object_exists=False, mutation_pool=None,
               transaction=None):
    if urn is not None:
      urn = rdfvalue.RDFURN(urn)
    self.urn = urn
    self.mode = mode
    self.parent = parent
    self.token = token
    self.age_policy = age
    self.follow_symlinks = follow_symlinks
    self.lock = utils.PickleableLock()
    self.mutation_pool = mutation_pool
    self.transaction = transaction

    if transaction and mutation_pool:
      raise ValueError("Cannot use a locked object with a mutation pool!")

    # If object was opened through a symlink, "symlink_urn" attribute will
    # contain a sylmink urn.
    self.symlink_urn = None

    # The object already exists in the data store - we do not need to update
    # indexes.
    self.object_exists = object_exists

    # This flag will be set whenever an attribute is changed that has the
    # creates_new_object_version flag set.
    self._new_version = False

    # Mark out attributes to delete when Flushing()
    self._to_delete = set()

    # If an explicit aff4 type is requested we store it here so we know to
    # verify aff4 attributes exist in the schema at Get() time.
    self.aff4_type = aff4_type

    # We maintain two attribute caches - self.synced_attributes reflects the
    # attributes which are synced with the data_store, while self.new_attributes
    # are new attributes which still need to be flushed to the data_store. When
    # this object is instantiated we populate self.synced_attributes with the
    # data_store, while the finish method flushes new changes.
    if clone is not None:
      if isinstance(clone, dict):
        # Just use these as the attributes, do not go to the data store. This is
        # a quick way of creating an object with data which was already fetched.
        self.new_attributes = {}
        self.synced_attributes = clone

      elif isinstance(clone, AFF4Object):
        # We were given another object to clone - we do not need to access the
        # data_store now.
        self.new_attributes = clone.new_attributes.copy()
        self.synced_attributes = clone.synced_attributes.copy()

      else:
        raise RuntimeError("Cannot clone from %s." % clone)
    else:
      self.new_attributes = {}
      self.synced_attributes = {}

      if "r" in mode:
        if local_cache:
          try:
            for attribute, value, ts in local_cache[utils.SmartUnicode(urn)]:
              self.DecodeValueFromAttribute(attribute, value, ts)
          except KeyError:
            pass
        else:
          # Populate the caches from the data store.
          for urn, values in FACTORY.GetAttributes([urn], age=age,
                                                   token=self.token):
            for attribute_name, value, ts in values:
              self.DecodeValueFromAttribute(attribute_name, value, ts)

    if clone is None:
      self.Initialize()

  def Initialize(self):
    """The method is called after construction to initialize the object.

    This will be called after construction, and each time the object is
    unserialized from the datastore.

    An AFF4 object contains attributes which can be populated from the
    database. This method is called to obtain a fully fledged object from
    a collection of attributes.
    """

  def DecodeValueFromAttribute(self, attribute_name, value, ts):
    """Given a serialized value, decode the attribute.

    Only attributes which have been previously defined are permitted.

    Args:
       attribute_name: The string name of the attribute.
       value: The serialized attribute value.
       ts: The timestamp of this attribute.
    """
    try:
      # Get the Attribute object from our schema.
      attribute = Attribute.PREDICATES[attribute_name]
      cls = attribute.attribute_type
      self._AddAttributeToCache(attribute, LazyDecoder(cls, value, ts),
                                self.synced_attributes)
    except KeyError:
      pass
    # TODO(user): uncomment as soon as some messages-flood protection
    # mechanisms are implemented in logging.debug().
    # if not attribute_name.startswith("index:"):
    #   logging.debug("Attribute %s not defined, skipping.", attribute_name)
    except (ValueError, rdfvalue.DecodeError):
      logging.debug("%s: %s invalid encoding. Skipping.",
                    self.urn, attribute_name)

  def _AddAttributeToCache(self, attribute_name, value, cache):
    """Helper to add a new attribute to a cache."""
    # If there's another value in cache with the same timestamp, the last added
    # one takes precedence. This helps a lot in tests that use FakeTime.
    attribute_list = cache.setdefault(attribute_name, [])
    if attribute_list and attribute_list[-1].age == value.age:
      attribute_list.pop()

    attribute_list.append(value)

  def CheckLease(self):
    """Check if our lease has expired, return seconds left.

    Returns:
      int: seconds left in the lease, 0 if not locked or lease is expired
    """
    if self.transaction:
      return self.transaction.CheckLease()

    return 0

  def UpdateLease(self, duration):
    """Updates the lease and flushes the object.

    The lease is set to expire after the "duration" time from the present
    moment.
    This method is supposed to be used when operation that requires locking
    may run for a time that exceeds the lease time specified in OpenWithLock().
    See flows/hunts locking for an example.

    Args:
      duration: Integer number of seconds. Lease expiry time will be set
                to "time.time() + duration".
    Raises:
      LockError: if the object is not currently locked or the lease has
                 expired.
    """
    if not self.locked:
      raise LockError(
          "Object must be locked to update the lease: %s." % self.urn)

    if self.CheckLease() == 0:
      raise LockError("Can not update lease that has already expired.")

    self.transaction.UpdateLease(duration)

  def Flush(self, sync=True):
    """Syncs this object with the data store, maintaining object validity."""
    if self.locked and self.CheckLease() == 0:
      raise LockError("Can not update lease that has already expired.")

    self._WriteAttributes(sync=sync)
    self._SyncAttributes()

    if self.parent:
      self.parent.Flush(sync=sync)

  def Close(self, sync=True):
    """Close and destroy the object.

    This is similar to Flush, but does not maintain object validity. Hence the
    object should not be interacted with after Close().

    Args:
       sync: Write the attributes synchronously to the data store.
    Raises:
       LockError: The lease for this object has expired.
    """
    if self.locked and self.CheckLease() == 0:
      raise LockError("Can not update lease that has already expired.")

    # Always sync when in a transaction.
    if self.locked:
      sync = True

    self._WriteAttributes(sync=sync)

    # Committing this transaction allows another thread to own it.
    if self.locked:
      self.transaction.Commit()

    if self.parent:
      self.parent.Close(sync=sync)

    # Interacting with a closed object is a bug. We need to catch this ASAP so
    # we remove all mode permissions from this object.
    self.mode = ""

  def OnDelete(self, deletion_pool=None):
    """Called when the object is about to be deleted.

    NOTE: If the implementation of this method has to list children or delete
    other dependent objects, make sure to use DeletionPool's API instead of a
    generic aff4.FACTORY one. DeletionPool is optimized for deleting large
    amounts of objects - it minimizes number of expensive data store calls,
    trying to group as many of them as possible into a single batch, and caches
    results of these calls.

    Args:
      deletion_pool: DeletionPool object used for this deletion operation.

    Raises:
      ValueError: if deletion pool is None.
    """
    if deletion_pool is None:
      raise ValueError("deletion_pool can't be None")

  @utils.Synchronized
  def _WriteAttributes(self, sync=True):
    """Write the dirty attributes to the data store."""
    # If the object is not opened for writing we do not need to flush it to the
    # data_store.
    if "w" not in self.mode:
      return

    if self.urn is None:
      raise RuntimeError("Storing of anonymous AFF4 objects not supported.")

    to_set = {}
    for attribute_name, value_array in self.new_attributes.iteritems():
      to_set_list = to_set.setdefault(attribute_name, [])
      for value in value_array:
        to_set_list.append((value.SerializeToDataStore(), value.age))

    if self._dirty:
      # We determine this object has a new version only if any of the versioned
      # attributes have changed. Non-versioned attributes do not represent a new
      # object version. The type of an object is versioned and represents a
      # version point in the life of the object.
      if self._new_version:
        to_set[self.Schema.TYPE] = [
            (rdfvalue.RDFString(self.__class__.__name__).SerializeToDataStore(),
             rdfvalue.RDFDatetime().Now())]

      # We only update indexes if the schema does not forbid it and we are not
      # sure that the object already exists.
      add_child_index = self.Schema.ADD_CHILD_INDEX
      if self.object_exists:
        add_child_index = False

      # Write the attributes to the Factory cache.
      FACTORY.SetAttributes(self.urn, to_set, self._to_delete,
                            add_child_index=add_child_index,
                            mutation_pool=self.mutation_pool,
                            sync=sync, token=self.token)

  @utils.Synchronized
  def _SyncAttributes(self):
    """Sync the new attributes to the synced attribute cache.

    This maintains object validity.
    """
    # This effectively moves all the values from the new_attributes to the
    # _attributes caches.
    for attribute, value_array in self.new_attributes.iteritems():
      if not attribute.versioned or self.age_policy == NEWEST_TIME:
        # Store the latest version if there are multiple unsynced versions.
        value = value_array[-1]
        self.synced_attributes[attribute] = [LazyDecoder(decoded=value,
                                                         age=value.age)]

      else:
        synced_value_array = self.synced_attributes.setdefault(attribute, [])
        for value in value_array:
          synced_value_array.append(LazyDecoder(decoded=value, age=value.age))

        synced_value_array.sort(key=lambda x: x.age, reverse=True)

    self.new_attributes = {}
    self._to_delete.clear()
    self._dirty = False
    self._new_version = False

  def _CheckAttribute(self, attribute, value):
    """Check that the value is of the expected type.

    Args:
       attribute: An instance of Attribute().
       value: An instance of RDFValue.
    Raises:
       ValueError: when the value is not of the expected type.
       AttributeError: When the attribute is not of type Attribute().
    """
    if not isinstance(attribute, Attribute):
      raise AttributeError("Attribute %s must be of type aff4.Attribute()",
                           attribute)

    if not isinstance(value, attribute.attribute_type):
      raise ValueError("Value for attribute %s must be of type %s()" % (
          attribute, attribute.attribute_type.__name__))

  def Copy(self, to_attribute, from_fd, from_attribute):
    values = from_fd.GetValuesForAttribute(from_attribute)
    for v in values:
      self.AddAttribute(to_attribute, v, age=v.age)

  def Set(self, attribute, value=None):
    """Set an attribute on this object.

    Set() is now a synonym for AddAttribute() since attributes are never
    deleted.

    Args:
      attribute: The attribute to set.
      value: The new value for this attribute.
    """
    # Specifically ignore None here. This allows us to safely copy attributes
    # from one object to another: fd.Set(fd2.Get(..))
    if attribute is None:
      return

    self.AddAttribute(attribute, value)

  def AddAttribute(self, attribute, value=None, age=None):
    """Add an additional attribute to this object.

    If value is None, attribute is expected to be already initialized with a
    value. For example:

    fd.AddAttribute(fd.Schema.CONTAINS("some data"))

    Args:
       attribute: The attribute name or an RDFValue derived from the attribute.
       value: The value the attribute will be set to.
       age: Age (timestamp) of the attribute. If None, current time is used.

    Raises:
       IOError: If this object is read only.
    """
    if "w" not in self.mode:
      raise IOError("Writing attribute %s to read only object." % attribute)

    if value is None:
      value = attribute
      attribute = value.attribute_instance

    # Check if this object should be locked in order to add the attribute.
    # NOTE: We don't care about locking when doing blind writes.
    if self.mode != "w" and attribute.lock_protected and not self.transaction:
      raise IOError("Object must be locked to write attribute %s." % attribute)

    self._CheckAttribute(attribute, value)

    # Does this represent a new version?
    if attribute.versioned:
      if attribute.creates_new_object_version:
        self._new_version = True

      # Update the time of this new attribute.
      if age:
        value.age = age
      else:
        value.age.Now()

    # Non-versioned attributes always replace previous versions and get written
    # at the earliest timestamp (so they appear in all objects).
    else:
      self._to_delete.add(attribute)
      self.synced_attributes.pop(attribute, None)
      self.new_attributes.pop(attribute, None)
      value.age = 0

    self._AddAttributeToCache(attribute, value, self.new_attributes)
    self._dirty = True

  @utils.Synchronized
  def DeleteAttribute(self, attribute):
    """Clears the attribute from this object."""
    if "w" not in self.mode:
      raise IOError("Deleting attribute %s from read only object." % attribute)

    # Check if this object should be locked in order to delete the attribute.
    # NOTE: We don't care about locking when doing blind writes.
    if self.mode != "w" and attribute.lock_protected and not self.transaction:
      raise IOError("Object must be locked to delete attribute %s." % attribute)

    if attribute in self.synced_attributes:
      self._to_delete.add(attribute)
      del self.synced_attributes[attribute]

    if attribute in self.new_attributes:
      del self.new_attributes[attribute]

    # Does this represent a new version?
    if attribute.versioned and attribute.creates_new_object_version:
      self._new_version = True

    self._dirty = True

  def IsAttributeSet(self, attribute):
    """Determine if the attribute is set.

    Args:
      attribute: The attribute to check.

    Returns:
      True if set, otherwise False.

    Checking Get against None doesn't work as Get will return a default
    attribute value. This determines if the attribute has been manually set.
    """
    return (attribute in self.synced_attributes or
            attribute in self.new_attributes)

  def Get(self, attribute, default=None):
    """Gets the attribute from this object."""
    if attribute is None:
      return default

    # Allow the user to specify the attribute by name.
    elif isinstance(attribute, str):
      attribute = Attribute.GetAttributeByName(attribute)

    # We can't read attributes from the data_store unless read mode was
    # specified. It is ok to read new attributes though.
    if "r" not in self.mode and (attribute not in self.new_attributes and
                                 attribute not in self.synced_attributes):
      raise IOError(
          "Fetching %s from object not opened for reading." % attribute)

    for result in self.GetValuesForAttribute(attribute, only_one=True):
      try:
        # The attribute may be a naked string or int - i.e. not an RDFValue at
        # all.
        result.attribute_instance = attribute
      except AttributeError:
        pass

      return result

    return attribute.GetDefault(self, default)

  def GetValuesForAttribute(self, attribute, only_one=False):
    """Returns a list of values from this attribute."""
    if not only_one and self.age_policy == NEWEST_TIME:
      raise RuntimeError("Attempting to read all attribute versions for an "
                         "object opened for NEWEST_TIME. This is probably "
                         "not what you want.")

    if attribute is None:
      return []

    elif isinstance(attribute, basestring):
      attribute = Attribute.GetAttributeByName(attribute)

    return attribute.GetValues(self)

  def Update(self, attribute=None, user=None, priority=None):
    """Requests the object refresh an attribute from the Schema."""

  def Upgrade(self, aff4_class):
    """Upgrades this object to the type specified.

    AFF4 Objects can be upgraded on the fly to other type - As long as the new
    type is derived from the current type. This feature allows creation of
    placeholder objects which can later be upgraded to the fully featured
    object.

    Note: It is not allowed to downgrade an object if that would result in a
    loss of information (since the new object has a smaller schema). This method
    tries to store the new object with its new attributes and will fail if any
    attributes can not be mapped.

    Args:
       aff4_class: A string representing the new class.

    Returns:
       an instance of the new class with all the same attributes as this current
       object.

    Raises:
       RuntimeError: When the object to upgrade is locked.
       AttributeError: When the new object can not accept some of the old
       attributes.
       InstantiationError: When we cannot instantiate the object type class.
    """
    # We are already of the required type
    if self.__class__.__name__ == aff4_class:
      return self

    # Instantiate the right type
    cls = self.classes.get(str(aff4_class))
    if cls is None:
      raise InstantiationError("Could not instantiate %s" % aff4_class)

    # It's not allowed to downgrade the object
    if isinstance(self, cls):
      # TODO(user): check what we should do here:
      #                 1) Nothing
      #                 2) raise
      #                 3) return self
      # Option 3) seems ok, but we need to be sure that we don't use
      # Create(mode='r') anywhere where code actually expects the object to be
      # downgraded.
      return self

    # NOTE: It is possible for attributes to become inaccessible here if the old
    # object has an attribute which the new object does not have in its
    # schema. The values of these attributes will not be available any longer in
    # the new object - usually because old attributes do not make sense in the
    # context of the new object.

    # Instantiate the class
    result = cls(self.urn, mode=self.mode, clone=self, parent=self.parent,
                 token=self.token, age=self.age_policy,
                 object_exists=self.object_exists,
                 follow_symlinks=self.follow_symlinks, aff4_type=self.aff4_type,
                 mutation_pool=self.mutation_pool, transaction=self.transaction)
    result.symlink_urn = self.urn
    result.Initialize()

    return result

  def ForceNewVersion(self):
    self._dirty = True
    self._new_version = True

  def __repr__(self):
    return "<%s@%X = %s>" % (self.__class__.__name__, hash(self), self.urn)

  # The following are used to ensure a bunch of AFF4Objects can be sorted on
  # their URNs.
  def __gt__(self, other):
    return self.urn > other

  def __lt__(self, other):
    return self.urn < other

  def __nonzero__(self):
    """We override this because we don't want to fall back to __len__.

    We want to avoid the case where a nonzero check causes iteration over all
    items. Subclasses may override as long as their implementation is efficient.

    Returns:
      True always
    """
    return True

  # Support the with protocol.
  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    try:
      self.Close()
    except Exception:  # pylint: disable=broad-except
      # If anything bad happens here, we must abort the transaction or the
      # object will stay locked.
      if self.transaction:
        self.transaction.Abort()

      raise

  def AddLabels(self, *labels_names, **kwargs):
    """Add labels to the AFF4Object."""
    if not self.token and "owner" not in kwargs:
      raise RuntimeError("Can't set label: No owner specified and "
                         "no access token available.")
    owner = kwargs.get("owner") or self.token.username

    current_labels = self.Get(self.Schema.LABELS, self.Schema.LABELS())
    for label_name in labels_names:
      label = aff4_rdfvalues.AFF4ObjectLabel(
          name=label_name,
          owner=owner,
          timestamp=rdfvalue.RDFDatetime().Now())
      current_labels.AddLabel(label)

    self.Set(current_labels)

  def RemoveLabels(self, *labels_names, **kwargs):
    """Remove specified labels from the AFF4Object."""
    if not self.token and "owner" not in kwargs:
      raise RuntimeError("Can't remove label: No owner specified and "
                         "no access token available.")
    owner = kwargs.get("owner") or self.token.username

    current_labels = self.Get(self.Schema.LABELS)
    for label_name in labels_names:
      label = aff4_rdfvalues.AFF4ObjectLabel(name=label_name, owner=owner)
      current_labels.RemoveLabel(label)

    self.Set(self.Schema.LABELS, current_labels)

  def SetLabels(self, *labels_names, **kwargs):
    self.ClearLabels()
    self.AddLabels(*labels_names, **kwargs)

  def ClearLabels(self):
    self.Set(self.Schema.LABELS, aff4_rdfvalues.AFF4ObjectLabelsList())

  def GetLabels(self):
    return self.Get(self.Schema.LABELS,
                    aff4_rdfvalues.AFF4ObjectLabelsList()).labels

  def GetLabelsNames(self, owner=None):
    labels = self.Get(self.Schema.LABELS, aff4_rdfvalues.AFF4ObjectLabelsList())
    return labels.GetLabelNames(owner=owner)


# This will register all classes into this modules's namespace regardless of
# where they are defined. This allows us to decouple the place of definition of
# a class (which might be in a plugin) from its use which will reference this
# module.
AFF4Object.classes = globals()


class AttributeExpression(lexer.Expression):
  """An expression which is used to filter attributes."""

  def SetAttribute(self, attribute):
    """Checks that attribute is a valid Attribute() instance."""
    # Grab the attribute registered for this name
    self.attribute = attribute
    self.attribute_obj = Attribute.GetAttributeByName(attribute)
    if self.attribute_obj is None:
      raise lexer.ParseError("Attribute %s not defined" % attribute)

  def SetOperator(self, operator):
    """Sets the operator for this expression."""
    self.operator = operator
    # Find the appropriate list of operators for this attribute
    attribute_type = self.attribute_obj.GetRDFValueType()
    operators = attribute_type.operators

    # Do we have such an operator?
    self.number_of_args, self.operator_method = operators.get(
        operator, (0, None))

    if self.operator_method is None:
      raise lexer.ParseError("Operator %s not defined on attribute '%s'" % (
          operator, self.attribute))

    self.operator_method = getattr(attribute_type, self.operator_method)

  def Compile(self, filter_implemention):
    """Returns the data_store filter implementation from the attribute."""
    return self.operator_method(self.attribute_obj,
                                filter_implemention, *self.args)


class AFF4QueryParser(lexer.SearchParser):
  expression_cls = AttributeExpression


class AFF4Volume(AFF4Object):
  """Volumes contain other objects.

  The AFF4 concept of a volume abstracts away how objects are stored. We simply
  define an AFF4 volume as a container of other AFF4 objects. The volume may
  implement any storage mechanism it likes, including virtualizing the objects
  contained within it.
  """
  _behaviours = frozenset(["Container"])

  class SchemaCls(AFF4Object.SchemaCls):
    CONTAINS = Attribute("aff4:contains", rdfvalue.RDFURN,
                         "An AFF4 object contained in this container.")

  def Query(self, filter_string="", limit=1000, age=NEWEST_TIME):
    """Lists all direct children of this object.

    The direct children of this object are fetched from the index.

    Args:
      filter_string: A filter string to be used to filter AFF4 objects.
      limit: Only fetch up to these many items.
      age: The age policy for the returned children.

    Returns:
      A generator over the children.
    """
    direct_child_urns = []
    for entry in data_store.DB.ResolvePrefix(self.urn, "index:dir/",
                                             limit=limit, token=self.token):
      _, filename = entry[0].split("/", 1)
      direct_child_urns.append(self.urn.Add(filename))

    children = self.OpenChildren(children=direct_child_urns,
                                 limit=limit, age=age)

    if filter_string:
      # Parse the query string.
      ast = AFF4QueryParser(filter_string).Parse()
      filter_obj = ast.Compile(AFF4Filter)

      children = filter_obj.Filter(children)

    return children

  def OpenMember(self, path, mode="r"):
    """Opens the member which is contained in us.

    Args:
       path: A string relative to our own URN or an absolute urn.
       mode: Mode for object.

    Returns:
       an AFF4Object instance.

    Raises:
      InstantiationError: If we are unable to open the member (e.g. it does not
        already exist.)
    """
    if isinstance(path, rdfvalue.RDFURN):
      child_urn = path
    else:
      child_urn = self.urn.Add(path)

    # Read the row from the table.
    result = AFF4Object(child_urn, mode=mode, token=self.token)

    # Get the correct type.
    aff4_type = result.Get(result.Schema.TYPE)
    if aff4_type:
      # Try to get the container.
      return result.Upgrade(aff4_type)

    raise InstantiationError("Path %s not found" % path)

  def ListChildren(self, limit=1000000, age=NEWEST_TIME):
    """Yields RDFURNs of all the children of this object.

    Args:
      limit: Total number of items we will attempt to retrieve.
      age: The age of the items to retrieve. Should be one of ALL_TIMES,
           NEWEST_TIME or a range in microseconds.

    Yields:
      RDFURNs instances of each child.
    """
    # Just grab all the children from the index.
    index_prefix = "index:dir/"
    for predicate, _, timestamp in data_store.DB.ResolvePrefix(
        self.urn, index_prefix, token=self.token,
        timestamp=Factory.ParseAgeSpecification(age), limit=limit):
      urn = self.urn.Add(predicate[len(index_prefix):])
      urn.age = rdfvalue.RDFDatetime(timestamp)
      yield urn

  def OpenChildren(self, children=None, mode="r", limit=1000000,
                   chunk_limit=100000, age=NEWEST_TIME):
    """Yields AFF4 Objects of all our direct children.

    This method efficiently returns all attributes for our children directly, in
    a few data store round trips. We use the directory indexes to query the data
    store.

    Args:
      children: A list of children RDFURNs to open. If None open all our
             children.
      mode: The mode the files should be opened with.
      limit: Total number of items we will attempt to retrieve.
      chunk_limit: Maximum number of items to retrieve at a time.
      age: The age of the items to retrieve. Should be one of ALL_TIMES,
           NEWEST_TIME or a range.
    Yields:
      Instances for each direct child.
    """
    if children is None:
      subjects = list(self.ListChildren(limit=limit, age=age))
    else:
      subjects = list(children)
    subjects.sort()
    # Read at most limit children at a time.
    while subjects:
      to_read = subjects[:chunk_limit]
      subjects = subjects[chunk_limit:]
      for child in FACTORY.MultiOpen(to_read, mode=mode, token=self.token,
                                     age=age):
        yield child

  @property
  def real_pathspec(self):
    """Returns a pathspec for an aff4 object even if there is none stored."""
    pathspec = self.Get(self.Schema.PATHSPEC)

    stripped_components = []
    parent = self

    # TODO(user): this code is potentially slow due to multiple separate
    # aff4.FACTORY.Open() calls. OTOH the loop below is executed very rarely -
    # only when we deal with deep files that got fetched alone and then
    # one of the directories in their path gets updated.
    while not pathspec and len(parent.urn.Split()) > 1:
      # We try to recurse up the tree to get a real pathspec.
      # These directories are created automatically without pathspecs when a
      # deep directory is listed without listing the parents.
      # Note /fs/os or /fs/tsk won't be updateable so we will raise IOError
      # if we try.
      stripped_components.append(parent.urn.Basename())
      pathspec = parent.Get(parent.Schema.PATHSPEC)
      parent = FACTORY.Open(parent.urn.Dirname(), token=self.token)

    if pathspec:
      if stripped_components:
        # We stripped pieces of the URL, time to add them back.
        new_path = utils.JoinPath(*reversed(stripped_components[:-1]))
        pathspec.Append(rdf_paths.PathSpec(path=new_path,
                                           pathtype=pathspec.last.pathtype))
    else:
      raise IOError("Item has no pathspec.")

    return pathspec


class AFF4Root(AFF4Volume):
  """The root of the VFS.

  This virtual collection contains the entire virtual filesystem, and therefore
  can be queried across the entire data store.
  """

  def Query(self, filter_string="", filter_obj=None, subjects=None, limit=100):
    """Filter the objects contained within this collection."""
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.filter)

    subjects = []
    result_set = data_store.DB.Query([], filter_obj, subjects=subjects,
                                     limit=limit, token=self.token)
    for match in result_set:
      subjects.append(match["subject"][0][0])

    # Open them all at once.
    result = data_store.ResultSet(FACTORY.MultiOpen(subjects, token=self.token))
    result.total_count = result_set.total_count

    return result

  def OpenMember(self, path, mode="r"):
    """If we get to the root without a container, virtualize an empty one."""
    urn = self.urn.Add(path)
    result = AFF4Volume(urn, mode=mode, token=self.token)
    result.Initialize()

    return result


class AFF4Symlink(AFF4Object):
  """This is a symlink to another AFF4 object.

  This means that opening this object will return the linked to object. To
  create a symlink, one must open the symlink for writing and set the
  Schema.SYMLINK_TARGET attribute.

  Opening the object for reading will return the linked to object.
  """

  class SchemaCls(AFF4Object.SchemaCls):
    SYMLINK_TARGET = Attribute("aff4:symlink_target", rdfvalue.RDFURN,
                               "The target of this link.")

  def __new__(cls, unused_urn, mode="r", clone=None, token=None,
              age=NEWEST_TIME, follow_symlinks=True, **_):
    # When first created, the symlink object is exposed.
    if mode == "w" or not follow_symlinks:
      return super(AFF4Symlink, cls).__new__(cls)
    elif clone is not None:
      # Get the real object (note, clone shouldn't be None during normal
      # object creation process):
      target_urn = clone.Get(cls.SchemaCls.SYMLINK_TARGET)
      result = FACTORY.Open(target_urn, mode=mode, age=age, token=token)
      result.symlink_urn = clone.urn
      return result
    else:
      raise RuntimeError("Unable to open symlink.")


class AFF4OverlayedVolume(AFF4Volume):
  """A special kind of volume with overlayed contained objects.

  This AFF4Volume can contain virtual overlays. An overlay is a path which
  appears to be contained within our object, but is in fact the same object. For
  example if self.urn = RDFURN('aff4:/C.123/foobar'):

  Opening aff4:/C.123/foobar/overlayed/ will return a copy of aff4:/C.123/foobar
  with the variable self.overlayed_path = "overlayed".

  This is used to effectively allow a single AFF4Volume to handle overlay
  virtual paths inside itself without resorting to storing anything in the
  database for every one of these object. Thus we can have a WinRegistry
  AFF4Volume that handles any paths within without having storage for each
  registry key.
  """
  overlayed_path = ""

  def IsPathOverlayed(self, path):  # pylint: disable=unused-argument
    """Should this path be overlayed.

    Args:
      path: A direct_child of ours.

    Returns:
      True if the path should be overlayed.
    """
    return False

  def OpenMember(self, path, mode="rw"):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, mode=mode, clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).OpenMember(path, mode)

  def CreateMember(self, path, aff4_type, mode="w", clone=None):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, mode=mode, clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).CreateMember(
        path, aff4_type, mode=mode, clone=clone)


class AFF4Stream(AFF4Object):
  """An abstract stream for reading data."""
  __metaclass__ = abc.ABCMeta

  # The read pointer offset.
  offset = 0
  size = 0

  class SchemaCls(AFF4Object.SchemaCls):
    # Note that a file on the remote system might have stat.st_size > 0 but if
    # we do not have any of the data available to read: size = 0.
    SIZE = Attribute("aff4:size", rdfvalue.RDFInteger,
                     "The total size of available data for this stream.",
                     "size", default=0)

    HASH = Attribute("aff4:hashobject", rdf_crypto.Hash,
                     "Hash object containing all known hash digests for"
                     " the object.")

  def __len__(self):
    return self.size

  def Initialize(self):
    super(AFF4Stream, self).Initialize()
    # This is the configurable default length for allowing Read to be called
    # without a specific length.
    self.max_unbound_read = config_lib.CONFIG["Server.max_unbound_read_size"]

  @abc.abstractmethod
  def Read(self, length):
    pass

  @abc.abstractmethod
  def Write(self, data):
    pass

  @abc.abstractmethod
  def Tell(self):
    pass

  @abc.abstractmethod
  def Seek(self, offset, whence=0):
    pass

  # These are file object conformant namings for library functions that
  # grr uses, and that expect to interact with 'real' file objects.
  def read(self, length=None):  # pylint: disable=invalid-name
    if length is None:
      length = self.size - self.offset
      if length > self.max_unbound_read:
        raise OversizedRead("Attempted to read file of size %s when "
                            "Server.max_unbound_read_size is %s" %
                            (self.size, self.max_unbound_read))
    return self.Read(length)

  seek = utils.Proxy("Seek")
  tell = utils.Proxy("Tell")
  close = utils.Proxy("Close")
  write = utils.Proxy("Write")
  flush = utils.Proxy("Flush")


class AFF4MemoryStreamBase(AFF4Stream):
  """A stream which keeps all data in memory.

  This is an abstract class, subclasses must define the CONTENT attribute
  in the Schema to be versioned or unversioned.
  """

  def Initialize(self):
    """Try to load the data from the store."""
    super(AFF4MemoryStreamBase, self).Initialize()
    contents = ""

    if "r" in self.mode:
      contents = self.Get(self.Schema.CONTENT)
      try:
        if contents is not None:
          contents = zlib.decompress(utils.SmartStr(contents))
      except zlib.error:
        pass

    self.fd = StringIO.StringIO(contents)
    self.size = len(contents)
    self.offset = 0

  def Truncate(self, offset=None):
    if offset is None:
      offset = self.offset
    self.fd = StringIO.StringIO(self.fd.getvalue()[:offset])
    self.size.Set(offset)

  def Read(self, length):
    return self.fd.read(int(length))

  def Write(self, data):
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")

    self._dirty = True
    self.fd.write(data)
    self.size = max(self.size, self.fd.tell())

  def Tell(self):
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def Flush(self, sync=True):
    if self._dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT(compressed_content))
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4MemoryStreamBase, self).Flush(sync=sync)

  def Close(self, sync=True):
    if self._dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT(compressed_content))
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4MemoryStreamBase, self).Close(sync=sync)

  def OverwriteAndClose(self, compressed_data, size, sync=True):
    """Directly overwrite the current contents.

    Replaces the data currently in the stream with compressed_data,
    and closes the object. Makes it possible to avoid recompressing
    the data.
    Args:
      compressed_data: The data to write, must be zlib compressed.
      size: The uncompressed size of the data.
      sync: Whether the close should be synchronous.
    """
    self.Set(self.Schema.CONTENT(compressed_data))
    self.Set(self.Schema.SIZE(size))
    super(AFF4MemoryStreamBase, self).Close(sync=sync)

  def GetContentAge(self):
    return self.Get(self.Schema.CONTENT).age


class AFF4MemoryStream(AFF4MemoryStreamBase):
  """A versioned stream which keeps all data in memory."""

  class SchemaCls(AFF4MemoryStreamBase.SchemaCls):
    CONTENT = Attribute("aff4:content", rdfvalue.RDFBytes,
                        "Total content of this file.", default="")


class AFF4UnversionedMemoryStream(AFF4MemoryStreamBase):
  """An unversioned stream which keeps all data in memory."""

  class SchemaCls(AFF4MemoryStreamBase.SchemaCls):
    CONTENT = Attribute("aff4:content", rdfvalue.RDFBytes,
                        "Total content of this file.", default="",
                        versioned=False)


# Still needed for backwards compatibility.
# TODO(user): Remove when current flows (Jan 14) have finished processing.
class AFF4ObjectCache(utils.FastStore):
  """A cache which closes its objects when they expire."""

  def KillObject(self, obj):
    obj.Close(sync=True)


class ChunkCache(utils.FastStore):
  """A cache which closes its objects when they expire."""

  def __init__(self, kill_cb=None, *args, **kw):
    self.kill_cb = kill_cb
    super(ChunkCache, self).__init__(*args, **kw)

  def KillObject(self, obj):
    if self.kill_cb:
      self.kill_cb(obj)

  def __getstate__(self):
    if self.kill_cb:
      raise NotImplementedError("Can't pickle callback.")
    return self.__dict__


class AFF4ImageBase(AFF4Stream):
  """An AFF4 Image is stored in segments.

  We are both an Image here and a volume (since we store the segments inside
  us). This is an abstract class, subclasses choose the type to use for chunks.
  """

  NUM_RETRIES = 10
  CHUNK_ID_TEMPLATE = "%010X"

  # This is the chunk size of each chunk. The chunksize can not be changed once
  # the object is created.
  chunksize = 64 * 1024

  # Subclasses should set the name of the type of stream to use for chunks.
  STREAM_TYPE = None

  class SchemaCls(AFF4Stream.SchemaCls):
    _CHUNKSIZE = Attribute("aff4:chunksize", rdfvalue.RDFInteger,
                           "Total size of each chunk.", default=64 * 1024)

    # Note that we can't use CONTENT.age in place of this, since some types
    # (specifically, AFF4Image) do not have a CONTENT attribute, since they're
    # stored in chunks. Rather than maximising the last updated time over all
    # chunks, we store it and update it as an attribute here.
    CONTENT_LAST = Attribute("metadata:content_last", rdfvalue.RDFDatetime,
                             "The last time any content was written.",
                             creates_new_object_version=False)

  def Initialize(self):
    """Build a cache for our chunks."""
    super(AFF4ImageBase, self).Initialize()
    self.offset = 0
    # A cache for segments - When we get pickled we want to discard them.
    self.chunk_cache = ChunkCache(self._WriteChunk, 100)

    if "r" in self.mode:
      self.size = int(self.Get(self.Schema.SIZE))
      # pylint: disable=protected-access
      self.chunksize = int(self.Get(self.Schema._CHUNKSIZE))
      # pylint: enable=protected-access
      self.content_last = self.Get(self.Schema.CONTENT_LAST)
    else:
      self.size = 0
      self.content_last = None

  def SetChunksize(self, chunksize):
    # pylint: disable=protected-access
    self.Set(self.Schema._CHUNKSIZE(chunksize))
    # pylint: enable=protected-access
    self.chunksize = int(chunksize)
    self.Truncate(0)

  def Seek(self, offset, whence=0):
    # This stream does not support random writing in "w" mode. When the stream
    # is opened in "w" mode we can not read from the data store and therefore we
    # can not merge writes with existing data. It only makes sense to append to
    # existing streams.
    if self.mode == "w":
      # Seeking to the end of the stream is ok.
      if not (whence == 2 and offset == 0):
        raise IOError("Can not seek with an AFF4Image opened for write only.")

    if whence == 0:
      self.offset = offset
    elif whence == 1:
      self.offset += offset
    elif whence == 2:
      self.offset = long(self.size) + offset

  def Tell(self):
    return self.offset

  def Truncate(self, offset=0):
    self._dirty = True
    self.size = offset
    self.offset = offset
    self.chunk_cache.Flush()

  def _ReadChunk(self, chunk):
    self._ReadChunks([chunk])
    return self.chunk_cache.Get(chunk)

  def _ReadChunks(self, chunks):
    chunk_names = {self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk): chunk
                   for chunk in chunks}
    for child in FACTORY.MultiOpen(
        chunk_names, mode="rw", token=self.token, age=self.age_policy):
      if isinstance(child, AFF4Stream):
        fd = StringIO.StringIO(child.read())
        fd.dirty = False
        fd.chunk = chunk_names[child.urn]
        self.chunk_cache.Put(fd.chunk, fd)

  def _WriteChunk(self, chunk):
    if chunk.dirty:
      chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk.chunk)
      with FACTORY.Create(
          chunk_name, self.STREAM_TYPE, mode="rw", token=self.token) as fd:
        fd.write(chunk.getvalue())

  def _GetChunkForWriting(self, chunk):
    """Opens a chunk for writing, creating a new one if it doesn't exist yet."""
    try:
      chunk = self.chunk_cache.Get(chunk)
      chunk.dirty = True
      return chunk
    except KeyError:
      pass

    try:
      chunk = self._ReadChunk(chunk)
      chunk.dirty = True
      return chunk
    except KeyError:
      pass

    fd = StringIO.StringIO()
    fd.chunk = chunk
    fd.dirty = True
    self.chunk_cache.Put(chunk, fd)
    return fd

  def _GetChunkForReading(self, chunk):
    """Returns the relevant chunk from the datastore and reads ahead."""
    try:
      return self.chunk_cache.Get(chunk)
    except KeyError:
      pass

    # We don't have this chunk already cached. The most common read
    # access pattern is contiguous reading so since we have to go to
    # the data store already, we read ahead to reduce round trips.

    missing_chunks = []
    for chunk_number in range(chunk, chunk + 10):
      if chunk_number not in self.chunk_cache:
        missing_chunks.append(chunk_number)

    self._ReadChunks(missing_chunks)
    # This should work now - otherwise we just give up.
    try:
      return self.chunk_cache.Get(chunk)
    except KeyError:
      raise ChunkNotFoundError("Cannot open chunk %s" % chunk)

  def _ReadPartial(self, length):
    """Read as much as possible, but not more than length."""
    chunk = self.offset / self.chunksize
    chunk_offset = self.offset % self.chunksize

    available_to_read = min(length, self.chunksize - chunk_offset)

    retries = 0
    while retries < self.NUM_RETRIES:
      fd = self._GetChunkForReading(chunk)
      if fd:
        break
      # Arriving here means we know about blobs that cannot be found in the db.
      # The most likely reason is that they have not been synced yet so we
      # retry a couple of times just in case they come in eventually.
      logging.warning("Chunk not found.")
      time.sleep(1)
      retries += 1

    if retries >= self.NUM_RETRIES:
      raise IOError("Chunk not found for reading.")

    fd.seek(chunk_offset)

    result = fd.read(available_to_read)
    self.offset += len(result)

    return result

  def Read(self, length):
    """Read a block of data from the file."""
    result = ""

    # The total available size in the file
    length = int(length)
    length = min(length, self.size - self.offset)

    while length > 0:
      data = self._ReadPartial(length)
      if not data:
        break

      length -= len(data)
      result += data
    return result

  def _WritePartial(self, data):
    """Writes at most one chunk of data."""

    chunk = self.offset / self.chunksize
    chunk_offset = self.offset % self.chunksize
    data = utils.SmartStr(data)

    available_to_write = min(len(data), self.chunksize - chunk_offset)

    fd = self._GetChunkForWriting(chunk)
    fd.seek(chunk_offset)

    fd.write(data[:available_to_write])
    self.offset += available_to_write

    return data[available_to_write:]

  def Write(self, data):
    self._dirty = True
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")
    while data:
      data = self._WritePartial(data)

    self.size = max(self.size, self.offset)
    self.content_last = rdfvalue.RDFDatetime().Now()

  def Flush(self, sync=True):
    """Sync the chunk cache to storage."""
    if self._dirty:
      self.Set(self.Schema.SIZE(self.size))
      if self.content_last is not None:
        self.Set(self.Schema.CONTENT_LAST, self.content_last)

    # Flushing the cache will write all chunks to the blob store.
    self.chunk_cache.Flush()
    super(AFF4ImageBase, self).Flush(sync=sync)

  def Close(self, sync=True):
    """This method is called to sync our data into storage.

    Args:
      sync: Should flushing be synchronous.
    """
    self.Flush(sync=sync)

  def GetContentAge(self):
    return self.content_last

  def __getstate__(self):
    # We can't pickle the callback.
    if "chunk_cache" in self.__dict__:
      self.chunk_cache.Flush()
      res = self.__dict__.copy()
      del res["chunk_cache"]
      return res
    return self.__dict__

  def __setstate__(self, state):
    self.__dict__ = state
    self.chunk_cache = ChunkCache(self._WriteChunk, 100)


class AFF4Image(AFF4ImageBase):
  """An AFF4 Image containing a versioned stream."""
  STREAM_TYPE = "AFF4MemoryStream"


class AFF4UnversionedImage(AFF4ImageBase):
  """An AFF4 Image containing an unversioned stream."""
  STREAM_TYPE = "AFF4UnversionedMemoryStream"


# Utility functions
class AFF4InitHook(registry.InitHook):

  pre = ["ACLInit", "DataStoreInit"]

  def Run(self):
    """Delayed loading of aff4 plugins to break import cycles."""
    # pylint: disable=unused-variable,global-statement,g-import-not-at-top
    from grr.lib import aff4_objects

    global FACTORY

    FACTORY = Factory()  # pylint: disable=g-bad-name
    # pylint: enable=unused-variable,global-statement,g-import-not-at-top


class AFF4Filter(object):
  """A simple filtering system to be used with Query()."""
  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def __init__(self, *args):
    self.args = args

  @abc.abstractmethod
  def FilterOne(self, fd):
    """Filter a single aff4 object."""

  def Filter(self, subjects):
    """A generator which filters the subjects.

    Args:
       subjects: An iterator of aff4 objects.

    Yields:
       The Objects which pass the filter.
    """
    for subject in subjects:
      if self.FilterOne(subject):
        yield subject


# A global registry of all AFF4 classes
FACTORY = None
ROOT_URN = rdfvalue.RDFURN("aff4:/")


def issubclass(obj, cls):  # pylint: disable=redefined-builtin,g-bad-name
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


def CurrentAuditLog():
  """Get the rdfurn of the current audit log."""
  now_sec = rdfvalue.RDFDatetime().Now().AsSecondsFromEpoch()
  rollover = config_lib.CONFIG["Logging.aff4_audit_log_rollover"]
  # This gives us a filename that only changes every
  # Logging.aff4_audit_log_rollover seconds, but is still a valid timestamp.
  current_log = (now_sec // rollover) * rollover
  return ROOT_URN.Add("audit").Add("logs").Add(str(current_log))
