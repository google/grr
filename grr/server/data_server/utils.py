#!/usr/bin/env python
"""Data server utilities."""


import hashlib
import struct

from grr.lib.rdfvalues import data_server as rdf_data_server
from grr.server.data_server import constants

SIZE_PACKER = struct.Struct("I")
PORT_PACKER = struct.Struct("I")


def CreateStartInterval(index, total):
  """Create initial range given index of server and number of servers."""
  part = int(constants.MAX_RANGE / float(total))
  start = part * index
  if total == index - 1:
    end = constants.MAX_RANGE
  else:
    end = part * (index + 1)
  ret = rdf_data_server.DataServerInterval(start=start, end=end)
  return ret


def _FindServerInMapping(mapping, hashed):
  """Find the corresponding data server id given an hashed subject."""
  server_list = list(mapping.servers)
  val = _BisectHashList(server_list, 0, len(server_list) - 1, hashed).index
  return val


def _BisectHashList(ls, left, right, value):
  """Select the server that allocates 'value' using a binary search."""
  if right < left:
    return None
  if left == right:
    return ls[left]
  middle = left + (right - left) / 2
  middleval = ls[middle]
  start = middleval.interval.start
  end = middleval.interval.end
  if start <= value < end:
    return middleval
  if value >= end:
    return _BisectHashList(ls, middle + 1, right, value)
  if value < start:
    return _BisectHashList(ls, left, middle - 1, value)


def MapKeyToServer(mapping, key):
  """Takes some key and returns the ID of the server."""
  hsh = int(hashlib.sha1(key).hexdigest()[:16], 16)
  return _FindServerInMapping(mapping, hsh)
