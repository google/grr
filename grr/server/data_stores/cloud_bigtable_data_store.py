#!/usr/bin/env python
"""Google Cloud Bigtable data store."""


import datetime
import logging
from multiprocessing.pool import ThreadPool
import threading
import time
import traceback

from grpc.framework.interfaces.face import face
import pytz

from google.cloud import bigtable
from google.cloud.bigtable import row_filters

from grr import config
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import structs
from grr.server import aff4
from grr.server import data_store


class Error(data_store.Error):
  """All errors inherit from here."""


class AccessError(Error):
  """Raised when we are unable to access the BT cell."""
  counter = "grr_cloud_bigtable_access_errors"


class ExistingLock(data_store.DBSubjectLockError):
  """Raised when we don't get the lock."""
  counter = "grr_cloud_bigtable_lock_failures"


class CloudBigTableInit(registry.InitHook):

  def RunOnce(self):
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_access_errors")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_read_retries")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_write_retries")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_delete_retries")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_read_failures")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_write_failures")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_delete_failures")
    stats.STATS.RegisterCounterMetric("grr_cloud_bigtable_lock_failures")


class CloudBigtableLock(data_store.DBSubjectLock):
  """Cloud Bigtable subject locking."""

  def _Acquire(self, lease_time):
    now = int(time.time() * 1e6)
    expires = int((time.time() + lease_time) * 1e6)

    # Only latest value
    latest_value = row_filters.CellsColumnLimitFilter(1)
    # Match any lease time value > now which means someone else holds a lock
    # We can't store these as ints, encode to str.
    current_lease = row_filters.ValueRangeFilter(
        start_value=utils.SmartStr(now), inclusive_start=False)

    # aff4:lease
    family, column = self.store.GetFamilyColumn(self.store.LEASE_ATTRIBUTE)
    col_filter = row_filters.ColumnRangeFilter(
        family, start_column=column, end_column=column)

    # Note filter chains are evaluated in order so there are performance
    # considerations with which filter to apply first
    filter_chain = row_filters.RowFilterChain(
        [col_filter, current_lease, latest_value])
    mutate_row = self.store.table.row(self.subject, filter_=filter_chain)

    # state=False means no lease or it's expired, in this case take the lock.
    mutate_row.set_cell(family, column, utils.SmartStr(expires), state=False)

    # Check in review: I think we want to retry the RPC here? Or should we just
    # raise like we can't get the lock?
    existing_lock = self.store.CallWithRetry(mutate_row.commit, "write")

    if existing_lock:
      raise ExistingLock("Row %s locked." % self.subject)

    # We have the lock
    self.expires = expires
    self.locked = True

  def UpdateLease(self, lease_time):
    new_expires = int((time.time() + lease_time) * 1e6)
    family, column = self.store.GetFamilyColumn(self.store.LEASE_ATTRIBUTE)
    mutate_row = self.store.table.row(self.subject)
    mutate_row.set_cell(family, column, utils.SmartStr(new_expires))
    self.store.CallWithRetry(mutate_row.commit, "write")
    self.expires = new_expires

  def Release(self):
    # If we're still holding a lock, release it.
    if self.locked:
      mutate_row = self.store.table.row(self.subject)
      family, column = self.store.GetFamilyColumn(self.store.LEASE_ATTRIBUTE)
      # Rather than write 0 to release, we just delete the attribute and remove
      # the versions.
      mutate_row.delete_cell(family, column)
      self.store.CallWithRetry(mutate_row.commit, "delete")
      self.expires = None


