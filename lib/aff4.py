#!/usr/bin/env python
"""AFF4 interface implementation.

This contains an AFF4 data model implementation.
"""

import __builtin__
import abc
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
from grr.lib.rdfvalues import grr_rdf


# Factor to convert from seconds to microseconds
MICROSECONDS = 1000000


# Age specifications for opening AFF4 objects.
NEWEST_TIME = "NEWEST_TIME"
ALL_TIMES = "ALL_TIMES"

# Just something to write on an index attribute to make it exist.
EMPTY_DATA = "X"

AFF4_PREFIXES = ["aff4:.*", "metadata:.*"]


class Error(Exception):
  pass


class LockError(Error):
  pass


class InstantiationError(Error, IOError):
  pass


class ChunkNotFoundError(IOError):
  pass


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

    # Create a token for system level actions:
    self.root_token = rdfvalue.ACLToken(username="GRRSystem",
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
      for subject, values in data_store.DB.MultiResolveRegex(
          urns, AFF4_PREFIXES, timestamp=self.ParseAgeSpecification(age),
          token=token, limit=None):

        # Ensure the values are sorted.
        values.sort(key=lambda x: x[-1], reverse=True)

        key = self._MakeCacheInvariant(subject, token, age)
        self.cache.Put(key, values)

        yield utils.SmartUnicode(subject), values

  def SetAttributes(self, urn, attributes, to_delete, add_child_index=True,
                    sync=False, token=None):
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
    data_store.DB.MultiSet(urn, attributes, token=token,
                           replace=False, sync=sync, to_delete=to_delete)

    # TODO(user): This can run in the thread pool since its not time
    # critical.
    self._UpdateIndex(urn, attributes, add_child_index, token)

  def _UpdateIndex(self, urn, attributes, add_child_index, token):
    """Updates any indexes we need."""
    index = {}
    for attribute, values in attributes.items():
      if attribute.index:
        for value, _ in values:
          index.setdefault(attribute.index, []).append((attribute, value))

    if index:
      for index_urn, index_data in index.items():
        aff4index = self.Create(index_urn, "AFF4Index", mode="w", token=token)
        for attribute, value in index_data:
          aff4index.Add(urn, attribute, value)
        aff4index.Close()

    if add_child_index:
      self._UpdateChildIndex(urn, token)

  def _UpdateChildIndex(self, urn, token):
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
    """
    try:
      # Create navigation aids by touching intermediate subject names.
      while urn.Path() != "/":
        basename = urn.Basename()
        dirname = rdfvalue.RDFURN(urn.Dirname())

        try:
          self.intermediate_cache.Get(urn.Path())
          return
        except KeyError:
          data_store.DB.MultiSet(dirname, {
              AFF4Object.SchemaCls.LAST: [
                  rdfvalue.RDFDatetime().Now().SerializeToDataStore()],

              # This updates the directory index.
              "index:dir/%s" % utils.SmartStr(basename): [EMPTY_DATA],
              },
                                 token=token, replace=True, sync=False)

          self.intermediate_cache.Put(urn.Path(), 1)

          urn = dirname

    except access_control.UnauthorizedAccess:
      pass

  def _DeleteChildFromIndex(self, urn, token):
    try:
      # Create navigation aids by touching intermediate subject names.
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
    obj = self.Create(urn, aff4_type, mode="rw", ignore_cache=ignore_cache,
                      token=token, age=age, force_new_version=force_new_version)

    # Keep the transaction around - when this object is closed, the transaction
    # will be committed.
    obj.transaction = transaction

    return obj

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
    obj = self.Open(urn, aff4_type=aff4_type, mode="rw", ignore_cache=True,
                    token=token, age=age, follow_symlinks=False)

    # Keep the transaction around - when this object is closed, the transaction
    # will be committed.
    obj.transaction = transaction

    return obj

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
    for predicate, value, ts in data_store.DB.ResolveRegex(
        old_urn, AFF4_PREFIXES,
        timestamp=self.ParseAgeSpecification(age),
        token=token, limit=limit):
      values.setdefault(predicate, []).append((value, ts))

    if values:
      data_store.DB.MultiSet(new_urn, values,
                             token=token, replace=False,
                             sync=sync)

  def Open(self, urn, aff4_type=None, mode="r", ignore_cache=False,
           token=None, local_cache=None, age=NEWEST_TIME, follow_symlinks=True):
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
                         ignore_cache=ignore_cache, force_new_version=False)

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

    # Read the row from the table.
    result = AFF4Object(urn, mode=mode, token=token, local_cache=local_cache,
                        age=age, follow_symlinks=follow_symlinks)

    # Get the correct type.
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
                aff4_type=None, age=NEWEST_TIME):
    """Opens a bunch of urns efficiently."""
    if token is None:
      token = data_store.default_token

    if mode not in ["w", "r", "rw"]:
      raise RuntimeError("Invalid mode %s" % mode)

    symlinks = []
    for urn, values in self.GetAttributes(urns, token=token, age=age):
      try:
        obj = self.Open(urn, mode=mode, ignore_cache=ignore_cache, token=token,
                        local_cache={urn: values}, aff4_type=aff4_type, age=age,
                        follow_symlinks=False)
        target = obj.Get(obj.Schema.SYMLINK_TARGET)
        if target is not None:
          symlinks.append(target)
        else:
          yield obj
      except IOError:
        pass

    if symlinks:
      for obj in self.MultiOpen(symlinks, mode=mode, ignore_cache=ignore_cache,
                                token=token, aff4_type=aff4_type, age=age):
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

    for i in range(0, len(version_list)-1):
      age_range = (version_list[i+1][0], version_list[i][0])
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
    for subject, values in data_store.DB.MultiResolveRegex(
        urns, ["aff4:type"], token=token):
      yield dict(urn=rdfvalue.RDFURN(subject), type=values[0])

  def Create(self, urn, aff4_type, mode="w", token=None, age=NEWEST_TIME,
             ignore_cache=False, force_new_version=True):
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
            ignore_cache=ignore_cache)
        result = existing.Upgrade(aff4_type)
        if force_new_version and existing.Get(result.Schema.TYPE) != aff4_type:
          result.ForceNewVersion()
        return result
      except IOError:
        pass

    # Object does not exist, just make it.
    cls = AFF4Object.classes[str(aff4_type)]
    result = cls(urn, mode=mode, token=token, age=age)
    result.Initialize()
    if force_new_version:
      result.ForceNewVersion()

    return result

  def Delete(self, urn, token=None, limit=None):
    """Drop all the information about this object.

    DANGEROUS! This recursively deletes all objects contained within the
    specified URN.

    Args:
      urn: The object to remove.
      token: The Security Token to use for opening this item.
      limit: The total number of objects to remove. Default is None, which
             means no limit will be enforced.
    Raises:
      RuntimeError: If the urn is too short. This is a safety check to ensure
      the root is not removed.
    """
    if token is None:
      token = data_store.default_token

    urn = rdfvalue.RDFURN(urn)
    if len(urn.Path()) < 1:
      raise RuntimeError("URN %s too short. Please enter a valid URN" % urn)

    # Get all the children (not only immediate ones, but the whole subtree)
    # from the index.
    all_urns = [urn]
    subjects_to_check = [urn]

    # To make the implementation more efficient we first collect urns of all
    # the children objects in the subtree of the urn to be deleted.
    while True:
      found_children = []
      for _, children in FACTORY.MultiListChildren(
          subjects_to_check, token=token):
        found_children.extend(children)
        all_urns.extend(children)

      if not found_children:
        break

      subjects_to_check = found_children

      if limit and len(all_urns) >= limit:
        logging.warning(u"Removed object has more children than the limit: %s",
                        urn)
        all_urns = all_urns[:limit]
        break

    logging.info(u"Found %d objects to remove when removing %s",
                 len(all_urns), urn)

    # Only the index of the parent object should be updated. Everything
    # below the target object (along with indexes) is going to be
    # deleted.
    self._DeleteChildFromIndex(urn, token)

    for urn_to_delete in all_urns:
      logging.debug(u"Removing %s", urn_to_delete)

      try:
        self.intermediate_cache.ExpireObject(urn_to_delete.Path())
      except KeyError:
        pass
      data_store.DB.DeleteSubject(urn_to_delete, token=token, sync=False)

    # Ensure this is removed from the cache as well.
    self.Flush()

    # Do not remove the index or deeper objects may become unnavigable.
    logging.info("Removed %d objects", len(all_urns))

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
    index_prefix = "index:dir/"
    for subject, values in data_store.DB.MultiResolveRegex(
        urns, index_prefix + ".+", token=token,
        timestamp=Factory.ParseAgeSpecification(age),
        limit=limit):

      subject_result = []
      for predicate, _, timestamp in values:
        urn = rdfvalue.RDFURN(subject).Add(predicate[len(index_prefix):])
        urn.age = rdfvalue.RDFDatetime(timestamp)
        subject_result.append(urn)

      yield subject, subject_result

  def Flush(self):
    data_store.DB.Flush()
    self.cache.Flush()
    self.intermediate_cache.Flush()

  def UpdateNotificationRules(self):
    fd = self.Open(rdfvalue.RDFURN("aff4:/config/aff4_rules"), mode="r",
                   token=self.root_token)
    self.notification_rules = [rule for rule in fd.OpenChildren()
                               if isinstance(rule, AFF4NotificationRule)]

  def NotifyWriteObject(self, aff4_object):
    current_time = time.time()
    if (current_time - self.notification_rules_timestamp >
        config_lib.CONFIG["AFF4.notification_rules_cache_age"]):
      self.notification_rules_timestamp = current_time
      self.UpdateNotificationRules()

    for rule in self.notification_rules:
      try:
        rule.OnWriteObject(aff4_object)
      except Exception, e:  # pylint: disable=broad-except
        logging.error("Error while applying the rule: %s", e)


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
    return "<Attribute(%s, %s)>" %(self.name, self.predicate)

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
      raise AttributeError("Invalid attribute")

  def GetRDFValueType(self):
    """Returns this attribute's RDFValue class."""
    result = self.attribute_type
    for field_name in self.field_names:
      # Support the new semantic protobufs.
      if issubclass(result, rdfvalue.RDFProtoStruct):
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

    if isinstance(fd, rdfvalue.RDFValueArray):
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

    LABELS = Attribute("aff4:labels_list", rdfvalue.AFF4ObjectLabelsList,
                       "Any object can have labels applied to it.", "Labels",
                       creates_new_object_version=False, versioned=False)

    LEASED_UNTIL = Attribute("aff4:lease", rdfvalue.RDFDatetime,
                             "The time until which the object is leased by a "
                             "particular caller.", versioned=False,
                             creates_new_object_version=False)

    LAST_OWNER = Attribute("aff4:lease_owner", rdfvalue.RDFString,
                           "The owner of the lease.", versioned=False,
                           creates_new_object_version=False)

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
      """For unknown attributes just return None.

      Often the actual object returned is not the object that is expected. In
      those cases attempting to retrieve a specific named attribute will raise,
      e.g.:

      fd = aff4.FACTORY.Open(urn)
      fd.Get(fd.Schema.SOME_ATTRIBUTE, default_value)

      This simply ensures that the default is chosen.

      Args:
        attr: Some ignored attribute.
      """
      return None

  # Make sure that when someone references the schema, they receive an instance
  # of the class.
  @property
  def Schema(self):   # pylint: disable=g-bad-name
    return self.SchemaCls()

  def __init__(self, urn, mode="r", parent=None, clone=None, token=None,
               local_cache=None, age=NEWEST_TIME, follow_symlinks=True):
    if urn is not None:
      urn = rdfvalue.RDFURN(urn)
    self.urn = urn
    self.mode = mode
    self.parent = parent
    self.token = token
    self.age_policy = age
    self.follow_symlinks = follow_symlinks
    self.lock = utils.PickleableLock()

    # This flag will be set whenever an attribute is changed that has the
    # creates_new_object_version flag set.
    self._new_version = False

    # Mark out attributes to delete when Flushing()
    self._to_delete = set()

    # Cached index object for Label handling.
    self._labels_index = None

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
      if not attribute_name.startswith("index:"):
        logging.debug("Attribute %s not defined, skipping.", attribute_name)
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

      # Write the attributes to the Factory cache.
      FACTORY.SetAttributes(self.urn, to_set, self._to_delete,
                            add_child_index=self.Schema.ADD_CHILD_INDEX,
                            sync=sync, token=self.token)

      # Notify the factory that this object got updated.
      FACTORY.NotifyWriteObject(self)

      # Flush label indexes.
      if self._labels_index is not None:
        self._labels_index.Flush(sync=sync)

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
      raise ValueError("Value for attribute %s must be of type %s()",
                       attribute, attribute.attribute_type.__name__)

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
    if self.locked:
      raise RuntimeError("Cannot upgrade a locked object.")

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
                 follow_symlinks=self.follow_symlinks)
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

  def _GetLabelsIndex(self):
    """Creates and caches labels index object."""
    if self._labels_index is None:
      self._labels_index = FACTORY.Create(
          self.labels_index_urn, "AFF4LabelsIndex", mode="w",
          token=self.token)
    return self._labels_index

  def AddLabels(self, *labels_names, **kwargs):
    """Add labels to the AFF4Object."""
    if not self.token and "owner" not in kwargs:
      raise RuntimeError("Can't set label: No owner specified and "
                         "no access token available.")
    owner = kwargs.get("owner") or self.token.username

    labels_index = self._GetLabelsIndex()
    current_labels = self.Get(self.Schema.LABELS, self.Schema.LABELS())
    for label_name in labels_names:
      label = rdfvalue.AFF4ObjectLabel(name=label_name, owner=owner,
                                       timestamp=rdfvalue.RDFDatetime().Now())
      if current_labels.AddLabel(label):
        labels_index.AddLabel(self.urn, label_name, owner=owner)

    self.Set(current_labels)

  def RemoveLabels(self, *labels_names, **kwargs):
    """Remove specified labels from the AFF4Object."""
    if not self.token and "owner" not in kwargs:
      raise RuntimeError("Can't remove label: No owner specified and "
                         "no access token available.")
    owner = kwargs.get("owner") or self.token.username

    labels_index = self._GetLabelsIndex()
    current_labels = self.Get(self.Schema.LABELS)
    for label_name in labels_names:
      label = rdfvalue.AFF4ObjectLabel(name=label_name, owner=owner)
      current_labels.RemoveLabel(label)

      labels_index.RemoveLabel(self.urn, label_name, owner=owner)

    self.Set(self.Schema.LABELS, current_labels)

  def SetLabels(self, *labels_names, **kwargs):
    self.ClearLabels()
    self.AddLabels(*labels_names, **kwargs)

  def ClearLabels(self):
    self.Set(self.Schema.LABELS, rdfvalue.AFF4ObjectLabelsList())

  def GetLabels(self):
    return self.Get(self.Schema.LABELS, rdfvalue.AFF4ObjectLabelsList()).labels

  def GetLabelsNames(self):
    return self.Get(self.Schema.LABELS, rdfvalue.AFF4ObjectLabelsList()).names


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
    for entry in data_store.DB.ResolveRegex(self.urn, "index:dir/.*",
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
    for predicate, _, timestamp in data_store.DB.ResolveRegex(
        self.urn, index_prefix + ".+", token=self.token,
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
        pathspec.Append(rdfvalue.PathSpec(path=new_path,
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
      return FACTORY.Open(target_urn, mode=mode, age=age, token=token)
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

  def IsPathOverlayed(self, path):   # pylint: disable=unused-argument
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

    HASH = Attribute("aff4:hashobject", rdfvalue.Hash,
                     "Hash object containing all known hash digests for"
                     " the object.")

  def __len__(self):
    return self.size

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
  read = utils.Proxy("Read")
  seek = utils.Proxy("Seek")
  tell = utils.Proxy("Tell")
  close = utils.Proxy("Close")
  write = utils.Proxy("Write")
  flush = utils.Proxy("Flush")


class AFF4MemoryStream(AFF4Stream):
  """A stream which keeps all data in memory."""

  class SchemaCls(AFF4Stream.SchemaCls):
    CONTENT = Attribute("aff4:content", rdfvalue.RDFBytes,
                        "Total content of this file.", default="")

  def Initialize(self):
    """Try to load the data from the store."""
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
    self.size = self.fd.len

  def Tell(self):
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def Flush(self, sync=True):
    if self._dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT(compressed_content))
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4MemoryStream, self).Flush(sync=sync)

  def Close(self, sync=True):
    if self._dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT(compressed_content))
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4MemoryStream, self).Close(sync=sync)

  def GetContentAge(self):
    return self.Get(self.Schema.CONTENT).age


