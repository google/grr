#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Utils exporting data from AFF4 to the rest of the world."""

import os
import stat

import logging

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import serialize
from grr.lib import threadpool
from grr.lib import utils


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
  count = 0

  data_buffer = file_obj.Read(buffer_size)
  while data_buffer:
    target_file.write(data_buffer)
    data_buffer = file_obj.Read(buffer_size)
    count += 1
    if not count % 3:
      logging.info("Downloading: %s: %s done", file_obj.urn,
                   utils.FormatNumberAsString(count*buffer_size))
  target_file.close()


def RecursiveDownload(dir_obj, target_dir, depth=10, overwrite=False):
  """Recursively downloads a file entry to the target path.

  Args:
    dir_obj: An aff4 object that contains children.
    target_dir: Full path of the directory to write to.
    depth: Depth to download to. 1 means just the directory itself.
    overwrite: Should we overwrite files that exist.
  """
  if not isinstance(dir_obj, aff4.AFF4Volume):
    return
  for sub_file_entry in dir_obj.OpenChildren():
    path_elements = [target_dir]
    sub_target_dir = u"/".join(path_elements)
    try:
      # Any file-like object with data in AFF4 should inherit AFF4Stream.
      if isinstance(sub_file_entry, aff4.AFF4Stream):
        CopyAFF4ToLocal(sub_file_entry.urn, sub_target_dir,
                        overwrite=overwrite, token=sub_file_entry.token)
      elif "Container" in sub_file_entry.behaviours:
        if depth <= 1:  # Don't go any deeper.
          continue
        if not os.path.isdir(sub_target_dir):
          os.makedirs(sub_target_dir)
        RecursiveDownload(sub_file_entry, sub_target_dir, overwrite=overwrite,
                          depth=depth-1)
    except IOError:
      logging.exception("Unable to download %s", sub_file_entry.urn)
    finally:
      sub_file_entry.Close()


def DownloadCollection(coll_path, target_path, token=None, overwrite=False,
                       dump_client_info=False, max_threads=10):
  """Iterate through a Collection object downloading all files.

  Args:
    coll_path: Path to an AFF4 collection.
    target_path: Base directory to write to.
    token: Token for access.
    overwrite: If True, overwrite existing files.
    dump_client_info: If True, this will detect client paths, and dump a yaml
      version of the client object to the root path. This is useful for seeing
      the hostname/users of the machine the client id refers to.
    max_threads: Use this many threads to do the downloads.
  """
  completed_clients = set()
  try:
    coll = aff4.FACTORY.Open(coll_path, required_type="RDFValueCollection",
                             token=token)
  except IOError:
    logging.error("%s is not a valid collection. Typo? "
                  "Are you sure something was written to it?", coll_path)
    return
  tp = threadpool.ThreadPool.Factory("Downloader", max_threads)
  tp.Start()

  logging.info("Expecting to download %s files", coll.size)

  # Collections can include anything they want, but we only handle RDFURN and
  # StatEntry entries in this function.
  for grr_message in coll:
    # If a raw message, work out the type.
    if isinstance(grr_message, rdfvalue.GRRMessage):
      grr_message = grr_message.payload

    if isinstance(grr_message, rdfvalue.RDFURN):
      urn = grr_message
    elif isinstance(grr_message, rdfvalue.StatEntry):
      urn = rdfvalue.RDFURN(grr_message.aff4path)
    else:
      continue

    # Handle dumping client info, but only once per client.
    client_id = urn.Split()[0]
    re_match = aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(client_id)
    if dump_client_info and re_match and not client_id in completed_clients:
      args = (rdfvalue.RDFURN(client_id), target_path, token, overwrite)
      tp.AddTask(target=DumpClientYaml, args=args, name="ClientYamlDownloader")
      completed_clients.add(client_id)

    # Now queue downloading the actual files.
    args = (urn, target_path, token, overwrite)
    tp.AddTask(target=CopyAFF4ToLocal, args=args,
               name="Downloader")

  tp.Join()


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
    filepath = os.path.join(target_dir, fd.urn.Path()[1:])
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
    logging.error("Failed to read %s due to %s", aff4_urn, e)
    raise


def DumpClientYaml(client_urn, target_dir, token=None, overwrite=False):
  """Dump a yaml file containing client info."""
  fd = aff4.FACTORY.Open(client_urn, "VFSGRRClient", token=token)
  dirpath = os.path.join(target_dir, fd.urn.Split()[0])
  if not os.path.exists(dirpath):
    os.makedirs(dirpath)
  filepath = os.path.join(dirpath, "client_info.yaml")
  if not os.path.isfile(filepath) or overwrite:
    with open(filepath, "w") as out_file:
      out_file.write(serialize.YamlDumper(fd))
