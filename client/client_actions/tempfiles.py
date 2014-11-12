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
from grr.client.vfs_handlers import files
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils


class Error(Exception):
  """Base error class."""


class ErrorBadPath(Error):
  """OS file path errors."""


class ErrorNotTempFile(Error):
  """Attempt to delete a file that isn't a GRR tempfile."""


def CreateGRRTempFile(directory=None, filename=None, lifetime=0, mode="w+b",
                      suffix=""):
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

    filename: The name of the file to use. Note that setting both filename and
       directory name is not allowed.

    lifetime: time in seconds before we should delete this tempfile.

    mode: The mode to open the file.

    suffix: optional suffix to use for the temp file

  Returns:
    Python file object

  Raises:
    OSError: on permission denied
    ErrorBadPath: if path is not absolute
    ValueError: if Client.tempfile_prefix is undefined in the config.
  """
  if filename and directory:
    raise ErrorBadPath("Providing both filename and directory name forbidden.")

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
  if filename is None:
    outfile = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix,
                                          dir=directory, delete=False)
  else:
    if suffix:
      filename = "%s.%s" % (filename, suffix)

    outfile = open(os.path.join(directory, filename), mode)

  if lifetime > 0:
    cleanup = threading.Timer(lifetime, DeleteGRRTempFile, (outfile.name,))
    cleanup.start()

  # Fix perms on the file, since this code is used for writing executable blobs
  # we apply RWX.
  if sys.platform == "win32":
    client_utils.WinChmod(outfile.name, ["FILE_ALL_ACCESS"])
  else:
    os.chmod(outfile.name, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

  return outfile


def DeleteGRRTempFile(path):
  """Delete a GRR temp file.

  To limit possible damage the path must be absolute and either the file must be
  within Client.tempdir or the file name must begin with Client.tempfile_prefix.

  Args:
    path: path string to file to be deleted.

  Raises:
    OSError: Permission denied, or file not found.
    ErrorBadPath: Path must be absolute
    ErrorNotTempFile: Filename must start with Client.tempfile_prefix
  """
  if not os.path.isabs(path):
    raise ErrorBadPath("Path must be absolute")

  prefix = config_lib.CONFIG["Client.tempfile_prefix"]
  directory = config_lib.CONFIG["Client.tempdir"]
  if not (os.path.basename(path).startswith(prefix) or
          os.path.commonprefix([directory, path]) == directory):
    msg = "Can't delete %s, filename must start with %s"
    raise ErrorNotTempFile(msg % (path, prefix))

  if os.path.exists(path):
    # Clear our file handle cache so the file can be deleted.
    files.FILE_HANDLE_CACHE.Flush()
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

    # Normalize the path, so DeleteGRRTempFile can correctly check if
    # it is within Client.tempdir.
    if args.path:
      path = client_utils.CanonicalPathToLocalPath(
          utils.NormalizePath(args.path))
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
