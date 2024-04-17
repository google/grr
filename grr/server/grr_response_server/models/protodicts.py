#!/usr/bin/env python
"""Module with helpers related to `Dict` messages."""

from typing import Union

from grr_response_proto import jobs_pb2


DataBlobValue = Union[
    bool,
    int,
    float,
    bytes,
    str,
    list["DataBlobValue"],
    dict["DataBlobValue", "DataBlobValue"],
]


def DataBlob(value: DataBlobValue) -> jobs_pb2.DataBlob:
  """Creates a `DataBlob` message from the given Python value.

  Args:
    value: A Python value to convert to a `DataBlob` message.

  Returns:
    A `DataBlob` message corresponding to the given value.
  """
  if isinstance(value, bool):
    return jobs_pb2.DataBlob(boolean=value)
  if isinstance(value, int):
    return jobs_pb2.DataBlob(integer=value)
  if isinstance(value, float):
    return jobs_pb2.DataBlob(float=value)
  if isinstance(value, str):
    return jobs_pb2.DataBlob(string=value)
  if isinstance(value, bytes):
    return jobs_pb2.DataBlob(data=value)
  if isinstance(value, list):
    result = jobs_pb2.DataBlob()
    result.list.CopyFrom(BlobArray(value))
    return result
  if isinstance(value, dict):
    result = jobs_pb2.DataBlob()
    result.dict.CopyFrom(Dict(value))
    return result

  raise TypeError(f"Unexpected type: {type(value)}")


def BlobArray(values: list[DataBlobValue]) -> jobs_pb2.BlobArray:
  """Creates a `BlobArray` message from the given list of Python values.

  Args:
    values: A list of Python values to convert to a `BlobArray` message.

  Returns:
    A `BlobArray` message corresponding to the given Python list.
  """
  result = jobs_pb2.BlobArray()

  for value in values:
    result.content.append(DataBlob(value))

  return result


def Dict(dikt: dict[DataBlobValue, DataBlobValue]) -> jobs_pb2.Dict:
  """Creates a `Dict` message from the given Python dictionary.

  Args:
    dikt: A dictionary of Python values to convert to a `Dict` message.

  Returns:
    A `Dict` message corresponding to the given Python dictionary.
  """
  result = jobs_pb2.Dict()

  for key, value in dikt.items():
    result.dat.add(k=DataBlob(key), v=DataBlob(value))

  return result
