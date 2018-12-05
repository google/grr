#!/usr/bin/env python
"""Utils exporting data from AFF4 to the rest of the world."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import stat
import time

import queue

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import sequential_collection
from grr_response_server import serialize
from grr_response_server import threadpool
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard
from grr_response_server.flows.general import collectors
from grr_response_server.hunts import results

BUFFER_SIZE = 16 * 1024 * 1024

THREADPOOL_JOIN_TIMEOUT = 1200


def GetAllClients(token=None):
  """Return a list of all client urns."""
  index = client_index.CreateClientIndex(token=token)
  return index.LookupClients(["."])


class IterateAllClientUrns(object):
  """Class to iterate over all URNs."""

  THREAD_POOL_NAME = "ClientUrnIter"
  QUEUE_TIMEOUT = 30

  def __init__(self, func=None, max_threads=10, token=None):
    """Iterate over all clients in a threadpool.

    Args:
      func: A function to call with each client urn.
      max_threads: Number of threads to use.
      token: Auth token.

    Raises:
      ValueError: If function not specified.
    """
    self.thread_pool = threadpool.ThreadPool.Factory(self.THREAD_POOL_NAME,
                                                     max_threads)
    self.thread_pool.Start()
    self.token = token
    self.func = func
    self.broken_subjects = []  # Entries that are broken or fail to run.

    self.out_queue = queue.Queue()

  def GetInput(self):
    """Yield client urns."""
    clients = GetAllClients(token=self.token)
    logging.debug("Got %d clients", len(clients))
    return clients

  def Run(self):
    """Run the iteration."""
    count = 0
    for count, input_data in enumerate(self.GetInput()):
      if count % 2000 == 0:
        logging.debug("%d processed.", count)
      args = (input_data, self.out_queue, self.token)
      self.thread_pool.AddTask(
          target=self.IterFunction, args=args, name=self.THREAD_POOL_NAME)

    while count >= 0:
      try:
        # We only use the timeout to wait if we got to the end of the Queue but
        # didn't process everything yet.
        out = self.out_queue.get(timeout=self.QUEUE_TIMEOUT, block=True)
        if out:
          yield out
          count -= 1
      except queue.Empty:
        break

    # Join and stop to clean up the threadpool.
    self.thread_pool.Stop(join_timeout=THREADPOOL_JOIN_TIMEOUT)

  def IterFunction(self, *args):
    """Function to run on each input. This can be overridden."""
    self.func(*args)


class IterateAllClients(IterateAllClientUrns):
  """Class to iterate over all GRR Client objects."""

  def __init__(self, max_age, client_chunksize=25, **kwargs):
    """Iterate over all clients in a threadpool.

    Args:
      max_age: Maximum age in seconds of clients to check.
      client_chunksize: A function to call with each client urn.
      **kwargs: Arguments passed to init.
    """
    super(IterateAllClients, self).__init__(**kwargs)
    self.client_chunksize = client_chunksize
    self.max_age = max_age

  def GetInput(self):
    """Yield client urns."""
    client_list = GetAllClients(token=self.token)
    logging.debug("Got %d clients", len(client_list))
    for client_group in collection.Batch(client_list, self.client_chunksize):
      for fd in aff4.FACTORY.MultiOpen(
          client_group,
          mode="r",
          aff4_type=aff4_grr.VFSGRRClient,
          token=self.token):
        if isinstance(fd, aff4_grr.VFSGRRClient):
          # Skip if older than max_age
          oldest_time = (time.time() - self.max_age) * 1e6
        if fd.Get(aff4_grr.VFSGRRClient.SchemaCls.PING) >= oldest_time:
          yield fd


def DownloadFile(file_obj, target_path, buffer_size=BUFFER_SIZE):
  """Download an aff4 file to the local filesystem overwriting it if it exists.

  Args:
    file_obj: An aff4 object that supports the file interface (Read, Seek)
    target_path: Full path of file to write to.
    buffer_size: Read in chunks this size.
  """
  logging.info(u"Downloading: %s to: %s", file_obj.urn, target_path)

  target_file = open(target_path, "wb")
  file_obj.Seek(0)
  count = 0

  data_buffer = file_obj.Read(buffer_size)
  while data_buffer:
    target_file.write(data_buffer)
    data_buffer = file_obj.Read(buffer_size)
    count += 1
    if not count % 3:
      logging.debug(u"Downloading: %s: %s done", file_obj.urn,
                    utils.FormatNumberAsString(count * buffer_size))
  target_file.close()


def RecursiveDownload(dir_obj,
                      target_dir,
                      max_depth=10,
                      depth=1,
                      overwrite=False,
                      max_threads=10):
  """Recursively downloads a file entry to the target path.

  Args:
    dir_obj: An aff4 object that contains children.
    target_dir: Full path of the directory to write to.
    max_depth: Depth to download to. 1 means just the directory itself.
    depth: Current depth of recursion.
    overwrite: Should we overwrite files that exist.
    max_threads: Use this many threads to do the downloads.
  """
  if not isinstance(dir_obj, aff4.AFF4Volume):
    return

  # Reuse the same threadpool as we call recursively.
  thread_pool = threadpool.ThreadPool.Factory("Downloader", max_threads)
  thread_pool.Start()

  for sub_file_entry in dir_obj.OpenChildren():
    path_elements = [target_dir]
    sub_target_dir = u"/".join(path_elements)
    try:
      # Any file-like object with data in AFF4 should inherit AFF4Stream.
      if isinstance(sub_file_entry, aff4.AFF4Stream):
        args = (sub_file_entry.urn, sub_target_dir, sub_file_entry.token,
                overwrite)
        thread_pool.AddTask(
            target=CopyAFF4ToLocal, args=args, name="Downloader")
      elif "Container" in sub_file_entry.behaviours:
        if depth >= max_depth:  # Don't go any deeper.
          continue
        try:
          os.makedirs(sub_target_dir)
        except OSError:
          pass
        RecursiveDownload(
            sub_file_entry,
            sub_target_dir,
            overwrite=overwrite,
            depth=depth + 1)
    except IOError:
      logging.exception("Unable to download %s", sub_file_entry.urn)
    finally:
      sub_file_entry.Close()

  # Join and stop the threadpool.
  if depth <= 1:
    thread_pool.Stop(join_timeout=THREADPOOL_JOIN_TIMEOUT)


def _OpenCollectionPath(coll_path):
  """Tries to open various types of collections at the given path."""
  hunt_collection = results.HuntResultCollection(coll_path)
  if hunt_collection and hunt_collection[0].payload:
    return hunt_collection

  indexed_collection = sequential_collection.GeneralIndexedCollection(coll_path)
  if indexed_collection:
    return indexed_collection


def DownloadCollection(coll_path,
                       target_path,
                       token=None,
                       overwrite=False,
                       dump_client_info=False,
                       flatten=False,
                       max_threads=10):
  """Iterate through a Collection object downloading all files.

  Args:
    coll_path: Path to an AFF4 collection.
    target_path: Base directory to write to.
    token: Token for access.
    overwrite: If True, overwrite existing files.
    dump_client_info: If True, this will detect client paths, and dump a yaml
      version of the client object to the root path. This is useful for seeing
      the hostname/users of the machine the client id refers to.
    flatten: If True, produce a "files" flat folder with links to all the found
      files.
    max_threads: Use this many threads to do the downloads.
  """
  completed_clients = set()
  coll = _OpenCollectionPath(coll_path)
  if coll is None:
    logging.error(
        "%s is not a valid collection. Typo? "
        "Are you sure something was written to it?", coll_path)
    return

  thread_pool = threadpool.ThreadPool.Factory("Downloader", max_threads)
  thread_pool.Start()

  # Extract the client id from the source urn. This code makes me
  # quite sad but there is just no concept of passing a client id in
  # the export tool (and this would be unsafe anyways since the user
  # could then download files from arbitrary machines easily). The
  # export tool is on the way to deprecation so we decided to do this
  # instead of fixing the obsolete code.
  try:
    collection_urn = coll.collection_id
  except AttributeError:
    collection_urn = coll.urn

  try:
    original_client_id = rdf_client.ClientURN(collection_urn.Split()[0])
  except IOError:
    original_client_id = None

  logging.info("Expecting to download %s files", len(coll))

  # Collections can include anything they want, but we only handle RDFURN and
  # StatEntry entries in this function.
  for grr_message in coll:
    source = None
    # If a raw message, work out the type.
    if isinstance(grr_message, rdf_flows.GrrMessage):
      source = grr_message.source
      grr_message = grr_message.payload

    if isinstance(grr_message, rdfvalue.RDFURN):
      urn = grr_message
    elif isinstance(grr_message, rdf_client_fs.StatEntry):
      urn = rdfvalue.RDFURN(grr_message.AFF4Path(source or original_client_id))
    elif isinstance(grr_message, rdf_file_finder.FileFinderResult):
      urn = rdfvalue.RDFURN(
          grr_message.stat_entry.AFF4Path(source or original_client_id))
    elif isinstance(grr_message, collectors.ArtifactFilesDownloaderResult):
      if grr_message.HasField("downloaded_file"):
        urn = grr_message.downloaded_file.AFF4Path(source or original_client_id)
      else:
        continue
    elif isinstance(grr_message, rdfvalue.RDFBytes):
      try:
        os.makedirs(target_path)
      except OSError:
        pass
      try:
        # We just dump out bytes and carry on.
        client_id = source.Split()[0]
        with open(os.path.join(target_path, client_id), "wb") as fd:
          fd.write(str(grr_message))
      except AttributeError:
        pass
      continue
    else:
      continue

    # Handle dumping client info, but only once per client.
    if dump_client_info:
      client_id = urn.Split()[0]
      re_match = aff4_grr.VFSGRRClient.CLIENT_ID_RE.match(client_id)
      if re_match and client_id not in completed_clients:
        args = (rdf_client.ClientURN(client_id), target_path, token, overwrite)
        thread_pool.AddTask(
            target=DumpClientYaml, args=args, name="ClientYamlDownloader")
        completed_clients.add(client_id)

    # Now queue downloading the actual files.
    args = (urn, target_path, token, overwrite)
    if flatten:
      target = CopyAndSymlinkAFF4ToLocal
    else:
      target = CopyAFF4ToLocal
    thread_pool.AddTask(target=target, args=args, name="Downloader")

  # Join and stop the threadpool.
  thread_pool.Stop(join_timeout=THREADPOOL_JOIN_TIMEOUT)


def CopyAFF4ToLocal(aff4_urn, target_dir, token=None, overwrite=False):
  """Copy an AFF4 object that supports a read interface to local filesystem.

  Args:
    aff4_urn: URN of thing to copy.
    target_dir: Directory to copy the file to.
    token: Auth token.
    overwrite: If True overwrite the file if it exists.

  Returns:
    If aff4_urn points to a file, returns path to the downloaded file.
    Otherwise returns None.

  By default file will only be overwritten if file size differs.
  """
  try:
    fd = aff4.FACTORY.Open(aff4_urn, token=token)
    filepath = os.path.join(target_dir, fd.urn.Path()[1:])

    # If urn points to a directory, just create it.
    if isinstance(fd, standard.VFSDirectory):
      try:
        os.makedirs(filepath)
      except OSError:
        pass

      return None
    # If urn points to a file, download it.
    elif isinstance(fd, aff4.AFF4Stream):
      if not os.path.isfile(filepath):
        try:
          # Ensure directory exists.
          os.makedirs(os.path.dirname(filepath))
        except OSError:
          pass
        DownloadFile(fd, filepath)
      elif (os.stat(filepath)[stat.ST_SIZE] != fd.Get(fd.Schema.SIZE) or
            overwrite):
        # We should overwrite because user said, or file sizes differ.
        DownloadFile(fd, filepath)
      else:
        logging.info("File %s exists, skipping", filepath)

      return filepath
    else:
      raise ValueError("Opened urn is neither a downloaded file nor a "
                       "directory: %s" % aff4_urn)

  except IOError as e:
    logging.exception("Failed to read %s due to %s", aff4_urn, e)
    raise


def CopyAndSymlinkAFF4ToLocal(aff4_urn, target_dir, token=None,
                              overwrite=False):
  path = CopyAFF4ToLocal(aff4_urn, target_dir, token=token, overwrite=overwrite)
  if path:
    files_output_dir = os.path.join(target_dir, "files")
    try:
      os.makedirs(files_output_dir)
    except OSError:
      pass

    unique_name = "_".join(aff4_urn.Split())
    symlink_path = os.path.join(files_output_dir, unique_name)
    try:
      os.symlink(path, symlink_path)
    except OSError:
      logging.exception("Can't create symlink to a file: %s -> %s",
                        symlink_path, path)


def DumpClientYaml(client_urn, target_dir, token=None, overwrite=False):
  """Dump a yaml file containing client info."""
  fd = aff4.FACTORY.Open(client_urn, aff4_grr.VFSGRRClient, token=token)
  dirpath = os.path.join(target_dir, fd.urn.Split()[0])
  try:
    # Due to threading this can actually be created by another thread.
    os.makedirs(dirpath)
  except OSError:
    pass
  filepath = os.path.join(dirpath, "client_info.yaml")
  if not os.path.isfile(filepath) or overwrite:
    with open(filepath, "wb") as out_file:
      out_file.write(serialize.YamlDumper(fd))
