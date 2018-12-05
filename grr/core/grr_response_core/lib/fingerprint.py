#!/usr/bin/env python

# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file was imported with permission from
# http://verify-sigs.googlecode.com/files/verify-sigs-1.1.tar.bz2
"""Fingerprinter class and some utilty functions to exercise it.

While this file contains a main and some top-level functions, those
are meant for exploration and debugging. Intended use is through the
Fingerprinter, as exemplified in main.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import hashlib
import os
import struct

# pylint: disable=g-bad-name
# Two classes given named tupes for ranges and relative ranges.
Range = collections.namedtuple('Range', 'start end')
RelRange = collections.namedtuple('RelRange', 'start len')

# pylint: enable=g-bad-name


class Finger(object):
  """A Finger defines how to hash a file to get specific fingerprints.

  The Finger contains one or more hash functions, a set of ranges in the
  file that are to be processed with these hash functions, and relevant
  metadata and accessor methods.

  While one Finger provides potentially multiple hashers, they all get
  fed the same ranges of the file.
  """

  def __init__(self, hashers, ranges, metadata_dict):
    self.hashers = hashers
    self.ranges = ranges
    self.metadata = metadata_dict

  def CurrentRange(self):
    """The working range of this Finger. Returns None if there is none."""
    if self.ranges:
      return self.ranges[0]
    return None

  def ConsumeRange(self, start, end):
    """Consumes an entire range, or part thereof.

    If the finger has no ranges left, or the curent range start is higher
    than the end of the consumed block, nothing happens. Otherwise,
    the current range is adjusted for the consumed block, or removed,
    if the entire block is consumed. For things to work, the consumed
    range and the current finger starts must be equal, and the length
    of the consumed range may not exceed the length of the current range.

    Args:
      start: Beginning of range to be consumed.
      end: First offset after the consumed range (end + 1).

    Raises:
      RuntimeError: if the start position of the consumed range is
          higher than the start of the current range in the finger, or if
          the consumed range cuts accross block boundaries.
    """
    old = self.CurrentRange()
    if old is None:
      return
    if old.start > start:
      if old.start < end:
        raise RuntimeError('Block end too high.')
      return
    if old.start < start:
      raise RuntimeError('Block start too high.')
    if old.end == end:
      del self.ranges[0]
    elif old.end > end:
      self.ranges[0] = Range(end, old.end)
    else:
      raise RuntimeError('Block length exceeds range.')

  def HashBlock(self, block):
    """Given a data block, feed it to all the registered hashers."""
    for hasher in self.hashers:
      hasher.update(block)


class Fingerprinter(object):
  """Compute different types of cryptographic hashes over a file.

  Depending on type of file and mode of invocation, filetype-specific or
  generic hashes get computed over a file. Different hashes can cover
  different ranges of the file. The file is read only once. Memory
  use of class objects is dominated by min(file size, block size),
  as defined below.

  The class delivers an array with dicts of hashes by file type. Where
  appropriate, embedded signature data is also returned from the file.

  Suggested use:
  - Provide file object at initialisation time.
  - Invoke one or more of the Eval* functions, with your choice of hashers.
  - Call HashIt and take from the resulting dict what you need.
  """

  BLOCK_SIZE = 1000000
  GENERIC_HASH_CLASSES = (hashlib.md5, hashlib.sha1, hashlib.sha256,
                          hashlib.sha512)
  AUTHENTICODE_HASH_CLASSES = (hashlib.md5, hashlib.sha1)

  def __init__(self, file_obj):
    self.fingers = []
    self.file = file_obj
    self.file.seek(0, os.SEEK_END)
    self.filelength = self.file.tell()

  def _GetNextInterval(self):
    """Returns the next Range of the file that is to be hashed.

    For all fingers, inspect their next expected range, and return the
    lowest uninterrupted range of interest. If the range is larger than
    BLOCK_SIZE, truncate it.

    Returns:
      Next range of interest in a Range namedtuple.
    """
    ranges = [x.CurrentRange() for x in self.fingers]
    starts = set([r.start for r in ranges if r])
    ends = set([r.end for r in ranges if r])
    if not starts:
      return None
    min_start = min(starts)
    starts.remove(min_start)
    ends |= starts
    min_end = min(ends)
    if min_end - min_start > self.BLOCK_SIZE:
      min_end = min_start + self.BLOCK_SIZE
    return Range(min_start, min_end)

  def _AdjustIntervals(self, start, end):
    for finger in self.fingers:
      finger.ConsumeRange(start, end)

  def _HashBlock(self, block, start, end):
    """_HashBlock feeds data blocks into the hashers of fingers.

    This function must be called before adjusting fingers for next
    interval, otherwise the lack of remaining ranges will cause the
    block not to be hashed for a specific finger.

    Start and end are used to validate the expected ranges, to catch
    unexpected use of that logic.

    Args:
      block: The data block.
      start: Beginning offset of this block.
      end: Offset of the next byte after the block.

    Raises:
      RuntimeError: If the provided and expected ranges don't match.
    """
    for finger in self.fingers:
      expected_range = finger.CurrentRange()
      if expected_range is None:
        continue
      if (start > expected_range.start or
          (start == expected_range.start and end > expected_range.end) or
          (start < expected_range.start and end > expected_range.start)):
        raise RuntimeError('Cutting across fingers.')
      if start == expected_range.start:
        finger.HashBlock(block)

  def HashIt(self):
    """Finalizing function for the Fingerprint class.

    This method applies all the different hash functions over the
    previously specified different ranges of the input file, and
    computes the resulting hashes.

    After calling HashIt, the state of the object is reset to its
    initial state, with no fingers defined.

    Returns:
      An array of dicts, with each dict containing name of fingerprint
      type, names of hashes and values, and additional, type-dependent
      key / value pairs, such as an array of SignedData tuples for the
      PE/COFF fingerprint type.

    Raises:
       RuntimeError: when internal inconsistencies occur.
    """
    while True:
      interval = self._GetNextInterval()
      if interval is None:
        break
      self.file.seek(interval.start, os.SEEK_SET)
      block = self.file.read(interval.end - interval.start)
      if len(block) != interval.end - interval.start:
        raise RuntimeError('Short read on file.')
      self._HashBlock(block, interval.start, interval.end)
      self._AdjustIntervals(interval.start, interval.end)

    results = []
    for finger in self.fingers:
      res = {}
      leftover = finger.CurrentRange()
      if leftover:
        if (len(finger.ranges) > 1 or leftover.start != self.filelength or
            leftover.end != self.filelength):
          raise RuntimeError('Non-empty range remains.')
      res.update(finger.metadata)
      for hasher in finger.hashers:
        res[hasher.name] = hasher.digest()
      results.append(res)

    # Clean out things for a fresh start (on the same file object).
    self.fingers = []

    # Make sure the results come back in 'standard' order, regardless of the
    # order in which fingers were added. Helps with reproducing test results.
    return sorted(results, key=lambda r: r['name'])

  def EvalGeneric(self, hashers=None):
    """Causes the entire file to be hashed by the given hash functions.

    This sets up a 'finger' for fingerprinting, where the entire file
    is passed through a pre-defined (or user defined) set of hash functions.

    Args:
      hashers: An iterable of hash classes (e.g. out of hashlib) which will
               be instantiated for use. If hashers is not provided, or is
               provided as 'None', the default hashers will get used. To
               invoke this without hashers, provide an empty list.

    Returns:
      Always True, as all files are 'generic' files.
    """
    if hashers is None:
      hashers = Fingerprinter.GENERIC_HASH_CLASSES
    hashfuncs = [x() for x in hashers]
    finger = Finger(hashfuncs, [Range(0, self.filelength)], {'name': 'generic'})
    self.fingers.append(finger)
    return True

  def _PecoffHeaderParser(self):
    """Parses PECOFF headers.

    Reads header magic and some data structures in a file to determine if
    it is a valid PECOFF header, and figure out the offsets at which
    relevant data is stored.
    While this code contains multiple seeks and small reads, that is
    compensated by the underlying libc buffering mechanism.

    Returns:
      None if the parsed file is not PECOFF.
      A dict with offsets and lengths for CheckSum, CertTable, and SignedData
      fields in the PECOFF binary, for those that are present.
    """
    extents = {}
    self.file.seek(0, os.SEEK_SET)
    buf = self.file.read(2)
    if buf != 'MZ':
      return None
    self.file.seek(0x3C, os.SEEK_SET)
    buf = self.file.read(4)
    pecoff_sig_offset = struct.unpack('<I', buf)[0]
    if pecoff_sig_offset >= self.filelength:
      return None
    self.file.seek(pecoff_sig_offset, os.SEEK_SET)
    buf = self.file.read(4)
    if buf != 'PE\0\0':
      return None
    self.file.seek(pecoff_sig_offset + 20, os.SEEK_SET)
    buf = self.file.read(2)
    optional_header_size = struct.unpack('<H', buf)[0]
    optional_header_offset = pecoff_sig_offset + 4 + 20
    if optional_header_size + optional_header_offset > self.filelength:
      # This is not strictly a failure for windows, but such files better
      # be treated as generic files. They can not be carrying SignedData.
      return None
    if optional_header_size < 68:
      # We can't do authenticode-style hashing. If this is a valid binary,
      # which it can be, the header still does not even contain a checksum.
      return None
    self.file.seek(optional_header_offset, os.SEEK_SET)
    buf = self.file.read(2)
    image_magic = struct.unpack('<H', buf)[0]
    if image_magic == 0x10b:
      # 32 bit
      rva_base = optional_header_offset + 92
      cert_base = optional_header_offset + 128
    elif image_magic == 0x20b:
      # 64 bit
      rva_base = optional_header_offset + 108
      cert_base = optional_header_offset + 144
    else:
      # A ROM image or such, not in the PE/COFF specs. Not sure what to do.
      return None
    extents['CheckSum'] = RelRange(optional_header_offset + 64, 4)
    self.file.seek(rva_base, os.SEEK_SET)
    buf = self.file.read(4)
    number_of_rva = struct.unpack('<I', buf)[0]
    if (number_of_rva < 5 or
        optional_header_offset + optional_header_size < cert_base + 8):
      return extents
    extents['CertTable'] = RelRange(cert_base, 8)

    self.file.seek(cert_base, os.SEEK_SET)
    buf = self.file.read(8)
    start, length = struct.unpack('<II', buf)
    if (length == 0 or start < optional_header_offset + optional_header_size or
        start + length > self.filelength):
      # The location of the SignedData blob is just wrong (or there is none).
      # Ignore it -- everything else we did still makes sense.
      return extents
    extents['SignedData'] = RelRange(start, length)
    return extents

  def _CollectSignedData(self, extent):
    """Extracts signedData blob from PECOFF binary and parses first layer."""
    start, length = extent

    self.file.seek(start, os.SEEK_SET)
    buf = self.file.read(length)
    signed_data = []
    # This loop ignores trailing cruft, or too-short signedData chunks.
    while len(buf) >= 8:
      dw_length, w_revision, w_cert_type = struct.unpack('<IHH', buf[:8])
      if dw_length < 8:
        # If the entire blob is smaller than its header, bail out.
        return signed_data
      b_cert = buf[8:dw_length]
      buf = buf[(dw_length + 7) & 0x7ffffff8:]
      signed_data.append((w_revision, w_cert_type, b_cert))
    return signed_data

  def EvalPecoff(self, hashers=None):
    """If the file is a PE/COFF file, computes authenticode hashes on it.

    This checks if the input file is a valid PE/COFF image file (e.g. a
    Windows binary, driver, or DLL) and if yes, sets up a 'finger' for
    fingerprinting in Authenticode style.
    If available, the 'SignedData' section of the image file is retrieved,
    and parsed into its constituent parts. An array of tuples of these
    parts is added to results by HashIt()

    Args:
      hashers: An iterable of hash classes (e.g. out of hashlib) which will
               be instantiated for use. If 'None' is provided, a default set
               of hashers is used. To select no hash function (e.g. to only
               extract metadata), use an empty iterable.

    Returns:
      True if the file is detected as a valid PE/COFF image file,
      False otherwise.
    """
    try:
      extents = self._PecoffHeaderParser()
    except struct.error:
      # Parsing the header failed. Just ignore this, and claim
      # that the file is not a valid PE/COFF image file.
      extents = None
    if extents is None:
      return False

    signed_data = None
    ranges = []
    start = 0
    # Ordering of these conditions matches expected order in file.
    # If a condition holds true, the matching range is skipped for hashing.
    if 'CheckSum' in extents:
      ranges.append(Range(start, end=extents['CheckSum'].start))
      start = sum(extents['CheckSum'])
      # New start now points past CheckSum area.
    if 'CertTable' in extents:
      ranges.append(Range(start, end=extents['CertTable'].start))
      start = sum(extents['CertTable'])
      # New start now points past CertTable area.
    if 'SignedData' in extents:
      # Exclude the range even if the blob itself can't be parsed correctly.
      ranges.append(Range(start, end=extents['SignedData'].start))
      start = sum(extents['SignedData'])
      # New start now points past SignedData area.
      signed_data = self._CollectSignedData(extents['SignedData'])
    ranges.append(Range(start, end=self.filelength))

    if hashers is None:
      hashers = Fingerprinter.AUTHENTICODE_HASH_CLASSES
    hashfuncs = [x() for x in hashers]
    metadata = {'name': 'pecoff'}
    if signed_data:
      metadata['SignedData'] = signed_data
    finger = Finger(hashfuncs, ranges, metadata)
    self.fingers.append(finger)
    return True
