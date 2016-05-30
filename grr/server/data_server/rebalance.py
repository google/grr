#!/usr/bin/env python
"""Utilities for load rebalancing."""


import os
import shutil
import StringIO
import zlib

# pylint: disable=g-import-not-at-top
try:
  import urllib3
  from urllib3 import connectionpool
except ImportError:
  # Urllib3 also comes as part of requests, try to fallback.
  from requests.packages import urllib3
  from requests.packages.urllib3 import connectionpool

import logging

from grr.lib import data_store
from grr.lib import utils
from grr.lib.data_stores import common
from grr.lib.rdfvalues import data_server as rdf_data_server

from grr.server.data_server import constants
from grr.server.data_server import store
from grr.server.data_server import utils as sutils
# pylint: enable=g-import-not-at-top

# Database files that cannot be copied.
COPY_EXCEPTIONS = [store.BASE_MAP_SUBJECT]
# Files that cannot be moved from inside the transaction directory.
MOVE_EXCEPTIONS = [constants.TRANSACTION_FILENAME, constants.REMOVE_FILENAME]
# Level of compression when moving Sqlite files.
COMPRESSION_LEVEL = 3


def _RecComputeRebalanceSize(mapping, server_id, dspath, subpath):
  """Recursively compute the size of files that need to be moved."""
  total = 0
  fulldir = utils.JoinPath(dspath, subpath)
  for comp in os.listdir(fulldir):
    if comp == constants.REBALANCE_DIRECTORY:
      continue
    # Real path name.
    path = utils.JoinPath(fulldir, comp)
    # Get basename and extension.
    name, unused_extension = os.path.splitext(comp)
    if name in COPY_EXCEPTIONS:
      logging.info("Skip %s", comp)
      continue
    if os.path.isdir(path):
      total += _RecComputeRebalanceSize(mapping, server_id, dspath,
                                        utils.JoinPath(subpath, comp))
    elif os.path.isfile(path):
      key = common.MakeDestinationKey(subpath, name)
      where = sutils.MapKeyToServer(mapping, key)
      if where != server_id:
        logging.info("Need to move %s from %d to %d", path, server_id, where)
        total += os.path.getsize(path)
      else:
        logging.info("File %s stays here", path)
  return total


def ComputeRebalanceSize(mapping, server_id):
  """Compute size of files that need to be moved."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return 0
  if not os.path.isdir(loc):
    return 0
  return _RecComputeRebalanceSize(mapping, server_id, loc, "")


class FileCopyWrapper(object):
  """Wraps the database file for post'ing it to the server."""

  def __init__(self, rebalance, directory, filename, fullpath):
    filesize = os.path.getsize(fullpath)
    filecopy = rdf_data_server.DataServerFileCopy(rebalance_id=rebalance.id,
                                                  directory=directory,
                                                  filename=filename,
                                                  size=filesize)
    filecopy_str = filecopy.SerializeToString()
    self.header = sutils.SIZE_PACKER.pack(len(filecopy_str))
    self.header += filecopy_str
    self.header = StringIO.StringIO(self.header)
    self.fp = open(fullpath, "rb")
    self.compressor = zlib.compressobj(COMPRESSION_LEVEL)
    # Buffered compressed data that needs to be read.
    self.buffered = ""
    # Flag to mark end of database file.
    self.end_of_file = False
    # Flag to mark if we can no longer use read().
    self.end_of_stream = False
    # Flag to indicate that we are going to read the header first.
    self.read_header = True

  def read(self, blocksize):  # pylint: disable=invalid-name
    """Returns data back to the HTTP post request."""
    if self.end_of_stream:
      return ""
    if self.read_header:
      # Read from header first.
      ret = self.header.read(blocksize)
      if ret:
        return ret
      self.read_header = False
    # Otherwise, read from the file, compress the data and return it.
    # Note that since we add a block size marker, we need subtract marker size.
    blocksize -= sutils.SIZE_PACKER.size
    while not self.buffered and not self.end_of_file:
      raw = self.fp.read(blocksize)
      if not raw:
        # We need to flush the compressor and send that data too.
        self.end_of_file = True
        self.buffered += self.compressor.flush()
        break
      # While compressing, we may not get anything immediatelly.
      compressed = self.compressor.compress(raw)
      if compressed:
        self.buffered += compressed
    if len(self.buffered) > blocksize:
      ret = self.buffered[:blocksize]
      self.buffered = self.buffered[blocksize:]
    else:
      ret = self.buffered
      self.buffered = ""
    if not ret:
      # Once the data is exhausted, we mark the end of the stream
      # and we simply return the 0 marker.
      self.end_of_stream = True
    # Return the size of the block plus the block itself.
    return sutils.SIZE_PACKER.pack(len(ret)) + ret

  def close(self):  # pylint: disable=invalid-name
    self.fp.close()
    self.header.close()


