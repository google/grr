#!/usr/bin/env python
"""Module containing functions for converting messages to dataframe."""
import collections
from collections.abc import Sequence
import datetime
import stat
from typing import Any, Optional

import pandas as pd

from google.protobuf import descriptor
from google.protobuf import message
from grr_response_proto import osquery_pb2
from grr_response_proto import semantic_pb2


def from_sequence(seq: Sequence[Any]) -> pd.DataFrame:
  """Converts sequence of objects to a dataframe.

  Args:
    seq: Sequence of objects to convert.

  Returns:
    Pandas dataframe representing given sequence of objects.
  """
  dframes = [from_object(obj) for obj in seq]
  if not dframes:
    return pd.DataFrame()

  return pd.concat(dframes, ignore_index=True, sort=False)


def from_object(obj: Any) -> pd.DataFrame:
  """Converts object to a dataframe.

  Args:
    obj: Object to convert.

  Returns:
    Pandas dataframe representing given object.
  """
  if isinstance(obj, message.Message):
    return from_message(obj)
  return pd.DataFrame(data=[obj])


def from_message(
    msg: message.Message, components: Optional[list[str]] = None
) -> pd.DataFrame:
  """Converts protobuf message to a dataframe.

  Args:
    msg: Protobuf message to convert.
    components: Prefixes for column names.

  Returns:
    Pandas dataframe representing given message.
  """
  if components is None:
    components = []

  data = {}
  for desc, value in msg.ListFields():
    if isinstance(value, message.Message):
      data.update(from_message(value, components + [desc.name]))
    else:
      data.update(_get_pretty_value(value, desc, components))

  return pd.DataFrame(data=data)


def from_osquery_table(table: osquery_pb2.OsqueryTable) -> pd.DataFrame:
  """Converts osquery table to a dataframe.

  Args:
    table: Table to convert.

  Returns:
    Pandas dataframe representing given osquery table.
  """
  columns = [column.name for column in table.header.columns]
  data = {column: [] for column in columns}

  for row in table.rows:
    for column, value in zip(columns, row.values):
      data[column].append(value)
  return pd.DataFrame(data=data)


def _get_pretty_value(
    value: Any, desc: descriptor.FieldDescriptor, components: list[str]
) -> dict[str, list[Any]]:
  """Converts value to the object easier to work with or more representative.

  Args:
    value: Object to transform.
    desc: Field descriptor of a value.
    components: Prefixes for column names.

  Returns:
    Data dictionary representing the given value.
  """
  data = {}
  column_name = '.'.join(components + [desc.name])
  sem_type = semantic_pb2.sem_type

  if desc.label == desc.LABEL_REPEATED:
    data[column_name] = [from_sequence(value)]

  elif desc.type == desc.TYPE_ENUM:
    char_name = next(_.name for _ in desc.enum_type.values if _.number == value)
    data[column_name] = [char_name]

  elif desc.type == desc.TYPE_BYTES:
    data[column_name] = [value]
    data[column_name + '.pretty'] = [repr(value)]

  elif desc.GetOptions().Extensions[sem_type].type == 'RDFDatetime':
    data[column_name] = [value]
    pretty_value = datetime.datetime.utcfromtimestamp(value / (10**6))
    data[column_name + '.pretty'] = [pretty_value]

  elif desc.GetOptions().Extensions[sem_type].type == 'StatMode':
    data[column_name] = [value]
    data[column_name + '.pretty'] = [stat.filemode(value)]

  else:
    data[column_name] = [value]

  return data


def reindex_dataframe(
    df: pd.DataFrame,
    priority_columns: Optional[list[str]] = None,
    ignore_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
  """Reorders and removes dataframe columns according to the given priorities.

  Args:
    df: Dataframe to reorder columns in.
    priority_columns: List of first columns in a new dataframe.
    ignore_columns: List of columns to remove from a dataframe.

  Returns:
    Reordered dataframe.
  """
  if priority_columns is None:
    priority_columns = []
  if ignore_columns is None:
    ignore_columns = []

  priorities = collections.defaultdict(lambda: len(priority_columns))
  for idx, column in enumerate(priority_columns):
    priorities[column] = idx

  ignore_columns = set(ignore_columns)
  columns = [_ for _ in df.columns if _ not in ignore_columns]
  columns = sorted(columns, key=lambda _: priorities[_])
  return df.reindex(columns=columns)


def add_pretty_column(
    df: pd.DataFrame, col_name: str, values: Sequence[Any]
) -> pd.DataFrame:
  """Adds pretty column for the specified column name with values provided.

  Args:
    df: Dataframe to add column to.
    col_name: Name of the original column.
    values: Values of the pretty column to add.

  Returns:
    Dataframe with the pretty column added.
  """
  if col_name not in df.columns:
    return df

  pretty_col_name = '{}.pretty'.format(col_name)

  if pretty_col_name in df.columns:
    df[pretty_col_name] = values
  else:
    df.insert(
        df.columns.get_loc(col_name) + 1, pretty_col_name, pd.Series(values))
  return df
