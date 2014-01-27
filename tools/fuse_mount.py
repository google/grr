#!/usr/bin/env python
"""Tool for mounting AFF4 database over FUSE."""


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
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import utils

from grr.lib.aff4_objects import standard

# We use a slightly modified version of utils.ConditionalImport, since the
# submit checks throw an EnvironmentError, not an ImportError when fuse isn't
# installed.
try:
  fuse = utils.ConditionalImport("fuse")
except EnvironmentError:
  fuse = None

flags.DEFINE_string("aff4path", None,
                    "Path in AFF4 to use as the root of the filesystem.")

flags.DEFINE_string("mountpoint", None,
                    "Path to point at which the system should be mounted.")

flags.DEFINE_bool("background", False,
                  "Whether or not to run the filesystem in the background,"
                  "not viewing debug information.")

# TODO(user): For objects that aren't strictly files, add some
# functionality rather than just leaving them as filenames. e.g. cat returns
# string representation

# The modes we'll use for aff4 objects that aren't really files
# taken from /etc
_DEFAULT_MODE_FILE = 33188
# taken from /etc/passwd
_DEFAULT_MODE_DIRECTORY = 16877


class GRRFuseDatastoreOnly(object):
  """We implement the FUSE methods in this class."""

  def __init__(self, root, token):
    self.root = rdfvalue.RDFURN(root)
    self.token = token
    self.default_file_mode = _DEFAULT_MODE_FILE
    self.default_dir_mode = _DEFAULT_MODE_DIRECTORY

    try:
      logging.info("Making sure supplied aff4path actually exists....")
      self.getattr(root)
    except fuse.FuseOSError:
      logging.info("Supplied aff4path didn't exist!")
      raise IOError("Supplied aff4 path %s does not exist." % self.root)

  def _GetDefaultStat(self, is_dir, path):
    """Get the 'stat' for something not in the data store.

    Args:
      is_dir: Whether or not the path is a directory.
      path: The path to stat

    Returns:
      a dictionary corresponding to what we'll say the 'stat' is
      for objects which are not actually files, so have no OS level stat.

    """

    return {
        "pathspec": path,
        "st_atime": 0,
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
        "st_size": 0,
        "st_uid": 0
    }

  def _IsDir(self, path):
    """True if and only if the path has the directory bit set in its mode."""
    return stat.S_ISDIR(int(self.getattr(path)["st_mode"]))

  # pylint: disable=unused-argument,invalid-name
  def readdir(self, path, fh=None):
    """Reads a directory given by path.

    Args:
      path: The path to list children of.
      fh: A file handler. Not used.

    Yields:
      A generator of filenames.

    Raises:
      FuseOSError: If path is not a directory.
    """

    # We can't read a path if it's a file.
    if not self._IsDir(path):
      raise fuse.FuseOSError(errno.ENOTDIR)

    aff4_object = aff4.FACTORY.Open(self.root.Add(path), token=self.token)

    children = aff4_object.ListChildren()

    # Make these special directories unicode to be consistent with the rest of
    # aff4.
    for directory in [u".", u".."]:
      yield directory

    # Filter out any index objects.
    children = (child for child in children if not
                isinstance(aff4.FACTORY.Open(self.root.Add(child.Path()),
                                             token=self.token),
                           standard.AFF4Index))

    # ListChildren returns a generator, so we do the same.
    for child in children:
      yield child.Basename()

  def getattr(self, path, fh=None):
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

    # The root aff4 path technically doesn't exist in the data store, so
    # it is a special case.
    if full_path == "/":
      return self._GetDefaultStat(path=full_path, is_dir=True)

    aff4_object = aff4.FACTORY.Open(full_path, token=self.token)
    # Grab the stat according to aff4.
    aff4_stat = aff4_object.Get(aff4_object.Schema.STAT)

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
    elif aff4_object.Get(aff4_object.Schema.LAST) is None:
      # We raise the "no such file or directory" error.
      logging.info("Tried to stat %s, no such file or directory.",
                   full_path)
      raise fuse.FuseOSError(errno.ENOENT)
    else:
      # This is an object that exists in the datastore, but has no STAT, so we
      # don't know how to handle it.
      logging.info("Data store had no Schema attribute for %s",
                   full_path)

    # If the object was in the data store, but didn't have a stat, we just
    # show some default values.
    is_dir = "Container" in aff4_object.behaviours
    return self._GetDefaultStat(is_dir, path)

  # pylint: enable=invalid-name

  def RaiseReadOnlyError(self):
    """Raise an error complaining that the file system is read-only."""
    raise fuse.FuseOSError(errno.EROFS)

  # pylint: disable=invalid-name

  def mkdir(self, path, mode):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def symlink(self, target, name):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def rename(self, old_name, new_name):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def link(self, target, name):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def write(self, path, buf, offset, fh):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def truncate(self, path, length, fh=None):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  def create(self, path, mode, fi=None):
    """Unimplemented on purpose. File system is read-only."""
    self.RaiseReadOnlyError()

  # pylint: enable=unused-argument,invalid-name


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
    logging.critical("fusepy must be installed to run fuse_mount.py")
    sys.exit(1)

  if not (flags.FLAGS.aff4path and flags.FLAGS.mountpoint):
    Usage()
    sys.exit(1)

  # We multiple inherit from GRRFuseDatastoreOnly and fuse.Operations. In the
  # case that fuse is present, we run the actual FUSE layer, since we have
  # fuse.Operations. In the case that fuse is not present, we have already
  # exited by now if we were run from the command line, and if we were not run
  # from the command line, we've been imported, and we run the tests using a
  # mock fuse.

  class FuseOperation(GRRFuseDatastoreOnly, fuse.Operations):
    pass

  data_store.default_token = rdfvalue.ACLToken(username=getpass.getuser(),
                                               reason="fusemount")
  root = flags.FLAGS.aff4path

  logging.info("Fuse mounting %s at %s....", root, flags.FLAGS.mountpoint)
  fuse.FUSE(FuseOperation(root=root,
                          token=data_store.default_token),
            flags.FLAGS.mountpoint,
            foreground=not flags.FLAGS.background)


if __name__ == "__main__":
  flags.StartMain(main)
