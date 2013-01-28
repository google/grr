#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Utils exporting data from AFF4 to the rest of the world."""

import os
import stat

import logging

from grr.lib import aff4
from grr.lib import threadpool


BUFFER_SIZE = 16 * 1024 * 1024


def GetAllClients():
  """Return a list of all client urns."""
  return [str(x) for x in aff4.FACTORY.Open(aff4.ROOT_URN).ListChildren() if
          aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(str(x)[6:])]


def IterateAllClients(func, threads=10, token=None):
  """Iterate over all clients in a threadpool.

  Args:
    func: A function to call with each client urn.
    threads: Number of threads to use.
    token: Auth token.
  """

  tp = threadpool.ThreadPool.Factory("ClientIter", threads)
  tp.Start()
  clients = GetAllClients()
  logging.info("Got %d clients", len(clients))

  for count, client in enumerate(clients):
    if count % 2000 == 0:
      logging.info("%d clients processed.", count)
    args = (client, token)
    tp.AddTask(target=func, args=args,
               name="ClientIter")


def DownloadFile(file_obj, target_path, buffer_size=BUFFER_SIZE):
  """Download an aff4 file to the local filesystem overwriting it if it exists.

  Args:
    file_obj: An aff4 object that supports the file interface (Read, Seek)
    target_path: Full path of file to write to.
    buffer_size: Read in chunks this size.
  """
  logging.info("Downloading: %s to: %s", file_obj.urn, target_path)

  target_file = open(target_path, "w")
  file_obj.Seek(0)

  data_buffer = file_obj.Read(buffer_size)
  while data_buffer:
    target_file.write(data_buffer)
    data_buffer = file_obj.Read(buffer_size)
  target_file.close()


def RecursiveDownload(dir_obj, target_dir):
  """Recursively downloads a file entry to the target path.

  Args:
    dir_obj: An aff4 object that contains children.
    target_dir: Full path of the directory to write to.
  """
  for sub_file_entry in dir_obj.OpenChildren():
    path_elements = [target_dir]
    sub_target_dir = u"/".join(path_elements)
    try:
      # Any file-like object with data in AFF4 should inherit AFF4Stream
      if isinstance(sub_file_entry, aff4.AFF4Stream):
        CopyAFF4ToLocal(sub_file_entry, sub_target_dir)
      else:
        os.mkdir(sub_target_dir)
        RecursiveDownload(sub_file_entry, sub_target_dir)
    except IOError:
      logging.exception("Unable to download %s", sub_file_entry.urn)
    finally:
      sub_file_entry.Close()


def DownloadCollection(coll_path, target_path, token=None, overwrite=False,
                       max_threads=10):
  """Iterate through a Collection object downloading all files.

  Args:
    coll_path: Path to an AFF4 collection.
    target_path: Base directory to write to.
    token: Token for access.
    overwrite: If True, overwrite existing files.
    max_threads: Use this many threads to do the downloads.
  """
  try:
    coll = aff4.FACTORY.Open(coll_path, "RDFValueCollection", token=token)
  except IOError:
    logging.error("%s is not a valid collection", coll_path)
    return
  tp = threadpool.ThreadPool.Factory("Downloader", max_threads)
  tp.Start()

  for aff4object_summary in coll:
    args = (aff4object_summary.urn, target_path, token, overwrite)
    tp.AddTask(target=CopyAFF4ToLocal, args=args,
               name="Downloader")


def CopyAFF4ToLocal(aff4_urn, target_dir, token=None, overwrite=False):
  """Copy an AFF4 object that supports a read interface to local filesystem.

  Args:
    aff4_urn: URN of thing to copy.
    target_dir: Directory to copy the file to.
    token: Auth token.
    overwrite: If True overwrite the file if it exists.

  By default file will only be overwritten if file size differs.
  """
  try:
    fd = aff4.FACTORY.Open(aff4_urn, "AFF4Stream", token=token)
    filepath = os.path.join(target_dir, str(fd.urn))
    if not os.path.isfile(filepath):
      if not os.path.isdir(os.path.dirname(filepath)):
        # Ensure directory exists.
        os.makedirs(os.path.dirname(filepath))
      DownloadFile(fd, filepath)
    elif (os.stat(filepath)[stat.ST_SIZE] != fd.Get(fd.Schema.SIZE) or
          overwrite):
      # We should overwrite because user said, or file sizes differ.
      DownloadFile(fd, filepath)
    else:
      logging.info("File %s exists, skipping", filepath)
  except IOError as e:
    logging.error("Failed to read %s due to %s", filepath, e)
    raise