class AFF4ObjectCache(utils.FastStore):
  """A cache which closes its objects when they expire."""

  def KillObject(self, obj):
    obj.Close(sync=True)


class AFF4Image(AFF4Stream):
  """An AFF4 Image is stored in segments.

  We are both an Image here and a volume (since we store the segments inside
  us).
  """

  NUM_RETRIES = 10
  CHUNK_ID_TEMPLATE = "%010X"

  # This is the chunk size of each chunk. The chunksize can not be changed once
  # the object is created.
  chunksize = 64 * 1024

  class SchemaCls(AFF4Stream.SchemaCls):
    _CHUNKSIZE = Attribute("aff4:chunksize", rdfvalue.RDFInteger,
                           "Total size of each chunk.", default=64*1024)

    # Note that we can't use CONTENT.age in place of this, since some types
    # (specifically, AFF4Image) do not have a CONTENT attribute, since they're
    # stored in chunks. Rather than maximising the last updated time over all
    # chunks, we store it and update it as an attribute here.
    CONTENT_LAST = Attribute("metadata:content_last", rdfvalue.RDFDatetime,
                             "The last time any content was written.",
                             creates_new_object_version=False)

  def Initialize(self):
    """Build a cache for our chunks."""
    super(AFF4Image, self).Initialize()

    self.offset = 0
    # A cache for segments - When we get pickled we want to discard them.
    self.chunk_cache = AFF4ObjectCache(100)

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

  def _GetChunkForWriting(self, chunk):
    chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
    try:
      fd = self.chunk_cache.Get(chunk_name)
    except KeyError:
      fd = FACTORY.Create(chunk_name, "AFF4MemoryStream", mode="rw",
                          token=self.token)
      self.chunk_cache.Put(chunk_name, fd)

    return fd

  def _GetChunkForReading(self, chunk):
    """Returns the relevant chunk from the datastore and reads ahead."""

    chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
    try:
      fd = self.chunk_cache.Get(chunk_name)
    except KeyError:
      # The most common read access pattern is contiguous reading. Here we
      # readahead to reduce round trips.
      missing_chunks = []
      for chunk_number in range(chunk, chunk + 10):
        new_chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number)
        try:
          self.chunk_cache.Get(new_chunk_name)
        except KeyError:
          missing_chunks.append(new_chunk_name)

      for child in FACTORY.MultiOpen(
          missing_chunks, mode="rw", token=self.token, age=self.age_policy):
        if isinstance(child, AFF4Stream):
          self.chunk_cache.Put(child.urn, child)

      # This should work now - otherwise we just give up.
      try:
        fd = self.chunk_cache.Get(chunk_name)
      except KeyError:
        raise ChunkNotFoundError("Cannot open chunk %s" % chunk_name)

    return fd

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

    fd.Seek(chunk_offset)

    result = fd.Read(available_to_read)
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
    fd.Seek(chunk_offset)

    fd.Write(data[:available_to_write])
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

    # Flushing the cache will call Close() on all the chunks.
    self.chunk_cache.Flush()
    super(AFF4Image, self).Flush(sync=sync)

  def Close(self, sync=True):
    """This method is called to sync our data into storage.

    Args:
      sync: Should flushing be synchronous.
    """
    self.Flush(sync=sync)

  def GetContentAge(self):
    return self.content_last


class AFF4NotificationRule(AFF4Object):

  def OnWriteObject(self, unused_aff4_object):
    raise NotImplementedError()


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
