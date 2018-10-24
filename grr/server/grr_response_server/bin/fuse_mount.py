#!/usr/bin/env python
"""Tool for mounting AFF4 datastore over FUSE."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import errno
import getpass
import logging
import stat
import sys


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server.flows.general import filesystem
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client

from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow_utils
from grr_response_server import server_startup
from grr_response_server.aff4_objects import standard

# Check if fuse is installed. If it's not, set it to None so we know to mock it
# out later.
try:
  # pylint: disable=g-import-not-at-top
  import fuse
  # pylint: enable=g-import-not-at-top
except (EnvironmentError, ImportError):
  # We check for ImportErrors and EnvironmentErrors since submit checks throw an
  # EnvironmentError when fuse isn't installed.
  fuse = None

flags.DEFINE_string("aff4path", "/",
                    "Path in AFF4 to use as the root of the filesystem.")

flags.DEFINE_string("mountpoint", None,
                    "Path to point at which the system should be mounted.")

flags.DEFINE_bool(
    "background", False,
    "Whether or not to run the filesystem in the background,"
    " not viewing debug information.")

flags.DEFINE_float("timeout", 30,
                   "How long to poll a flow for before giving up.")

flags.DEFINE_integer(
    "max_age_before_refresh", 60 * 5,
    "Measured in seconds. Do a client-side update if it's"
    " been this long since we last did one.")

flags.DEFINE_bool(
    "ignore_cache", False, "Disables cache completely. Takes priority over"
    " refresh_policy.")

flags.DEFINE_enum(
    "refresh_policy",
    "if_older_than_max_age", ["if_older_than_max_age", "always", "never"],
    "How to refresh the cache. Options are: always (on every"
    " client-side access), never, or, by default,"
    " if_older_than_max_age (if last accessed > max_age seconds"
    " ago).",
    type=str)

flags.DEFINE_bool(
    "force_sparse_image", False,
    "Whether to convert existing files bigger than the"
    " size threshold to new, empty AFF4SparseImages.")

flags.DEFINE_integer(
    "sparse_image_threshold", 1024 * 1024 * 1024,
    "If a client side file that's not in the datastore yet"
    " is >= than this size, then store it as a sparse image.")

flags.DEFINE_string("username", None,
                    "Username to use for client authorization check.")

flags.DEFINE_string(
    "reason", None, "Reason to use for client authorization check. This "
    "needs to match the string in your approval request.")

# The modes we'll use for aff4 objects that aren't really files.
# Taken from /etc
_DEFAULT_MODE_FILE = 33188
# Taken from /etc/passwd
_DEFAULT_MODE_DIRECTORY = 16877


class GRRFuseDatastoreOnly(object):
  """We implement the FUSE methods in this class."""

  # Directories to hide. Readdir will not return them.
  ignored_dirs = [
      # We don't want to show AFF4Index objects.
      "/index/client"
  ]

  def __init__(self, root="/", token=None):
    self.root = rdfvalue.RDFURN(root)
    self.token = token
    self.default_file_mode = _DEFAULT_MODE_FILE
    self.default_dir_mode = _DEFAULT_MODE_DIRECTORY

    try:
      logging.info("Making sure supplied aff4path actually exists....")
      self.getattr(root)
      logging.info("OK")
    except fuse.FuseOSError:
      logging.info("Supplied aff4path didn't exist!")
      raise IOError("Supplied aff4 path '%s' does not exist." % self.root)

  def MakePartialStat(self, fd):
    """Try and give a 'stat' for something not in the data store.

    Args:
      fd: The object with no stat.

    Returns:
      A dictionary corresponding to what we'll say the 'stat' is
      for objects which are not actually files, so have no OS level stat.

    """

    is_dir = "Container" in fd.behaviours

    return {
        "pathspec": fd.Get(fd.Schema.PATHSPEC, ""),
        "st_atime": fd.Get(fd.Schema.LAST, 0),
        "st_blksize": 0,
        "st_blocks": 0,
        "st_ctime": 0,
        "st_dev": 0,
        "st_gid": 0,
        "st_ino": 0,
        "st_mode": self.default_dir_mode if is_dir else self.default_file_mode,
        "st_mtime": 0,
        "st_nlink": 0,
        "st_rdev": 0,
        "st_size": fd.Get(fd.Schema.SIZE, 0),
        "st_uid": 0
    }

  def _IsDir(self, path):
    """True if and only if the path has the directory bit set in its mode."""
    return stat.S_ISDIR(int(self.getattr(path)["st_mode"]))

  def Readdir(self, path, fh=None):
    """Reads a directory given by path.

    Args:
      path: The path to list children of.
      fh: A file handler. Not used.

    Yields:
      A generator of filenames.

    Raises:
      FuseOSError: If we try and list a file.

    """
    del fh

    # We can't read a path if it's a file.
    if not self._IsDir(path):
      raise fuse.FuseOSError(errno.ENOTDIR)

    fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)

    children = fd.ListChildren()

    # Make these special directories unicode to be consistent with the rest of
    # aff4.
    for directory in [u".", u".."]:
      yield directory

    # ListChildren returns a generator, so we do the same.
    for child in children:
      # Filter out any directories we've chosen to ignore.
      if child.Path() not in self.ignored_dirs:
        yield child.Basename()

  def Getattr(self, path, fh=None):
    """Performs a stat on a file or directory.

    Args:
      path: The path to stat.
      fh: A file handler. Not used.

    Returns:
      A dictionary mapping st_ names to their values.

    Raises:
      FuseOSError: When a path is supplied that grr doesn't know about, ie an
      invalid file path.
      ValueError: If an empty path is passed. (The empty string, when passed to
      self.root.Add, returns a path for aff4:/, the root directory, which is not
      the behaviour we want.)
    """
    del fh

    if not path:
      raise fuse.FuseOSError(errno.ENOENT)

    if path != self.root:
      full_path = self.root.Add(path)
    else:
      full_path = path

    fd = aff4.FACTORY.Open(full_path, token=self.token)

    # The root aff4 path technically doesn't exist in the data store, so
    # it is a special case.
    if full_path == "/":
      return self.MakePartialStat(fd)

    fd = aff4.FACTORY.Open(full_path, token=self.token)
    # Grab the stat according to aff4.
    aff4_stat = fd.Get(fd.Schema.STAT)

    # If the Schema for the object has a STAT attribute, go ahead and return
    # it as a dictionary.
    if aff4_stat:
      return aff4_stat.AsDict()

    # If the object didn't have a stored stat, we figure out if it is a special
    # grr object, or just doesn't exist.

    # We now check if the aff4 object actually has a row in the data store.
    # This prevents us from being able to cd to directories that don't exist,
    # since such directories have a newly-created empty AFF4Object,
    # but no row in the data store. Anything that is a
    # row in the data store will have a LAST attribute, so we check that.
    elif fd.Get(fd.Schema.LAST) is None:
      # We raise the "no such file or directory" error.
      raise fuse.FuseOSError(errno.ENOENT)
    else:
      # This is an object that exists in the datastore, but has no STAT, so we
      # don't know how to handle it.
      pass

    # If the object was in the data store, but didn't have a stat, we just
    # try and guess some sensible values.
    return self.MakePartialStat(fd)

  def Read(self, path, length=None, offset=0, fh=None):
    """Reads data from a file.

    Args:
      path: The path to the file to read.
      length: How many bytes to read.
      offset: Offset in bytes from which reading should start.
      fh: A file handler. Not used.

    Returns:
      A string containing the file contents requested.

    Raises:
      FuseOSError: If we try and read a directory or if we try and read an
      object that doesn't support reading.

    """
    del fh

    if self._IsDir(path):
      raise fuse.FuseOSError(errno.EISDIR)

    fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)

    # If the object has Read() and Seek() methods, let's use them.
    if all((hasattr(fd, "Read"), hasattr(fd, "Seek"), callable(fd.Read),
            callable(fd.Seek))):
      # By default, read the whole file.
      if length is None:
        length = fd.Get(fd.Schema.SIZE)

      fd.Seek(offset)
      return fd.Read(length)
    else:
      # If we don't have Read/Seek methods, we probably can't read this object.
      raise fuse.FuseOSError(errno.EIO)

  def RaiseReadOnlyError(self):
    """Raise an error complaining that the file system is read-only."""
    raise fuse.FuseOSError(errno.EROFS)

  # pylint: disable=invalid-name
  def mkdir(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def symlink(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def rename(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def link(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def write(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def truncate(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def create(self, *unused_args, **unused_kwargs):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  # pylint: enable=unused-argument,invalid-name

  # FUSE expects the names of the functions to be standard
  # filesystem function style (all lower case), so we set them so here.

  read = utils.Proxy("Read")
  readdir = utils.Proxy("Readdir")
  getattr = utils.Proxy("Getattr")


class GRRFuse(GRRFuseDatastoreOnly):
  """Interacts with the GRR clients to refresh data in the datastore."""

  def __init__(self,
               root="/",
               token=None,
               max_age_before_refresh=None,
               ignore_cache=False,
               force_sparse_image=False,
               sparse_image_threshold=1024**3,
               timeout=flow_utils.DEFAULT_TIMEOUT):
    """Create a new FUSE layer at the specified aff4 path.

    Args:
      root: String aff4 path for where we'd like to mount the FUSE layer.

      token: Datastore access token.

      max_age_before_refresh: How out of date our cache is. Specifically, if the
      time since we last did a client-side update of an aff4 object is greater
      than this value, we'll run a flow on the client and update that object.

      ignore_cache: If true, always refresh data from the client. Overrides
      max_age_before_refresh.

      force_sparse_image: Whether to try and store every file bigger than the
      size threshold as a sparse image, regardless of whether we've already got
      data for it.

      sparse_image_threshold: If a new file is >= this size, store it
      as an empty AFF4SparseImage.

      timeout: How long to wait for a client to finish running a flow, maximum.

    """

    self.size_threshold = sparse_image_threshold
    self.force_sparse_image = force_sparse_image
    self.timeout = timeout

    if ignore_cache:
      max_age_before_refresh = datetime.timedelta(0)

    # Cache expiry can be given as a datetime.timedelta object, but if
    # it is not we'll use the seconds specified as a flag.
    if max_age_before_refresh is None:
      self.max_age_before_refresh = datetime.timedelta(
          seconds=flags.FLAGS.max_age_before_refresh)
    else:
      self.max_age_before_refresh = max_age_before_refresh

    super(GRRFuse, self).__init__(root, token)

  def DataRefreshRequired(self, path=None, last=None):
    """True if we need to update this path from the client.

    Args:
      path: The path relative to the root to check freshness of.
      last: An aff4:last attribute to check freshness of.

      At least one of path or last must be supplied.

    Returns:
      True if the path hasn't been updated in the last
      self.max_age_before_refresh seconds, else False.

    Raises:
      type_info.TypeValueError: If no arguments are supplied.
    """

    # If we didn't get given a last attribute, use the path to get one from the
    # object.
    if last is None:
      if path is None:
        # If we didn't get a path either, we can't do anything.
        raise type_info.TypeValueError("Either 'path' or 'last' must"
                                       " be supplied as an argument.")

      fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)
      # We really care about the last time the stat was updated, so we use
      # this instead of the LAST attribute, which is the last time anything
      # was updated about the object.
      stat_obj = fd.Get(fd.Schema.STAT)
      if stat_obj:
        last = stat_obj.age
      else:
        last = rdfvalue.RDFDatetime(0)

    # If the object doesn't even have a LAST attribute by this point,
    # we say it hasn't been accessed within the cache expiry time.
    if last is None:
      return True
    last = last.AsDatetime()

    # Remember to use UTC time, since that's what the datastore uses.
    return datetime.datetime.utcnow() - last > self.max_age_before_refresh

  def _RunAndWaitForVFSFileUpdate(self, path):
    """Runs a flow on the client, and waits for it to finish."""

    client_id = rdf_client.GetClientURNFromPath(path)

    # If we're not actually in a directory on a client, no need to run a flow.
    if client_id is None:
      return

    flow_utils.UpdateVFSFileAndWait(
        client_id,
        token=self.token,
        vfs_file_urn=self.root.Add(path),
        timeout=self.timeout)

  def Readdir(self, path, fh=None):
    """Updates the directory listing from the client.

    Args:
      path: The path to the directory to update. Client is inferred from this.
      fh: A file handler. Not used.

    Returns:
      A list of filenames.

    """
    if self.DataRefreshRequired(path):
      self._RunAndWaitForVFSFileUpdate(path)

    return super(GRRFuse, self).Readdir(path, fh=None)

  def GetMissingChunks(self, fd, length, offset):
    """Return which chunks a file doesn't have.

    Specifically, we return a list of the chunks specified by a
    length-offset range which are not in the datastore.

    Args:
      fd: The database object to read chunks from.
      length: Length to read.
      offset: File offset to read from.

    Returns:
      A list of chunk numbers.
    """
    start_chunk = offset // fd.chunksize
    end_chunk = (offset + length - 1) // fd.chunksize

    relevant_chunks = range(start_chunk, end_chunk + 1)

    missing_chunks = set(relevant_chunks)
    for idx, metadata in iteritems(fd.ChunksMetadata(relevant_chunks)):
      if not self.DataRefreshRequired(last=metadata.get("last", None)):
        missing_chunks.remove(idx)

    return sorted(missing_chunks)

  def UpdateSparseImageIfNeeded(self, fd, length, offset):
    missing_chunks = self.GetMissingChunks(fd, length, offset)
    if not missing_chunks:
      return

    client_id = rdf_client.GetClientURNFromPath(fd.urn.Path())
    flow_utils.StartFlowAndWait(
        client_id,
        token=self.token,
        flow_name=filesystem.UpdateSparseImageChunks.__name__,
        file_urn=fd.urn,
        chunks_to_fetch=missing_chunks)

  def Read(self, path, length=None, offset=0, fh=None):
    fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)
    last = fd.Get(fd.Schema.CONTENT_LAST)
    client_id = rdf_client.GetClientURNFromPath(path)

    if not self.DataRefreshRequired(last=last, path=path):
      return super(GRRFuse, self).Read(path, length, offset, fh)

    if isinstance(fd, standard.AFF4SparseImage):
      # If we have a sparse image, update just a part of it.
      self.UpdateSparseImageIfNeeded(fd, length, offset)
      # Read the file from the datastore as usual.
      return super(GRRFuse, self).Read(path, length, offset, fh)

    # If it's the first time we've seen this path (or we're asking
    # explicitly), try and make it an AFF4SparseImage.
    if last is None or self.force_sparse_image:
      pathspec = fd.Get(fd.Schema.PATHSPEC)

      # Either makes a new AFF4SparseImage or gets the file fully,
      # depending on size.
      flow_utils.StartFlowAndWait(
          client_id,
          token=self.token,
          flow_name=filesystem.MakeNewAFF4SparseImage.__name__,
          pathspec=pathspec,
          size_threshold=self.size_threshold)

      # Reopen the fd in case it's changed to be an AFF4SparseImage
      fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)
      # If we are now a sparse image, just download the part we requested
      # from the client.
      if isinstance(fd, standard.AFF4SparseImage):
        flow_utils.StartFlowAndWait(
            client_id,
            token=self.token,
            flow_name=filesystem.FetchBufferForSparseImage.__name__,
            file_urn=self.root.Add(path),
            length=length,
            offset=offset)
    else:
      # This was a file we'd seen before that wasn't a sparse image, so update
      # it the usual way.
      self._RunAndWaitForVFSFileUpdate(path)

    # Read the file from the datastore as usual.
    return super(GRRFuse, self).Read(path, length, offset, fh)


def Usage():
  print("Needs at least --mountpoint")
  print("e.g. \n python grr/tools/fuse_mount.py "
        "--config=install_data/etc/grr-server.yaml "
        "--mountpoint=/home/%s/mntpoint" % getpass.getuser())


def main(argv):
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRR FUSE {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT,
                           "Context applied for all command line tools")
  server_startup.Init()

  if fuse is None:
    logging.fatal("""Could not start!
