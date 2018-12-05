#!/usr/bin/env python
"""Functions for manipulating ipv6 addresses.

We've written our own versions of socket.inet_pton and inet_ntop for ipv6
because those functions are not available on windows before python 3.4.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
import socket

# pytype: disable=import-error
from builtins import range  # pylint: disable=redefined-builtin
# pytype: enable=import-error

# ntop does not exist on Windows.
# pylint: disable=g-socket-inet-aton,g-socket-inet-ntoa

V4_ENDING = re.compile(r"(?P<v6>.*):(\d+)\.(\d+)\.(\d+)\.(\d+)$")
ZERO_SEQUENCE = re.compile(r"(?:^|\:)(?:0\:?)+")
BAD_SINGLE_COLON = re.compile(r"(^\:[^:].*|.*[^:]\:$)")


def _RemoveV4Ending(addr_string):
  """Replace v4 endings with v6 equivalents."""
  match = V4_ENDING.match(addr_string)
  if match:
    ipv4_addr = ".".join(match.groups()[1:])
    try:
      socket.inet_aton(ipv4_addr.encode("ascii"))
    except (socket.error, ValueError):
      raise socket.error("Illegal IPv4 extension: %s" % addr_string)

    if int(match.group(2)) == 0:
      raise socket.error("IPv4 can't start with 0")

    return "%s:%04x:%04x" % (match.group("v6"),
                             int(match.group(2)) * 256 + int(match.group(3)),
                             int(match.group(4)) * 256 + int(match.group(5)))
  return addr_string


def _StripLeadingOrTrailingDoubleColons(addr_string):
  """Strip leading or trailing double colon."""

  if addr_string.startswith("::"):
    return addr_string[1:]
  if addr_string.endswith("::"):
    return addr_string[:-1]
  return addr_string


def _ZeroPad(addr_string):
  """Pad out zeros in each address chunk as necessary."""
  chunks = addr_string.split(":")
  total_length = len(chunks)
  if total_length > 8:
    raise socket.error(
        "Too many address chunks in %s, expected 8" % addr_string)

  double_colon = False
  addr_array = []
  for chunk in chunks:
    if chunk:
      chunk_len = len(chunk)
      if chunk_len > 4:
        raise socket.error("Chunk must be length 4: %s" % addr_string)
      if chunk_len != 4:
        # Pad out with 0's until we have 4 digits
        chunk = "0" * (4 - chunk_len) + chunk
      addr_array.append(chunk)
    else:
      if double_colon:
        raise socket.error("More than one double colon in %s" % addr_string)
      else:
        double_colon = True
        # Add zeros for the compressed chunks
        addr_array.extend(["0000"] * (8 - total_length + 1))

  if len(addr_array) != 8:
    raise socket.error("Bad address length, expected 8 chunks: %s" % addr_array)

  return "".join(addr_array)


def InetPtoN(protocol, addr_string):
  """Convert ipv6 string to packed bytes.

  Args:
    protocol: socket.AF_INET or socket.AF_INET6
    addr_string: IPv6 address string
  Returns:
    bytestring representing address
  Raises:
    socket.error: on bad IPv6 address format
  """
  if protocol == socket.AF_INET:
    return socket.inet_aton(addr_string)

  if protocol != socket.AF_INET6:
    raise socket.error("Unsupported protocol")

  if not addr_string:
    raise socket.error("Empty address string")

  if BAD_SINGLE_COLON.match(addr_string):
    raise socket.error("Start or ends with single colon")

  if addr_string == "::":
    return ("0" * 32).decode("hex_codec")

  addr_string = _RemoveV4Ending(addr_string)
  addr_string = _StripLeadingOrTrailingDoubleColons(addr_string)
  addr_string = _ZeroPad(addr_string)

  try:
    return addr_string.decode("hex_codec")
  except TypeError:
    raise socket.error("Error decoding: %s" % addr_string)


def InetNtoP(protocol, packed_bytes):
  """Convert ipv6 packed bytes to string.

  Args:
    protocol: protocol
    packed_bytes: bytestring
  Returns:
    ipv6 string
  Raises:
    socket.error: on bad bytestring
  """

  if protocol == socket.AF_INET:
    return socket.inet_ntoa(packed_bytes)

  if protocol != socket.AF_INET6:
    raise socket.error("Unsupported protocol")

  if len(packed_bytes) != 16:
    raise socket.error("IPv6 addresses are 16 bytes long, got %s for %s" %
                       (len(packed_bytes), packed_bytes))

  hex_encoded = packed_bytes.encode("hex_codec")

  # Detect IPv4 endings
  if hex_encoded.startswith("00000000000000000000ffff"):
    return "::ffff:" + socket.inet_ntoa(packed_bytes[-4:])

  # Detect IPv4 endings. If the first quad is 0, it isn't IPv4.
  if hex_encoded.startswith("0" * 24) and not hex_encoded.startswith("0" * 28):
    return "::" + socket.inet_ntoa(packed_bytes[-4:])

  # Split into quads
  chunked = [hex_encoded[i:i + 4] for i in range(0, len(hex_encoded), 4)]

  output = []
  for chunk in chunked:
    # Strip leading zeros
    chunk = "".join(chunk).lstrip("0")
    if not chunk:
      # Set all 0 chunks to a single 0
      chunk = "0"
    output.append(chunk)

  result_str = ":".join(output)

  # Compress with :: by finding longest sequence of zeros that look like :0:0:0
  # or 0:0:0 if its the start of the string
  matches = ZERO_SEQUENCE.findall(result_str)
  if matches:
    largest_zero_str = max(matches, key=len)

    if len(largest_zero_str) > 3:
      # Replace any zero string longer than :0: with ::
      result_str = result_str.replace(largest_zero_str, "::", 1)

  return result_str


# If the implementation supports it, just use the native functions.
# pylint: disable=invalid-name

# Keep a reference to the custom functions in case we really want them (for
# tests).
CustomInetNtoP = InetNtoP
CustomInetPtoN = InetPtoN

if getattr(socket, "inet_ntop", None):
  InetNtoP = socket.inet_ntop

if getattr(socket, "inet_pton", None):
  InetPtoN = socket.inet_pton