def _SendFileToServer(pool, fullpath, subpath, basename, rebalance):
  """Sends a specific data store file to the server."""
  fp = FileCopyWrapper(rebalance, subpath, basename, fullpath)

  try:
    # Content-Length is 0 since we do not know the size of the compressed data.
    # We write the compressed data by blocks.
    headers = {"Content-Length": 0}
    res = pool.urlopen("POST", "/rebalance/copy-file", headers=headers, body=fp)
    if res.status != constants.RESPONSE_OK:
      return False
  except urllib3.exceptions.MaxRetryError:
    logging.warning("Failed to send file %s", fullpath)
    return False
  finally:
    fp.close()
  return True


def _GetTransactionDirectory(database_dir, rebalance_id):
  dirname = common.ConvertStringToFilename(rebalance_id)
  tempdir = utils.JoinPath(database_dir, constants.REBALANCE_DIRECTORY, dirname)
  return tempdir


def _CreateDirectory(database_dir, rebalance_id):
  tempdir = _GetTransactionDirectory(database_dir, rebalance_id)
  try:
    os.makedirs(tempdir)
  except os.error:
    pass
  return tempdir


def _FileWithRemoveList(database_dir, rebalance):
  tempdir = _CreateDirectory(database_dir, rebalance.id)
  return utils.JoinPath(tempdir, constants.REMOVE_FILENAME)


def _RecCopyFiles(rebalance, server_id, dspath, subpath, pool_cache,
                  removed_list):
  """Recursively send files for moving to the required data server."""
  fulldir = utils.JoinPath(dspath, subpath)
  mapping = rebalance.mapping
  for comp in os.listdir(fulldir):
    if comp == constants.REBALANCE_DIRECTORY:
      continue
    path = utils.JoinPath(fulldir, comp)
    name, unused_extension = os.path.splitext(comp)
    if name in COPY_EXCEPTIONS:
      continue
    if os.path.isdir(path):
      result = _RecCopyFiles(rebalance, server_id, dspath,
                             utils.JoinPath(subpath, comp), pool_cache,
                             removed_list)
      if not result:
        return False
      continue
    if not os.path.isfile(path):
      continue
    key = common.MakeDestinationKey(subpath, name)
    where = sutils.MapKeyToServer(mapping, key)
    if where != server_id:
      server = mapping.servers[where]
      addr = server.address
      port = server.port
      key = (addr, port)
      try:
        pool = pool_cache[key]
      except KeyError:
        pool = connectionpool.HTTPConnectionPool(addr, port=port)
        pool_cache[key] = pool
      logging.info("Need to move %s from %d to %d", key, server_id, where)
      if not _SendFileToServer(pool, path, subpath, comp, rebalance):
        return False
      removed_list.append(path)
    else:
      logging.info("File %s stays here", path)
  return True


def CopyFiles(rebalance, server_id):
  """Copies data store files to the corresponding data servers."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return True
  if not os.path.isdir(loc):
    return True
  pool_cache = {}
  removed_list = []
  ok = _RecCopyFiles(rebalance, server_id, loc, "", pool_cache, removed_list)
  if not ok:
    return False
  # Write list of removed files to temporary directory
  remove_file = _FileWithRemoveList(loc, rebalance)
  with open(remove_file, "w") as fp:
    for f in removed_list:
      fp.write(f.encode("utf8") + "\n")
  return True


def SaveTemporaryFile(fp):
  """Store incoming database file in a temporary directory."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  # Read DataServerFileCopy object.
  filecopy_len_str = fp.read(sutils.SIZE_PACKER.size)
  filecopy_len = sutils.SIZE_PACKER.unpack(filecopy_len_str)[0]
  filecopy = rdf_data_server.DataServerFileCopy(fp.read(filecopy_len))

  rebdir = _CreateDirectory(loc, filecopy.rebalance_id)
  filedir = utils.JoinPath(rebdir, filecopy.directory)
  try:
    os.makedirs(filedir)
  except OSError:
    pass
  filepath = utils.JoinPath(filedir, filecopy.filename)
  logging.info("Writing to file %s", filepath)
  with open(filepath, "wb") as wp:
    # We need to uncompress the file stream.
    decompressor = zlib.decompressobj()
    while True:
      block_len_str = fp.read(sutils.SIZE_PACKER.size)
      block_len = sutils.SIZE_PACKER.unpack(block_len_str)[0]
      if not block_len:
        break
      block = fp.read(block_len)
      to_decompress = decompressor.unconsumed_tail + block
      while to_decompress:
        decompressed = decompressor.decompress(to_decompress)
        if decompressed:
          wp.write(decompressed)
          to_decompress = decompressor.unconsumed_tail
        else:
          to_decompress = ""
    # Deal with remaining data.
    remaining = decompressor.flush()
    if remaining:
      wp.write(remaining)
  if os.path.getsize(filepath) != filecopy.size:
    logging.error("Size of file %s is not %d", filepath, filecopy.size)
    return False
  return True


