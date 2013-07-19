#!/usr/bin/env python
"""Create and delete GRR temporary files.

Utilities for working with GRR temp files.
"""



import os
import stat
import sys
import tempfile
import threading


from grr.client import actions
from grr.client import client_utils
from grr.lib import config_lib
from grr.lib import rdfvalue


config_lib.DEFINE_string(
    name="Client.tempfile_prefix",
    help="Prefix to use for temp files created by GRR.",
    default="tmp%(Client.name)")

config_lib.DEFINE_string(
    name="Client.tempdir",
    help="Default temporary directory to use on the client.",
    default="/var/tmp/grr/")


class Error(Exception):
  """Base error class."""


class ErrorBadPath(Error):
  """OS file path errors."""


class ErrorNotTempFile(Error):
  """Attempt to delete a file that isn't a GRR tempfile."""


def CreateGRRTempFile(directory=None, lifetime=0, suffix=""):
  """Open file with GRR prefix in directory to allow easy deletion.

  Missing parent dirs will be created. If an existing directory is specified
  its permissions won't be modified to avoid breaking system functionality.
  Permissions on the destination file will be set to root/SYSTEM rw.

  On windows the file is created, then permissions are set.  So there is
  potentially a race condition where the file is readable by other users.  If
  the caller doesn't specify a directory on windows we use the directory we are
  executing from as a safe default.

  If lifetime is specified a housekeeping thread is created to delete the file
  after lifetime seconds.  Files won't be deleted by default.

  Args:
    directory: string representing absolute directory where file should be
               written. If None, use 'tmp' under the directory we're running
               from.
    lifetime: time in seconds before we should delete this tempfile.
    suffix: optional suffix to use for the temp file
  Returns:
    Python file object
  Raises:
    OSError: on permission denied
    ErrorBadPath: if path is not absolute
    ValueError: if Client.tempfile_prefix is undefined in the config.
  """
  if not directory:
    directory = config_lib.CONFIG["Client.tempdir"]

  if not os.path.isabs(directory):
    raise ErrorBadPath("Directory %s is not absolute" % directory)

  if not os.path.isdir(directory):
    os.makedirs(directory)

    # Make directory 700 before we write the file
    if sys.platform == "win32":
      client_utils.WinChmod(directory,
                            ["FILE_GENERIC_READ", "FILE_GENERIC_WRITE"])
    else:
      os.chmod(directory, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

  prefix = config_lib.CONFIG.Get("Client.tempfile_prefix")
  outfile = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix,
                                        dir=directory, delete=False)

  if lifetime > 0:
    cleanup = threading.Timer(lifetime, DeleteGRRTempFile, (outfile.name,))
    cleanup.start()

  # Fix perms on the file, since this code is used for writing executable blobs
  # we apply RWX.
  if sys.platform == "win32":
    client_utils.WinChmod(outfile.name, ["FILE_ALL_ACCESS"],
                          user="SYSTEM")
  else:
    os.chmod(outfile.name, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

  return outfile


def DeleteGRRTempFile(path):
  """Delete a GRR temp file.

  To limit possible damage the path must be absolute and only files beginning
  with Client.tempfile_prefix can be deleted.

  Args:
    path: path string to file to be deleted.

  Raises:
    OSError: Permission denied, or file not found.
    ErrorBadPath: Path must be absolute
    ErrorNotTempFile: Filename must start with Client.tempfile_prefix
  """
  if not os.path.isabs(path):
    raise ErrorBadPath("Path must be absolute")

  prefix = config_lib.CONFIG.Get("Client.tempfile_prefix")
  if not os.path.basename(path).startswith(prefix):
    msg = "Can't delete %s, filename must start with %s"
    raise ErrorNotTempFile(msg % (path, prefix))

  if os.path.exists(path):
    os.remove(path)


class DeleteGRRTempFiles(actions.ActionPlugin):
  """Delete all the GRR temp files in a directory."""
  in_rdfvalue = rdfvalue.PathSpec
  out_rdfvalue = rdfvalue.LogMessage

  def Run(self, args):
    """Delete all the GRR temp files in path.

    If path is a directory, look in the top level for filenames beginning with
    Client.tempfile_prefix, and delete them.

    If path is a regular file and starts with Client.tempfile_prefix delete it.

    Args:
      args: pathspec pointing to directory containing temp files to be
            deleted, or a single file to be deleted.
    Returns:
      deleted: array of filename strings that were deleted
    Raises:
      ErrorBadPath: if path doesn't exist or is not a regular file or directory
    """
    if args.path:
      path = args.path
    else:
      path = config_lib.CONFIG["Client.tempdir"]

    deleted = []
    if os.path.isdir(path):
      for filename in os.listdir(path):
        abs_filename = os.path.join(path, filename)

        try:
          DeleteGRRTempFile(abs_filename)
          deleted.append(abs_filename)
        except ErrorNotTempFile:
          pass

    elif os.path.isfile(path):
      DeleteGRRTempFile(path)
      deleted = [path]

    elif not os.path.exists(path):
      raise ErrorBadPath("File %s does not exist" % path)
    else:
      raise ErrorBadPath("Not a regular file or directory: %s" % path)

    out_rdfvalue = rdfvalue.LogMessage(data="Deleted: %s" % deleted)
    self.SendReply(out_rdfvalue)
