#!/usr/bin/env python
"""Tool for mounting AFF4 datastore over FUSE."""

import datetime
import errno
import getpass
import stat
import sys


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

import logging


from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import type_info
from grr.lib import utils

from grr.lib.aff4_objects import security

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

flags.DEFINE_string("aff4path", None,
                    "Path in AFF4 to use as the root of the filesystem.")

flags.DEFINE_string("mountpoint", None,
                    "Path to point at which the system should be mounted.")

flags.DEFINE_bool("background", False,
                  "Whether or not to run the filesystem in the background,"
                  "not viewing debug information.")

flags.DEFINE_float("timeout", 30,
                   "How long to poll a flow for before giving up.")

flags.DEFINE_integer("max_age_before_refresh", 60*5,
                     "Measured in seconds. Do a client-side update if it's "
                     "been this long since we last did one.")

flags.DEFINE_bool("ignore_cache", False,
                  "Disables cache completely. Takes priority over "
                  "refresh_policy.")

flags.DEFINE_enum("refresh_policy", "if_older_than_max_age",
                  ["if_older_than_max_age", "always", "never"],
                  "How to refresh the cache. Options are: always (on every "
                  "client-side access), never, or, by default, "
                  "if_older_than_max_age (if last accessed > max_age seconds "
                  "ago).", type=str)

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
        "pathspec": fd.urn.Path(),
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

  # pylint: disable=unused-argument
  def Readdir(self, path, fh=None):
    """Reads a directory given by path.

    Args:
      path: The path to list children of.
      fh: A file handler. Not used.

    Yields:
      A generator of filenames.

    """
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

    if not path:
      raise fuse.FuseOSError(errno.ENOENT)

    if path != self.root.Path():
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

    """
    if self._IsDir(path):
      raise fuse.FuseOSError(errno.EISDIR)

    fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token)

    # If the object has Read() and Seek() methods, let's use them.
    if all((hasattr(fd, "Read"),
            hasattr(fd, "Seek"),
            callable(fd.Read),
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

  def __init__(self, root="/", token=None, max_age_before_refresh=None,
               ignore_cache=False, timeout=flow_utils.DEFAULT_TIMEOUT):
    """Create a new FUSE layer at the specified aff4 path.

    Args:
      root: String aff4 path for where we'd like to mount the FUSE layer.
      token: Datastore access token.
      max_age_before_refresh: How out of date our cache is. Specifically, if the
      time since we last did a client-side update of an aff4 object is greater
      than this value, we'll run a flow on the client and update that object.
      ignore_cache: If true, always refresh data from the client. Overrides
      max_age_before_refresh.
      timeout: How long to wait for a client to finish running a flow, maximum.


    """

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

  def DataRefreshRequired(self, path):
    """True if we need to update this path from the client."""
    fd = aff4.FACTORY.Open(self.root.Add(path), token=self.token,
                           ignore_cache=True)

    last = fd.Get(fd.Schema.LAST)
    # If the object doesn't even have a LAST attribute, we say it hasn't been
    # accessed within the cache expiry time.
    if last is None:
      return True
    last = last.AsDatetime()

    # Remember to use UTC time, since that's what the datastore uses.
    if datetime.datetime.utcnow() - last > self.max_age_before_refresh:
      logging.debug("%s last updated at %s, refreshing cache...", path,
                    last)
      return True
    return False

  @staticmethod
  def GetClientURNFromPath(path):
    """Extracts the Client id from the path, if it is present."""

    # Make sure that the first component of the path looks like a client.
    try:
      return rdfvalue.ClientURN(path.split("/")[1])
    except (type_info.TypeValueError, IndexError):
      return None

  def _RunAndWaitForVFSFileUpdate(self, path):
    """Runs a flow on the client, and waits for it to finish."""

    client_id = self.GetClientURNFromPath(path)

    # If we're not actually in a directory on a client, no need to run a flow.
    if client_id is None:
      return

    flow_utils.UpdateVFSFileAndWait(
        client_id,
        token=self.token,
        vfs_file_urn=rdfvalue.RDFURN(path),
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

  def Read(self, path, length=None, offset=0, fh=None):

    if self.DataRefreshRequired(path):
      self._RunAndWaitForVFSFileUpdate(path)

    return super(GRRFuse, self).Read(path, length, offset, fh)


def Usage():
  print "Needs at least --aff4path and --mountpoint"
  print ("e.g. \n python grr/tools/fuse_mount.py"
         "--config=grr/config/grr-server.yaml --aff4path=aff4:/"
         "--mountpoint=/home/%s/mntpoint"
         % getpass.getuser())


def main(unused_argv):
  config_lib.CONFIG.AddContext(
      "Commandline Context",
      "Context applied for all command line tools")
  startup.Init()

  if fuse is None:
    logging.critical("""Could not start!
fusepy must be installed to runfuse_mount.py!
Try:
  sudo pip install fusepy""")
    sys.exit(1)

  if not (flags.FLAGS.aff4path and flags.FLAGS.mountpoint):
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

  username = getpass.getuser()

  data_store.default_token = rdfvalue.ACLToken(username=username,
                                               reason="fusemount")
  # If we're mounting inside a client, check to see if we have access to that
  # client.
  client_id = GRRFuse.GetClientURNFromPath(root)
  if client_id is not None:
    token = security.Approval.GetApprovalForObject(
        client_id,
        token=data_store.default_token,
        username=username)
  else:
    token = data_store.default_token

  logging.info("fuse_mount.py is mounting %s at %s....", root,
               flags.FLAGS.mountpoint)

  refresh_policy = flags.FLAGS.refresh_policy

  if refresh_policy == "always":
    max_age_before_refresh = datetime.timedelta(0)
  elif refresh_policy == "never":
    # Set the max age to be the maximum possible time difference.
    max_age_before_refresh = datetime.timedelta(datetime.timedelta.max)
  elif refresh_policy == "if_older_than_max_age":
    max_age_before_refresh = datetime.timedelta(
        flags.FLAGS.max_age_before_refresh)
  else:
    # Otherwise, a flag outside the enum was given and the flag validator threw
    # an execption.
    pass

  fuse.FUSE(FuseOperation(root=root,
                          token=token,
                          max_age_before_refresh=max_age_before_refresh,
                          ignore_cache=flags.FLAGS.ignore_cache,
                          timeout=flags.FLAGS.timeout),
            flags.FLAGS.mountpoint,
            foreground=not flags.FLAGS.background)

if __name__ == "__main__":
  flags.StartMain(main)
