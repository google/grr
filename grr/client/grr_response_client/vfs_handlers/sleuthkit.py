#!/usr/bin/env python
"""Implement low level disk access using the sleuthkit."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import stat

import pytsk3

from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import precondition


class CachedFilesystem(object):
  """A container for the filesystem and image."""

  def __init__(self, fs, img):
    self.fs = fs
    self.img = img


class MyImgInfo(pytsk3.Img_Info):
  """An Img_Info class using the regular python file handling."""

  def __init__(self, fd=None, progress_callback=None):
    pytsk3.Img_Info.__init__(self)
    self.progress_callback = progress_callback
    self.fd = fd

  def read(self, offset, length):  # pylint: disable=g-bad-name
    # Sleuthkit operations might take a long time so we periodically call the
    # progress indicator callback as long as there are still data reads.
    if self.progress_callback:
      self.progress_callback()
    self.fd.seek(offset)
    return self.fd.read(length)

  def get_size(self):  # pylint: disable=g-bad-name
    # Windows is unable to report the true size of the raw device and allows
    # arbitrary reading past the end - so we lie here to force tsk to read it
    # anyway
    return 1e12


class TSKFile(vfs.VFSHandler):
  """Read a regular file."""

  supported_pathtype = rdf_paths.PathSpec.PathType.TSK
  auto_register = True

  # A mapping to encode TSK types to a stat.st_mode
  FILE_TYPE_LOOKUP = {
      pytsk3.TSK_FS_NAME_TYPE_UNDEF: 0,
      pytsk3.TSK_FS_NAME_TYPE_FIFO: stat.S_IFIFO,
      pytsk3.TSK_FS_NAME_TYPE_CHR: stat.S_IFCHR,
      pytsk3.TSK_FS_NAME_TYPE_DIR: stat.S_IFDIR,
      pytsk3.TSK_FS_NAME_TYPE_BLK: stat.S_IFBLK,
      pytsk3.TSK_FS_NAME_TYPE_REG: stat.S_IFREG,
      pytsk3.TSK_FS_NAME_TYPE_LNK: stat.S_IFLNK,
      pytsk3.TSK_FS_NAME_TYPE_SOCK: stat.S_IFSOCK,
  }

  META_TYPE_LOOKUP = {
      pytsk3.TSK_FS_META_TYPE_BLK: 0,
      pytsk3.TSK_FS_META_TYPE_CHR: stat.S_IFCHR,
      pytsk3.TSK_FS_META_TYPE_DIR: stat.S_IFDIR,
      pytsk3.TSK_FS_META_TYPE_FIFO: stat.S_IFIFO,
      pytsk3.TSK_FS_META_TYPE_LNK: stat.S_IFLNK,
      pytsk3.TSK_FS_META_TYPE_REG: stat.S_IFREG,
      pytsk3.TSK_FS_META_TYPE_SOCK: stat.S_IFSOCK,
  }

  # Files we won't return in directories.
  BLACKLIST_FILES = [
      "$OrphanFiles"  # Special TSK dir that invokes processing.
  ]

  # The file like object we read our image from
  tsk_raw_device = None

  # NTFS files carry an attribute identified by ntfs_type and ntfs_id.
  tsk_attribute = None

  # This is all bits that define the type of the file in the stat mode. Equal to
  # 0b1111000000000000.
  stat_type_mask = (
      stat.S_IFREG | stat.S_IFDIR | stat.S_IFLNK | stat.S_IFBLK
      | stat.S_IFCHR | stat.S_IFIFO | stat.S_IFSOCK)

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    """Use TSK to read the pathspec.

    Args:
      base_fd: The file like object we read this component from.
      pathspec: An optional pathspec to open directly.
      progress_callback: A callback to indicate that the open call is still
        working but needs more time.

    Raises:
      IOError: If the file can not be opened.
    """
    super(TSKFile, self).__init__(
        base_fd, pathspec=pathspec, progress_callback=progress_callback)
    if self.base_fd is None:
      raise IOError("TSK driver must have a file base.")

    # If our base is another tsk driver - borrow the reference to the raw
    # device, and replace the last pathspec component with this one after
    # extending its path.
    elif isinstance(base_fd, TSKFile) and self.base_fd.IsDirectory():
      self.tsk_raw_device = self.base_fd.tsk_raw_device
      last_path = utils.JoinPath(self.pathspec.last.path, pathspec.path)

      # Replace the last component with this one.
      self.pathspec.Pop(-1)
      self.pathspec.Append(pathspec)
      self.pathspec.last.path = last_path

    # Use the base fd as a base to parse the filesystem only if its file like.
    elif not self.base_fd.IsDirectory():
      self.tsk_raw_device = self.base_fd
      self.pathspec.Append(pathspec)
    else:
      # If we get here we have a directory from a non sleuthkit driver - dont
      # know what to do with it.
      raise IOError("Unable to parse base using Sleuthkit.")

    # If we are successful in opening this path below the path casing is
    # correct.
    self.pathspec.last.path_options = rdf_paths.PathSpec.Options.CASE_LITERAL

    fd_hash = self.tsk_raw_device.pathspec.SerializeToString()

    # Cache the filesystem using the path of the raw device
    try:
      self.filesystem = vfs.DEVICE_CACHE.Get(fd_hash)
      self.fs = self.filesystem.fs
    except KeyError:
      self.img = MyImgInfo(
          fd=self.tsk_raw_device, progress_callback=progress_callback)

      self.fs = pytsk3.FS_Info(self.img, 0)
      self.filesystem = CachedFilesystem(self.fs, self.img)

      vfs.DEVICE_CACHE.Put(fd_hash, self.filesystem)

    # We prefer to open the file based on the inode because that is more
    # efficient.
    if pathspec.HasField("inode"):
      self.fd = self.fs.open_meta(pathspec.inode)
      self.tsk_attribute = self.GetAttribute(pathspec.ntfs_type,
                                             pathspec.ntfs_id)
      if self.tsk_attribute:
        self.size = self.tsk_attribute.info.size
      else:
        self.size = self.fd.info.meta.size

    else:
      # Does the filename exist in the image?
      self.fd = self.fs.open(utils.SmartStr(self.pathspec.last.path))
      self.size = self.fd.info.meta.size
      self.pathspec.last.inode = self.fd.info.meta.addr

  def GetAttribute(self, ntfs_type, ntfs_id):
    for attribute in self.fd:
      if attribute.info.type == ntfs_type:
        # If ntfs_id is specified it has to also match.
        if ntfs_id != 0 and attribute.info.id != ntfs_id:
          continue

        return attribute

    return None

  def ListNames(self):
    directory_handle = self.fd.as_directory()
    for f in directory_handle:
      # TSK only deals with utf8 strings, but path components are always unicode
      # objects - so we convert to unicode as soon as we receive data from
      # TSK. Prefer to compare unicode objects to guarantee they are normalized.
      yield utils.SmartUnicode(f.info.name.name)

  def MakeStatResponse(self, tsk_file, tsk_attribute=None, append_name=None):
    """Given a TSK info object make a StatEntry.

    Note that tsk uses two things to uniquely identify a data stream - the inode
    object given in tsk_file and the attribute object which may correspond to an
    ADS of this file for filesystems which support ADS. We store both of these
    in the stat response.

    Args:
      tsk_file: A TSK File object for the specified inode.
      tsk_attribute: A TSK Attribute object for the ADS. If None we use the main
        stream.
      append_name: If specified we append this name to the last element of the
        pathspec.

    Returns:
      A StatEntry which can be used to re-open this exact VFS node.
    """
    precondition.AssertOptionalType(append_name, unicode)

    info = tsk_file.info
    response = rdf_client_fs.StatEntry()
    meta = info.meta
    if meta:
      response.st_ino = meta.addr
      for attribute in [
          "mode", "nlink", "uid", "gid", "size", "atime", "mtime", "ctime",
          "crtime"
      ]:
        try:
          value = int(getattr(meta, attribute))
          if value < 0:
            value &= 0xFFFFFFFF

          setattr(response, "st_%s" % attribute, value)
        except AttributeError:
          pass

    name = info.name
    child_pathspec = self.pathspec.Copy()

    if append_name is not None:
      # Append the name to the most inner pathspec
      child_pathspec.last.path = utils.JoinPath(child_pathspec.last.path,
                                                append_name)

    child_pathspec.last.inode = meta.addr
    if tsk_attribute is not None:
      child_pathspec.last.ntfs_type = int(tsk_attribute.info.type)
      child_pathspec.last.ntfs_id = int(tsk_attribute.info.id)
      child_pathspec.last.stream_name = tsk_attribute.info.name

      # Update the size with the attribute size.
      response.st_size = tsk_attribute.info.size

      default = rdf_paths.PathSpec.tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT
      last = child_pathspec.last
      if last.ntfs_type != default or last.ntfs_id:
        # This is an ads and should be treated as a file.
        # Clear all file type bits.
        response.st_mode &= ~self.stat_type_mask
        response.st_mode |= stat.S_IFREG

    else:
      child_pathspec.last.ntfs_type = None
      child_pathspec.last.ntfs_id = None
      child_pathspec.last.stream_name = None

    if name:
      # Encode the type onto the st_mode response
      response.st_mode |= self.FILE_TYPE_LOOKUP.get(int(name.type), 0)

    if meta:
      # What if the types are different? What to do here?
      response.st_mode |= self.META_TYPE_LOOKUP.get(int(meta.type), 0)

    # Write the pathspec on the response.
    response.pathspec = child_pathspec
    return response

  def Read(self, length):
    """Read from the file."""
    if not self.IsFile():
      raise IOError("%s is not a file." % self.pathspec.last.path)

    available = min(self.size - self.offset, length)
    if available > 0:
      # This raises a RuntimeError in some situations.
      try:
        data = self.fd.read_random(self.offset, available,
                                   self.pathspec.last.ntfs_type,
                                   self.pathspec.last.ntfs_id)
      except RuntimeError as e:
        raise IOError(e)

      self.offset += len(data)

      return data
    return ""

  def Stat(self, ext_attrs=None):
    """Return a stat of the file."""
    del ext_attrs  # Unused.
    return self.MakeStatResponse(self.fd, tsk_attribute=self.tsk_attribute)

  def ListFiles(self, ext_attrs=None):
    """List all the files in the directory."""
    del ext_attrs  # Unused.

    if not self.IsDirectory():
      raise IOError("%s is not a directory" % self.pathspec.CollapsePath())

    for f in self.fd.as_directory():
      try:
        name = utils.SmartUnicode(f.info.name.name)
        # Drop these useless entries.
        if name in [".", ".."] or name in self.BLACKLIST_FILES:
          continue

        # First we yield a standard response using the default attributes.
        yield self.MakeStatResponse(f, tsk_attribute=None, append_name=name)

        # Now send back additional named attributes for the ADS.
        for attribute in f:
          if attribute.info.type in [
              pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA, pytsk3.TSK_FS_ATTR_TYPE_DEFAULT
          ]:
            if attribute.info.name:
              yield self.MakeStatResponse(
                  f, append_name=name, tsk_attribute=attribute)
      except AttributeError:
        pass

  def IsDirectory(self):
    last = self.pathspec.last
    default = rdf_paths.PathSpec.tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT
    if last.ntfs_type != default or last.ntfs_id:
      # This is an ads so treat as a file.
      return False

    return self.fd.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR

  def IsFile(self):
    last = self.pathspec.last
    default = rdf_paths.PathSpec.tsk_fs_attr_type.TSK_FS_ATTR_TYPE_DEFAULT
    if last.ntfs_type != default or last.ntfs_id:
      # This is an ads so treat as a file.
      return True

    return self.fd.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG

  @classmethod
  def Open(cls, fd, component, pathspec=None, progress_callback=None):
    # A Pathspec which starts with TSK means we need to resolve the mount point
    # at runtime.
    if fd is None and component.pathtype == rdf_paths.PathSpec.PathType.TSK:
      # We are the top level handler. This means we need to check the system
      # mounts to work out the exact mount point and device we need to
      # open. We then modify the pathspec so we get nested in the raw
      # pathspec.
      raw_pathspec, corrected_path = client_utils.GetRawDevice(component.path)

      # Insert the raw device before the component in the pathspec and correct
      # the path
      component.path = corrected_path
      pathspec.Insert(0, component)
      pathspec.Insert(0, raw_pathspec)

      # Allow incoming pathspec to be given in the local system path
      # conventions.
      for component in pathspec:
        if component.path:
          component.path = client_utils.LocalPathToCanonicalPath(component.path)

      # We have not actually opened anything in this iteration, but modified the
      # pathspec. Next time we should be able to open it properly.
      return fd

    # If an inode is specified, just use it directly.
    elif component.HasField("inode"):
      return TSKFile(fd, component, progress_callback=progress_callback)

    # Otherwise do the usual case folding.
    else:
      return vfs.VFSHandler.Open(
          fd, component, pathspec=pathspec, progress_callback=progress_callback)
