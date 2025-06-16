"""Spanner-related helpers and other utilities."""

import contextlib
import datetime
import decimal
import pytz
import re
import time

from typing import Any
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar

from concurrent import futures

from google.cloud import pubsub_v1
from google.cloud import spanner_v1 as spanner_lib

from google.cloud.spanner import KeyRange, KeySet
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin
from google.cloud.spanner_v1 import Mutation, param_types

from google.rpc.code_pb2 import OK

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import iterator

from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2

Row = Tuple[Any, ...]
Cursor = Iterator[Row]

_T = TypeVar("_T")

class RequestQueue:
  """
  This stores the callback internally, and will continue to deliver messages to
  the callback as long as it is referenced in python code and Stop is not
  called.
  """

  def __init__(
      self,
      subscriber,
      subscription_path: str,
      callback,  # : Callable
      receiver_max_keepalive_seconds: int,
      receiver_max_active_callbacks: int,
      receiver_max_messages_per_callback: int,
  ):

    # An optional executor to use. If not specified, a default one with maximum 10
    # threads will be created.
    executor = futures.ThreadPoolExecutor(max_workers=receiver_max_active_callbacks)
    # A thread pool-based scheduler. It must not be shared across SubscriberClients.
    scheduler = pubsub_v1.subscriber.scheduler.ThreadScheduler(executor)

    #flow_control = pubsub_v1.types.FlowControl(max_messages=receiver_max_messages_per_callback)

    self.streaming_pull_future = subscriber.subscribe(
      subscription_path, callback=callback, scheduler=scheduler
      #subscription_path, callback=callback, scheduler=scheduler, flow_control=flow_control
    )

  def Stop(self):
    if self.streaming_pull_future:
      try:
        self.streaming_pull_future.cancel()
      except asyncio.CancelledError:
        pass # Expected when cancelling
      except Exception as e:
        print(f"Warning: Exception while cancelling future: {e}")

      time.sleep(0.1) # Give a short buffer for threads to clean up