def _RecMoveFiles(tempdir, dspath, subpath):
  fulltempdir = utils.JoinPath(tempdir, subpath)
  fulldsdir = utils.JoinPath(dspath, subpath)
  try:
    # The data store must have this directory.
    os.makedirs(fulldsdir)
  except OSError:
    pass
  for fname in os.listdir(fulltempdir):
    if fname in MOVE_EXCEPTIONS:
      # We do not need to move this file.
      continue
    temppath = utils.JoinPath(fulltempdir, fname)
    if os.path.isfile(temppath):
      newpath = utils.JoinPath(fulldsdir, fname)
      logging.info("Moving file %s to %s", temppath, newpath)
      os.rename(temppath, newpath)
    elif os.path.isdir(temppath):
      _RecMoveFiles(tempdir, dspath, utils.JoinPath(subpath, fname))


def MoveFiles(rebalance, is_master):
  """Commit the received files into the database."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  tempdir = _CreateDirectory(loc, rebalance.id)
  # Read files to remove.
  remove_file = _FileWithRemoveList(loc, rebalance)
  to_remove = []
  if os.path.exists(remove_file):
    to_remove = [line.decode("utf8").rstrip("\n")
                 for line in open(remove_file, "r")]
  for fname in to_remove:
    if not fname.startswith(loc):
      logging.warning("Wrong file to remove: %s", fname)
      continue
    if not os.path.exists(fname):
      logging.warning("File does not exist: %s", fname)
      continue
    if not os.path.isfile(fname):
      logging.warning("Not a file: %s", fname)
      continue
    os.unlink(fname)
    logging.info("Removing file %s", fname)
  try:
    os.unlink(remove_file)
  except OSError:
    pass
  # Move files.
  try:
    _RecMoveFiles(tempdir, loc, "")
  except OSError:
    return False
  # Remove temporary directory.
  # Master will remove it later.
  if not is_master:
    if tempdir.startswith(loc):
      shutil.rmtree(tempdir)
  return True


def SaveCommitInformation(rebalance):
  """Save rebalance object to file."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  tempdir = _CreateDirectory(loc, rebalance.id)
  tempfile = utils.JoinPath(tempdir, constants.TRANSACTION_FILENAME)
  with open(tempfile, "wb") as fp:
    fp.write(rebalance.SerializeToString())
  return True


def DeleteCommitInformation(rebalance):
  """Remove file with rebalance information."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  tempdir = _GetTransactionDirectory(loc, rebalance.id)
  tempfile = utils.JoinPath(tempdir, constants.TRANSACTION_FILENAME)
  try:
    os.unlink(tempfile)
  except OSError:
    pass
  return True


def GetCommitInformation(transid):
  """Read transaction information from stored file."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  tempdir = _GetTransactionDirectory(loc, transid)
  tempfile = utils.JoinPath(tempdir, constants.TRANSACTION_FILENAME)
  if not os.path.exists(tempfile):
    return None
  if not os.path.isfile(tempfile):
    return None
  with open(tempfile, "rb") as fp:
    return rdf_data_server.DataServerRebalance(fp.read())


def RemoveDirectory(rebalance):
  """Remove temporary directory of the given rebalance object."""
  loc = data_store.DB.Location()
  if not os.path.exists(loc):
    return False
  if not os.path.isdir(loc):
    return False
  tempdir = _GetTransactionDirectory(loc, rebalance.id)
  try:
    if tempdir.startswith(loc):
      shutil.rmtree(tempdir)
  except OSError:
    pass