class CloudBigTableDataStore(data_store.DataStore):
  """GCP CloudBigtable based data storage system.

  Note Cloud Bigtable only supports timestamp precision in milli seconds. All
  other GRR datastores support microseconds.

  Note that currently it isn't safe to use the bigtable garbage collection to
  make data disappear out from under the system, except for the two cases we use
  by default here.  Also, exposing the full power of the bigtable garbage
  collection system via configuration is very complicated. You can have nested
  AND and OR garbage collection rules, see http://goo.gl/L6Oh9i. If we decide to
  use this more extensively in the future we'll provide a sensible default gc
  strategy and tell people to modify using the bigtable client if they want to
  change it later.
  """

  COLUMN_FAMILIES = {
      "aff4": {},
      "metadata": {
          "versions": 1
      },
      "flow": {
          "versions": 1
      },
      "index": {},
      "notify": {},
      "kw_index": {},
      "task": {},
  }

  def __init__(self):
    super(CloudBigTableDataStore, self).__init__()
    self.lock = threading.RLock()
    self.instance = None
    self.table = None
    self._CalculateAttributeStorageTypes()

  # We can deprecate this once there is something included in the library:
  # https://github.com/GoogleCloudPlatform/gcloud-python/issues/2117
  def WaitOnOperation(self, operation, max_tries=4, delay=1, backoff=2):
    tries = 0
    while tries < max_tries:
      if operation.finished():
        return operation
      delay *= backoff**tries
      time.sleep(delay)
      tries += 1

  def GetInstance(self, btclient, instance_id):
    instances, _ = btclient.list_instances()
    for instance in instances:
      if instance.instance_id == instance_id:
        return instance
    return None

  def GetTable(self, instance, table_name):
    for table in instance.list_tables():
      if table.table_id == table_name:
        return table
    return None

  def StartClient(self, project_id=None, instance_id=None):
    # Connection to bigtable is fairly expensive so we open one and re-use it.
    # https://cloud.google.com/bigtable/docs/performance
    self.btclient = bigtable.Client(project=project_id)
    self.instance = self.btclient.instance(instance_id)
    self.table = self.instance.table(config.CONFIG["CloudBigtable.table_name"])

  def Initialize(self, project_id=None, instance_id=None):
    super(CloudBigTableDataStore, self).Initialize()
    project_id = project_id or config.CONFIG["CloudBigtable.project_id"]
    if not project_id:
      raise AccessError(
          "No Google Cloud project ID specified, can't create instance.")

    instance_id = instance_id or config.CONFIG["CloudBigtable.instance_id"]

    self.CreateInstanceAndTable(project_id=project_id, instance_id=instance_id)
    self.StartClient(project_id=project_id, instance_id=instance_id)
    self.pool = ThreadPool(config.CONFIG["CloudBigtable.threadpool_size"])

  def CreateInstanceAndTable(self, project_id=None, instance_id=None):
    # The client must be created with admin=True because it will create a
    # table.
    btclient = bigtable.Client(project=project_id, admin=True)
    tablename = config.CONFIG["CloudBigtable.table_name"]
    instance_name = config.CONFIG["CloudBigtable.instance_name"]

    btinstance = self.GetInstance(btclient, instance_id)
    if not btinstance:
      logging.info("Creating cloud bigtable: %s.%s in %s", instance_id,
                   tablename, project_id)
      btinstance = btclient.instance(
          instance_id,
          display_name=instance_name,
          serve_nodes=config.CONFIG["CloudBigtable.serve_nodes"],
          location=config.CONFIG["CloudBigtable.instance_location"])
      operation = btinstance.create()
      self.WaitOnOperation(operation)

    table = self.GetTable(btinstance, tablename)
    if not table:
      table = btinstance.table(tablename)
      table.create()
      for column, gc_rules in self.COLUMN_FAMILIES.iteritems():
        gc_rule = None
        if gc_rules:
          age = gc_rules.get("age", None)
          if age:
            gc_rule = bigtable.column_family.MaxAgeGCRule(age)

          version_max = gc_rules.get("versions", None)
          if version_max:
            gc_rule = bigtable.column_family.MaxVersionsGCRule(version_max)

        cf = table.column_family(column, gc_rule=gc_rule)
        cf.create()

    return btinstance

  def DeleteSubject(self, subject, sync=False, token=None):
    self.DeleteSubjects([subject], sync=sync, token=token)

  def DeleteSubjects(self, subjects, sync=False, token=None):
    # Currently there is no multi-row mutation support, but it exists in the
    # RPC API.
    # https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2411
    # So we delete all subjects at once using a threadpool
    pool_args = []
    for subject in subjects:
      row = self.table.row(utils.SmartStr(subject))
      row.delete()
      pool_args.append(((row.commit, "delete"), {}))

    if sync:
      self.pool.map(self._WrapCallWithRetry, pool_args)
    else:
      self.pool.map_async(self._WrapCallWithRetry, pool_args)

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types.

    Since BT only stores bytes, we need to record the basic types that are
    required to be stored for each column.
    """
    self._attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self._attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def Encode(self, attribute, value):
    """Encode the value for the attribute."""
    required_type = self._attribute_types.get(attribute, "bytes")
    if required_type in ("integer", "unsigned_integer"):
      return structs.VarintEncode(int(value))
    elif hasattr(value, "SerializeToString"):
      return value.SerializeToString()
    else:
      # Types "string" and "bytes" are stored as strings here.
      return utils.SmartStr(value)

  def Decode(self, attribute, value):
    """Decode the value to the required type."""
    required_type = self._attribute_types.get(attribute, "bytes")
    if required_type in ("integer", "unsigned_integer"):
      return structs.VarintReader(value, 0)[0]
    elif required_type == "string":
      return utils.SmartUnicode(value)
    else:
      return value

  def DBSubjectLock(self, subject, lease_time=None, token=None):
    return CloudBigtableLock(self, subject, lease_time=lease_time, token=token)

  def DatetimeToMicroseconds(self, datetime_utc):
    # How much do I hate datetime? let me count the ways.
    if datetime_utc.tzinfo != pytz.utc:
      raise ValueError(
          "DatetimeToMicroseconds can only safely convert UTC datetimes")
    epoch = datetime.datetime(1970, 1, 1, 0, 0, tzinfo=pytz.utc)  # pylint: disable=g-tzinfo-datetime
    diff = datetime_utc - epoch
    return int(diff.total_seconds() * 1e6)

  def DatetimeFromMicroseconds(self, time_usec):
    seconds = float(time_usec) / 1000000
    dt = datetime.datetime.utcfromtimestamp(seconds)
    return dt.replace(tzinfo=pytz.utc)  # pylint: disable=g-tzinfo-replace

  def GetFamilyColumn(self, attribute):
    return utils.SmartStr(attribute).split(":", 1)

  def _DeleteAllTimeStamps(self, row, attribute_list):
    """Add delete mutations to row, but don't commit."""
    delete_dict = {}
    # Group column families together so we can use delete_cells
    for attribute in attribute_list:
      family, column = self.GetFamilyColumn(attribute)
      delete_dict.setdefault(family, []).append(column)
    for family, column in delete_dict.iteritems():
      row.delete_cells(family, column)

  def Set(self,
          subject,
          attribute,
          value,
          timestamp=None,
          token=None,
          replace=True,
          sync=True):

    self.MultiSet(
        subject, {attribute: [value]},
        timestamp,
        token=token,
        replace=replace,
        sync=sync)

  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               sync=True,
               to_delete=None,
               token=None):
    row = self.table.row(utils.SmartStr(subject))
    if to_delete:
      self._DeleteAllTimeStamps(row, to_delete)

    for attribute, value_list in values.items():
      # Attributes must be strings
      family, column = self.GetFamilyColumn(attribute)

      if replace:
        row.delete_cell(family, column)

      for value in value_list:
        element_timestamp = timestamp
        if isinstance(value, tuple):
          try:
            value, element_timestamp = value
          except (TypeError, ValueError):
            pass

        if element_timestamp is None:
          datetime_ts = datetime.datetime.utcnow()
        else:
          datetime_ts = self.DatetimeFromMicroseconds(element_timestamp)

        # Value parameter here is bytes, so we need to encode unicode to a byte
        # string:
        # https://googlecloudplatform.github.io/google-cloud-python/latest/bigtable/row.html#google.cloud.bigtable.row.DirectRow.set_cell
        value = self.Encode(attribute, value)
        row.set_cell(family, column, value, timestamp=datetime_ts)

    if sync:
      self.CallWithRetry(row.commit, "write")
    else:
      self.pool.map_async(self._WrapCallWithRetry, [((row.commit, "write"),
                                                     {})])

  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=True,
                       token=None):
    self.MultiDeleteAttributes(
        [subject], attributes, start=start, end=end, sync=sync, token=token)

  def MultiDeleteAttributes(self,
                            subjects,
                            attributes,
                            start=None,
                            end=None,
                            sync=True,
                            token=None):

    subjects = [utils.SmartStr(subject) for subject in subjects]

    if isinstance(attributes, basestring):
      raise ValueError(
          "String passed to DeleteAttributes (non string iterable expected).")

    attributes = [utils.SmartStr(x) for x in attributes]

    for subject in subjects:
      row = self.table.row(subject)
      for attribute in attributes:
        if start is None and end is None:
          self._DeleteAllTimeStamps(row, [attribute])
        else:
          family, column = self.GetFamilyColumn(attribute)
          row.delete_cell(
              family,
              column,
              time_range=self._TimestampRangeFromTuple((start, end)))

      if sync:
        self.CallWithRetry(row.commit, "delete")
      else:
        self.pool.map_async(self._WrapCallWithRetry, [((row.commit, "delete"),
                                                       {})])

  def _TimestampRangeFromTuple(self, ts_tuple):
    start, end = ts_tuple
    if start is not None:
      if start == 0:
        start = None
      else:
        # Convert RDFDatetime to usec
        start = float(start)
        # Bigtable can only handle ms precision:
        # https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2626
        # If we give it a filter with usec values it raises RPC error with
        # "Timestamp granularity mismatch".  Truncate to ms here.
        start -= start % 1000
        start = self.DatetimeFromMicroseconds(start)

    if end is not None:
      # Convert RDFDatetime to usec
      end = float(end)
      # Some searches use 2**64 signed int to signal "no upper limit", there's a
      # better way to do that with the API using None.
      if end >= (2**64) / 2:
        end = None
      else:
        # Truncate to ms
        end -= end % 1000
        # GRR expects inclusive timestamps for upper and lower. TimestampRange
        # is exclusive on the end. So we add 1ms to the upper bound, which is
        # the next smallest timestamp bigtable will accept.
        # https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2608
        end += 1000
        end = self.DatetimeFromMicroseconds(end)
    return row_filters.TimestampRange(start=start, end=end)

  def _TimestampToFilter(self, timestamp):
    if timestamp == data_store.DataStore.ALL_TIMESTAMPS:
      return None

    if timestamp is None or timestamp == data_store.DataStore.NEWEST_TIMESTAMP:
      # Latest value only
      return row_filters.CellsColumnLimitFilter(1)

    if isinstance(timestamp, tuple):
      return row_filters.TimestampRangeFilter(
          self._TimestampRangeFromTuple(timestamp))

    raise data_store.Error("Invalid timestamp specification: %s." % timestamp)

  def CallWithRetry(self, callback, mode, *args, **kwargs):
    """Make the bigtable RPC with retries.

    Args:
      callback: a function to call, typically a bigtable row mutation.commit
      mode: A string to indicate what kind of db operation this is "read",
        "write", "delete".
      *args: args to pass to the callback
      **kwargs: keyword args to pass to the callback

    Returns:
      Callback result.

    Raises:
      AccessError: if we hit our RPC retry limit, or the RPC error isn't
      retryable.
      ValueError: if you pass an unknown operation in mode.
    """
    if mode not in set(["read", "write", "delete"]):
      raise ValueError("Mode must be 'read', 'write', 'delete'")

    retry_count = 0
    sleep_interval = config.CONFIG["CloudBigtable.retry_interval"]
    while retry_count < config.CONFIG["CloudBigtable.retry_max_attempts"]:

      try:
        response = callback(*args, **kwargs)
        return response
      except (face.ExpirationError, face.AbortionError) as e:
        last_error = e
        last_traceback = traceback.format_exc()
        print "Retrying %s" % last_traceback

      time.sleep(sleep_interval.seconds)
      logging.info("Retrying callback: %s", callback)
      retry_count += 1
      stats.STATS.IncrementCounter("grr_cloud_bigtable_%s_retries" % mode)
      sleep_interval *= config.CONFIG["CloudBigtable.retry_multiplier"]

    stats.STATS.IncrementCounter("grr_cloud_bigtable_%s_failures" % mode)
    logging.error("Gave up on %s %s after %s retries. %s", mode, callback,
                  retry_count, last_traceback)
    raise AccessError(
        "Giving up on %s callback:%s after %s retries. Last error: %s." %
        (mode, callback, retry_count, last_error))

  def _WrapCallWithRetry(self, argstuple):
    """Workaround not being able to pass kwargs to threadpool callback."""
    callargs, kwargs = argstuple
    return self.CallWithRetry(*callargs, **kwargs)

  def _SortResultsByAttrTimestampValue(self, result_list):
    """Sort order: attribute ASC, timestamp DESC, value ASC."""
    return sorted(result_list, key=lambda (a, val, ts): (a, -ts, val))

  def _GetSubjectResults(self, result, limit):
    subject_results = []
    for attribute, cells in result.to_dict().iteritems():
      for cell in cells:
        subject_results.append((attribute, self.Decode(attribute, cell.value),
                                self.DatetimeToMicroseconds(cell.timestamp)))
        limit -= 1
        if limit <= 0:
          return subject_results, limit
    return subject_results, limit

  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None,
                         token=None):
    """Get results from multiple rows matching multiple attributes.

    We could implement this using read_rows, but it is a table scan. Our current
    data model makes that slow because it is a directory hierarchy that includes
    entries for subdirectories interleaved. So if you want all the results for a
    directory you need to skip those in the scan.

    Instead we make an RPC for each subject all at once using a threadpool. We
    pay more in RPC overhead but we get to do it concurrently.

    Args:
      subjects: A list of subjects.
      attribute_prefix: The attribute prefix.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

      limit: The total number of result values to return.
      token: An ACL token.

    Yields:
       A list of tuples:
       (subject, [(attribute, value string, timestamp)])

       that can be simply converted to a dict.

       Values with the same attribute (happens when timestamp is not
       NEWEST_TIMESTAMP, but ALL_TIMESTAMPS or time range) are guaranteed
       to be ordered in the decreasing timestamp order.

    Raises:
      AccessError: if anything goes wrong.
      ValueError: if we get a string instead of a list of subjects.
    """
    if isinstance(subjects, basestring):
      raise ValueError("Expected list of subjects, got string: %s" % subjects)

    if isinstance(attribute_prefix, basestring):
      attribute_prefix_list = [utils.SmartStr(attribute_prefix)]
    else:
      attribute_prefix_list = [utils.SmartStr(x) for x in attribute_prefix]

    timestamp_filter = self._TimestampToFilter(timestamp)
    filter_union = []

    for attribute_prefix in attribute_prefix_list:
      family, column = self.GetFamilyColumn(attribute_prefix)

      family_filter = row_filters.FamilyNameRegexFilter(family)
      row_filter_list = [family_filter]

      if column:
        # Make it an actual regex
        column += ".*"
        col_filter = row_filters.ColumnQualifierRegexFilter(column)
        row_filter_list.append(col_filter)

      if timestamp_filter:
        row_filter_list.append(timestamp_filter)

      if len(row_filter_list) > 1:
        row_filter = row_filters.RowFilterChain(filters=row_filter_list)
      else:
        row_filter = row_filter_list[0]

      filter_union.append(row_filter)

    # More than one set of prefixes, use a union, otherwise just use the
    # existing filter chain.
    if len(filter_union) > 1:
      attribute_filter = row_filters.RowFilterUnion(filters=filter_union)
    else:
      attribute_filter = filter_union[0]

    # Apply those filters to each subject as a separate RPC using a threadpool
    pool_args = []
    original_subject_map = {}
    for subject in subjects:
      # List of *args, **kwargs to pass to the RPC caller
      pool_args.append(((self.table.read_row, "read", utils.SmartStr(subject)),
                        {
                            "filter_": attribute_filter
                        }))

      # We're expected to return subjects as their original type, which can be
      # URN, unicode, or string. Keep a mapping in this dict.
      original_subject_map[utils.SmartStr(subject)] = subject

    max_results = limit or 2**64
    for result in self.pool.imap_unordered(self._WrapCallWithRetry, pool_args):
      if max_results <= 0:
        break
      if result:
        subject_results, max_results = self._GetSubjectResults(
            result, max_results)
        yield original_subject_map[
            result.row_key], self._SortResultsByAttrTimestampValue(
                subject_results)

  @utils.Synchronized
  def Flush(self):
    """Wait for threadpool jobs to finish, then make a new pool."""
    self.pool.close()
    self.pool.join()
    self.pool = ThreadPool(config.CONFIG["CloudBigtable.threadpool_size"])

  def Resolve(self, subject, attribute, token=None):
    """Retrieve the latest value set for a subject's attribute.

    Args:
      subject: The subject URN.
      attribute: The attribute.
      token: The security token used in this call.

    Returns:
      A (string, timestamp in microseconds) stored in the bigtable
      cell, or (None, 0).

    Raises:
      AccessError: if anything goes wrong.
    """
    subject = utils.SmartStr(subject)

    attribute = utils.SmartStr(attribute)
    family, column = self.GetFamilyColumn(attribute)

    col_filter = row_filters.ColumnRangeFilter(
        family, start_column=column, end_column=column)

    # Most recent
    latest_filter = row_filters.CellsColumnLimitFilter(1)

    row_filter = row_filters.RowFilterChain(filters=[col_filter, latest_filter])
    row_data = self.table.read_row(subject, filter_=row_filter)

    if row_data:
      for cell in row_data.cells[family][column]:
        return self.Decode(
            attribute, cell.value), self.DatetimeToMicroseconds(cell.timestamp)

    return None, 0

  def ResolveMulti(self,
                   subject,
                   attributes,
                   timestamp=None,
                   limit=None,
                   token=None):
    """Resolve multiple attributes for a subject.

    Results will be returned in arbitrary order (i.e. not ordered by attribute
    or timestamp).

    Args:
      subject: The subject to resolve.
      attributes: The attribute string or list of strings to match. Note this is
          an exact match, not a regex.
      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).
      limit: The maximum total number of results we return.
      token: The security token used in this call.

    Yields:
       A unordered list of (attribute, value string, timestamp).

    Raises:
      AccessError: if anything goes wrong.
    """
    subject = utils.SmartStr(subject)

    if isinstance(attributes, basestring):
      attributes = [utils.SmartStr(attributes)]
    else:
      attributes = [utils.SmartStr(x) for x in attributes]

    filter_union = []
    for attribute in attributes:
      family, column = self.GetFamilyColumn(attribute)
      col_filter = row_filters.ColumnRangeFilter(
          family, start_column=column, end_column=column)
      filter_union.append(col_filter)

    # More than one attribute, use a union, otherwise just use the
    # existing filter.
    if len(filter_union) > 1:
      filter_union = row_filters.RowFilterUnion(filters=filter_union)
    else:
      filter_union = filter_union[0]

    # Essentially timestamp AND (attr1 OR attr2)
    timestamp_filter = self._TimestampToFilter(timestamp)
    if timestamp_filter:
      row_filter = row_filters.RowFilterChain(
          filters=[filter_union, timestamp_filter])
    else:
      row_filter = filter_union

    row_data = self.CallWithRetry(
        self.table.read_row, "read", subject, filter_=row_filter)

    if row_data:
      max_results = limit or 2**64
      for column, cells in row_data.cells[family].iteritems():
        attribute = ":".join((family, column))
        for cell in cells:
          if max_results <= 0:
            raise StopIteration
          max_results -= 1
          yield attribute, self.Decode(
              attribute,
              cell.value), self.DatetimeToMicroseconds(cell.timestamp)

  def _GetAttributeFilterUnion(self, attributes, timestamp_filter=None):
    filters = []
    for attribute_prefix in attributes:
      family, column = self.GetFamilyColumn(attribute_prefix)

      family_filter = row_filters.FamilyNameRegexFilter(family)
      row_filter_list = [family_filter]

      if column:
        col_filter = row_filters.ColumnQualifierRegexFilter(column)
        row_filter_list.append(col_filter)

      if timestamp_filter:
        row_filter_list.append(timestamp_filter)

      if len(row_filter_list) > 1:
        row_filter = row_filters.RowFilterChain(filters=row_filter_list)
      else:
        row_filter = row_filter_list[0]

      filters.append(row_filter)

    # More than one attribute, use a union, otherwise just use the
    # existing filter.
    if len(filters) > 1:
      filters = row_filters.RowFilterUnion(filters=filters)
    else:
      filters = filters[0]

    return filters

  def _ReOrderRowResults(self, row_data):
    subject_results = {}
    for family, column_dict in row_data.cells.iteritems():
      for column, cells in column_dict.iteritems():
        attribute = ":".join((family, column))
        subject_results[attribute] = []
        for cell in cells:
          subject_results[attribute].append(
              (self.DatetimeToMicroseconds(cell.timestamp), self.Decode(
                  attribute, cell.value)))

          subject_results[attribute] = sorted(
              subject_results[attribute], key=lambda x: -x[0])
        if len(subject_results[attribute]) == 1:
          subject_results[attribute] = subject_results[attribute][0]
    return subject_results

  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None,
                     token=None,
                     relaxed_order=False):
    subject_prefix = self._CleanSubjectPrefix(subject_prefix)
    after_urn = self._CleanAfterURN(after_urn, subject_prefix)
    # Turn subject prefix into an actual regex
    subject_prefix += ".*"

    subject_filter = row_filters.RowKeyRegexFilter(
        utils.SmartStr(subject_prefix))
    latest_value = row_filters.CellsColumnLimitFilter(1)
    attribute_filters = self._GetAttributeFilterUnion(attributes)
    # Subject AND (attr1 OR attr2) AND latest_value
    query_filter = row_filters.RowFilterChain(
        [subject_filter, attribute_filters, latest_value])

    # The API results include the start row, we want to exclude it, append a
    # null to do so.
    if after_urn is not None:
      after_urn += "\x00"

    rows_data = self.CallWithRetry(
        self.table.read_rows,
        "read",
        start_key=after_urn,
        limit=max_records,
        filter_=query_filter)

    # Ideally we should be able to stream and yield, but it seems we can't:
    # https://github.com/GoogleCloudPlatform/google-cloud-python/issues/1812
    self.CallWithRetry(rows_data.consume_all, "read")

    results = []
    if rows_data.rows:
      for subject, row_data in rows_data.rows.iteritems():
        subject_results = self._ReOrderRowResults(row_data)
        results.append((subject, subject_results))
    return sorted(results, key=lambda x: x[0])