class Database:
  """A wrapper around the PySpanner class.

  The wrapper is supposed to streamline the usage of Spanner database through
  an abstraction that is much harder to misuse. The wrapper will run retryable
  queries through a transaction runner handling all brittle logic for the user.
  """

  _PYSPANNER_PARAM_REGEX = re.compile(r"@p\d+") 

  def __init__(self, pyspanner: spanner_lib.database, project_id: str,
               msg_handler_top_id: str, msg_handler_sub_id: str,
               flow_processing_top_id: str, flow_processing_sub_id: str) -> None:
    super().__init__()
    self._pyspanner = pyspanner
    self.project_id = project_id
    self.publisher = pubsub_v1.PublisherClient()
    self.subscriber = pubsub_v1.SubscriberClient()
    self.flow_processing_sub_path = self.subscriber.subscription_path(project_id, flow_processing_sub_id)
    self.flow_processing_top_path = self.publisher.topic_path(project_id, flow_processing_top_id)
    self.message_handler_sub_path = self.subscriber.subscription_path(project_id, msg_handler_sub_id)
    self.message_handler_top_path = self.publisher.topic_path(project_id, msg_handler_top_id)

  def Now(self) -> rdfvalue.RDFDatetime:
    """Retrieves current time as reported by the database."""
    with self._pyspanner.snapshot() as snapshot:
      timestamp = None
      query = "SELECT CURRENT_TIMESTAMP() AS now"
      results = snapshot.execute_sql(query)
      for row in results:
        timestamp = row[0]
      return rdfvalue.RDFDatetime.FromDatetime(timestamp)

  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    """Returns minimal timestamp allowed by the DB."""
    return rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
  
  def _parametrize(self, query: str, names: Iterable[str]) -> str:
    match = self._PYSPANNER_PARAM_REGEX.search(query)
    if match is not None:
      raise ValueError(f"Query contains illegal sequence: {match.group(0)}")

    kwargs = {}
    for name in names:
      kwargs[name] = f"@{name}"

    return query.format(**kwargs)

  def _get_param_type(self, value):
    """
    Infers the Google Cloud Spanner type from a Python value.

    Args:
        value: The Python value whose Spanner type is to be inferred.

    Returns:
        A google.cloud.spanner_v1.types.Type object, or None if the type
        cannot be reliably inferred (e.g., for a standalone None value or
        an empty list).
    """
    if value is None:
        # Cannot determine a specific Spanner type from a None value alone.
        # This indicates that the type is ambiguous without further schema context.
        return None

    py_type = type(value)

    if py_type is int:
        return param_types.INT64
    elif py_type is float:
        return param_types.FLOAT64
    elif py_type is str:
        return param_types.STRING
    elif py_type is bool:
        return param_types.BOOL
    elif py_type is bytes:
        return param_types.BYTES
    elif py_type is datetime.date:
        return param_types.DATE
    elif py_type is datetime.datetime:
        # Note: Spanner TIMESTAMPs are stored in UTC. Ensure datetime objects
        # are timezone-aware (UTC) when writing data. This function only maps the type.
        return param_types.TIMESTAMP
    elif py_type is decimal.Decimal:
        return param_types.NUMERIC
    elif py_type is list:
        if len(value) > 0:
          return param_types.Array(self._get_param_type(value[0]))
        else:
          raise TypeError(f"Empty value for Python type: {py_type.__name__} for Spanner type conversion.")
    else:
        # Potentially raise an error for unsupported types or return None
        # For a generic solution, raising an error for unknown types is often safer.
        raise TypeError(f"Unsupported Python type: {py_type.__name__} for Spanner type conversion.")

  def Transact(
      self,
      func: Callable[["Transaction"], _T],
      txn_tag: Optional[str] = None,
  ) -> List[Any]:

    """Execute the given callback function in a Spanner transaction.

    Args:
      func: A transaction function to execute.
      txn_tag: Transaction tag to apply.

    Returns:
      The result of the transaction function executed.
    """
    return self._pyspanner.run_in_transaction(func)

  def Mutate(
      self, func: Callable[["Mutation"], None], txn_tag: Optional[str] = None
  ) -> None:
    """Execute the given callback function in a Spanner mutation.

    Args:
      func: A mutation function to execute.
      txn_tag: Optional[str] = None,
    """

    self.Transact(func, txn_tag=txn_tag)

  def Query(self, query: str, txn_tag: Optional[str] = None) -> Cursor:
    """Queries Spanner database using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      A cursor over the query results.
    """
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.execute_sql(query)

    return results

  def QuerySingle(self, query: str, txn_tag: Optional[str] = None) -> Row:
    """Queries PySpanner for a single row using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      A single row matching the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
    """
    return self.Query(query, txn_tag=txn_tag).one()

  def ParamQuery(
      self, query: str, params: Mapping[str, Any],
      param_type: Optional[dict] = {}, txn_tag: Optional[str] = None
  ) -> Cursor:
    """Queries PySpanner database using the given query string with params.

    The query string should specify parameters with the standard Python format
    placeholder syntax [1]. Note that parameters inside string literals in the
    query itself have to be escaped.

    Also, the query literal is not allowed to contain any '@p{idx}' strings
    inside as that would lead to an incorrect behaviour when evaluating the
    query. To prevent mistakes the function will raise an exception in such
    cases.

    [1]: https://docs.python.org/3/library/stdtypes.html#str.format

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A cursor over the query results.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    names, values = collection.Unzip(params.items())
    query =  self._parametrize(query, names)

    for key, value in params.items():
      if key not in param_type:
        try:
          param_type[key] = self._get_param_type(value)
        except TypeError as e:
          print(f"Warning for key '{key}': {e}. Setting type to None.")
          param_type[key] = None # Or re-raise, or handle differently

    print("query: {}".format(query))
    print("params: {}".format(params))
    print("param_type: {}".format(param_type))

    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.execute_sql(
            query,
            params=params,
            param_types=param_type,
        )

    return results

  def ParamQuerySingle(
      self, query: str, params: Mapping[str, Any],
      param_type: Optional[dict] = {}, txn_tag: Optional[str] = None
  ) -> Row:
    """Queries the database for a single row using with a query with params.

    See documentation for `ParamQuery` to learn more about the syntax of query
    parameters and other caveats.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A single result of running the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    return self.ParamQuery(query, params, param_type=param_type, txn_tag=txn_tag).one()

  def ParamExecute(
      self, query: str, params: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Executes the given query with parameters against a Spanner database.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    names, values = collection.Unzip(params.items())
    query =  self._parametrize(query, names)

    param_type = {}
    for key, value in params.items():
      try:
        param_type[key] = self._get_param_type(value)
      except TypeError as e:
        print(f"Warning for key '{key}': {e}. Setting type to None.")
        param_type[key] = None # Or re-raise, or handle differently

    print("query: {}".format(query))
    print("params: {}".format(params))
    print("param_type: {}".format(param_type))

    def param_execute(transaction):
        row_ct = transaction.execute_update(
            query,
            params=params,
            param_types=param_type,
        )

        print("{} record(s) updated.".format(row_ct))
    self._pyspanner.run_in_transaction(param_execute)

  def ExecutePartitioned(
      self, query: str, txn_tag: Optional[str] = None
  ) -> None:
    """Executes the given query against a Spanner database.

    This is a more efficient variant of the `Execute` method, but it does not
    guarantee atomicity. See the official documentation on partitioned updates
    for more information [1].

    [1]: go/spanner-partitioned-dml

    Args:
      query: An SQL query string to execute.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    query_options = None
    if txn_tag is not None:
      query_options = spanner_lib.QueryOptions()
      query_options.SetTag(txn_tag)

    return self._pyspanner.execute_partitioned_dml(query)

  def Insert(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert a row into the given table.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch() as batch:
      batch.insert(
        table=table,
        columns=columns,
        values=[values]
      )

  def Update(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Updates a row in the given table.

    Args:
      table: A table in which the row is to be updated.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch() as batch:
      batch.update(
        table=table,
        columns=columns,
        values=[values]
      )

  def InsertOrUpdate(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert or update a row into the given table within the transaction.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch() as batch:
      batch.insert_or_update(
        table=table,
        columns=columns,
        values=[values]
      )

  def Delete(
      self, table: str, key: Sequence[Any], txn_tag: Optional[str] = None
  ) -> None:
    """Deletes a specified row from the given table.

    Args:
      table: A table from which the row is to be deleted.
      key: A sequence of values denoting the key of the row to delete.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    keyset = KeySet(all_=True)
    if key:
      keyset = KeySet(keys=[key])
    with self._pyspanner.batch() as batch:
      batch.delete(table, keyset)

  def DeleteWithPrefix(self, table: str, key_prefix: Sequence[Any]) -> None:
    """Deletes a range of rows with common key prefix from the given table.

    Args:
      table: A table from which rows are to be deleted.
      key: A sequence of value denoting the prefix of the key of rows to delete.

    Returns:
      Nothing.
    """
    range = KeyRange(start_closed=key_prefix, end_closed=key_prefix)
    keyset = KeySet(ranges=[range])

    with self._pyspanner.batch() as batch:
      batch.delete(table, keyset)

  def Read(
      self,
      table: str,
      key: Sequence[Any],
      cols: Sequence[str],
  ) -> Mapping[str, Any]:
    """Read a single row with the given key from the specified table.

    Args:
      table: A name of the table to read from.
      key: A key of the row to read.
      cols: Columns of the row to read.

    Returns:
      A mapping from columns to values of the read row.
    """
    keyset = KeySet(keys=[key])
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.read(
            table=table,
            columns=cols,
            keyset=keyset
        )
    return results.one()

  def ReadSet(
      self,
      table: str,
      rows: KeySet,
      cols: Sequence[str],
  ) -> Iterator[Mapping[str, Any]]:
    """Read a set of rows from the specified table.

    Args:
      table: A name of the table to read from.
      rows: A set of keys specifying which rows to read.
      cols: Columns of the row to read.

    Returns:
      Mappings from columns to values of the rows read.
    """
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.read(
            table=table,
            columns=cols,
            keyset=rows
        )
    
    return results

  def PublishMessageHandlerRequests(self, requests: [str]) -> None:
    self.PublishRequests(requests, self.message_handler_top_path)

  def PublishFlowProcessingRequests(self, requests: [str]) -> None:
    self.PublishRequests(requests, self.flow_processing_top_path)

  def ReadMessageHandlerRequests(self, min_req: Optional[int] = None):
    return self.ReadRequests(self.message_handler_sub_path, min_req)

  def ReadFlowProcessingRequests(self, min_req: Optional[int] = None):
    return self.ReadRequests(self.flow_processing_sub_path, min_req)

  def AckMessageHandlerRequests(self, ack_ids: [str]) -> None:
    self.AckRequests(ack_ids, self.message_handler_sub_path)

  def AckFlowProcessingRequests(self, ack_ids: [str]) -> None:
    self.AckRequests(ack_ids, self.flow_processing_sub_path)
  
  def DeleteAllMessageHandlerRequests(self) -> None:
    self.DeleteAllRequests(self.message_handler_sub_path)

  def DeleteAllFlowProcessingRequests(self) -> None:
    self.DeleteAllRequests(self.flow_processing_sub_path)
  
  def LeaseMessageHandlerRequests(self, ack_ids: [str], ack_deadline: int) -> None:
    self.subscriber.modify_ack_deadline(
      request={
        "subscription": self.message_handler_sub_path,
        "ack_ids": ack_ids,
        "ack_deadline_seconds": ack_deadline,
      }
    )

  def LeaseFlowProcessingRequests(self, ack_ids: [str], ack_deadline: int) -> None:
    self.subscriber.modify_ack_deadline(
      request={
        "subscription": self.flow_processing_sub_path,
        "ack_ids": ack_ids,
        "ack_deadline_seconds": ack_deadline,
      }
    )

  def PublishRequests(self, requests: [str], top_path: str) -> None:
    for req in requests:
      self.publisher.publish(top_path, req)

  def AckRequests(self, ack_ids: [str], sub_path: str) -> None:
    self.subscriber.acknowledge(
      request={"subscription": sub_path, "ack_ids": ack_ids}
    )

  def DeleteAllRequests(self, sub_path: str) -> None:
    client = pubsub_v1.SubscriberClient()
    # Initialize request argument(s)
    request = {
        "subscription": sub_path,
        "time": datetime.datetime.now(pytz.utc) + datetime.timedelta(days=30) 
    }
    # Make the request
    response = client.seek(request=request)

  def ReadRequests(self, sub_path: str, min_req: Optional[int] = None):
    # Make the request

    start_time = time.time()
    results = {}
    want_more = True
    while want_more or (time.time() - start_time < 2):
      time.sleep(0.1)

      response = self.subscriber.pull(
        request = {
          "subscription": sub_path,
          "max_messages": 10000,
        },
      )
      for resp in response.received_messages:
        results.update({resp.message.message_id: {
                          "payload": resp.message.data,
                          "msg_id": resp.message.message_id,
                          "ack_id": resp.ack_id,
                          "publish_time": resp.message.publish_time}
                        })
      if min_req and len(results) >= min_req:
        want_more = False

    return results.values()

  def NewRequestQueue(
      self,
      queue: str,
      callback: Callable[[Sequence[Any], bytes], None],
      receiver_max_keepalive_seconds: Optional[int] = None,
      receiver_max_active_callbacks: Optional[int] = None,
      receiver_max_messages_per_callback: Optional[int] = None,
  ) -> RequestQueue:
    """Registers a queue callback in a given queue.

    Args:
      queue: Name of the queue.
      callback: Callback with 2 args (expanded_key, payload). expanded_key is a
        sequence where each item corresponds to an item of the message's key.
        Payload is the message itself, serialized as bytes.
      receiver_max_keepalive_seconds: Num seconds before the lease on the
        message expires (if the message is not acked before the lease expires,
        it will be delivered again).
      receiver_max_active_callbacks: Max number of callback to be called in
        parallel.
      receiver_max_messages_per_callback: Max messages to receive per callback.

    Returns:
      New queue receiver objects.
    """

    def _Callback(message: pubsub_v1.subscriber.message.Message):
      payload = message.data
      callback(payload=payload, msg_id=message.message_id, ack_id=message.ack_id,
               publish_time=message.publish_time)

    if queue == "MessageHandler" or queue == "":
      subscription_path = self.message_handler_sub_path
    elif queue == "FlowProcessing":
      subscription_path = self.flow_processing_sub_path

    return RequestQueue(
        self.subscriber,
        subscription_path,
        _Callback,
        receiver_max_keepalive_seconds=receiver_max_keepalive_seconds,
        receiver_max_active_callbacks=receiver_max_active_callbacks,
        receiver_max_messages_per_callback=receiver_max_messages_per_callback,
    )