fusepy must be installed to run fuse_mount.py!
Try to run:
  pip install fusepy

inside your virtualenv.
""")
    sys.exit(1)

  if not flags.FLAGS.mountpoint:
    Usage()
    sys.exit(1)

  # We multiple inherit from GRRFuse and fuse.Operations. In the
  # case that fuse is present, we run the actual FUSE layer, since we have
  # fuse.Operations. In the case that fuse is not present, we have already
  # exited by now if we were run from the command line, and if we were not run
  # from the command line, we've been imported, and we run the tests using a
  # mock fuse.

  class FuseOperation(GRRFuse, fuse.Operations):
    pass

  root = flags.FLAGS.aff4path

  username = flags.FLAGS.username or getpass.getuser()
  data_store.default_token = access_control.ACLToken(
      username=username, reason=flags.FLAGS.reason or "fusemount")

  logging.info("fuse_mount.py is mounting %s at %s....", root,
               flags.FLAGS.mountpoint)

  refresh_policy = flags.FLAGS.refresh_policy

  if refresh_policy == "always":
    max_age_before_refresh = datetime.timedelta(0)
  elif refresh_policy == "never":
    # Set the max age to be the maximum possible time difference.
    max_age_before_refresh = datetime.timedelta.max
  elif refresh_policy == "if_older_than_max_age":
    max_age_before_refresh = datetime.timedelta(
        seconds=flags.FLAGS.max_age_before_refresh)
  else:
    # Otherwise, a flag outside the enum was given and the flag validator threw
    # an execption.
    pass

  fuse_operation = FuseOperation(
      root=root,
      token=data_store.default_token,
      max_age_before_refresh=max_age_before_refresh,
      ignore_cache=flags.FLAGS.ignore_cache,
      force_sparse_image=flags.FLAGS.force_sparse_image,
      sparse_image_threshold=flags.FLAGS.sparse_image_threshold,
      timeout=flags.FLAGS.timeout)

  fuse.FUSE(
      fuse_operation,
      flags.FLAGS.mountpoint,
      foreground=not flags.FLAGS.background)


if __name__ == "__main__":
  flags.StartMain(main)
