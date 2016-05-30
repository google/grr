#!/usr/bin/env python
"""VFS Handler which provides access to the raw physical memory.

Memory access is provided by use of a special driver. Note that it is preferred
to use this VFS handler rather than directly access the raw handler since this
handler protects the system from access to unmapped memory regions such as DMA
regions. It is always safe to access all of memory using this handler.
"""




from rekall import session
import rekall_types as rdf_rekall_types
from grr.client import vfs
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class MemoryVFS(vfs.VFSHandler):
  """Access memory via the GRR Client VFS abstraction."""
  page_size = 0x1000

  supported_pathtype = rdf_paths.PathSpec.PathType.MEMORY
  auto_register = True

  def __init__(self,
               base_fd,
               pathspec=None,
               progress_callback=None,
               full_pathspec=None):
    super(MemoryVFS, self).__init__(None,
                                    progress_callback=progress_callback,
                                    full_pathspec=full_pathspec)
    if base_fd is not None:
      raise IOError("Memory handler can not be stacked on another handler.")

    self.pathspec = full_pathspec
    self.session = session.Session(filename=full_pathspec.path)
    load_as_plugin = self.session.plugins.load_as()
    self.address_space = load_as_plugin.GetPhysicalAddressSpace()
    if not self.address_space:
      raise IOError("Unable to open device")

    self.size = self.address_space.end()

  @classmethod
  def Open(cls,
           fd,
           component,
           pathspec=None,
           full_pathspec=None,
           progress_callback=None):
    if fd is None:
      return cls(base_fd=None, full_pathspec=full_pathspec)
    return fd

  def IsDirectory(self):
    return False

  def Stat(self):
    result = rdf_client.StatEntry(st_size=self.size, pathspec=self.pathspec)
    return result

  def GetMemoryInformation(self):
    result = rdf_rekall_types.MemoryInformation(
        cr3=self.session.GetParameter("dtb", 0),
        device=self.pathspec)

    for run in self.address_space.get_address_ranges():
      result.runs.Append(offset=run.start, length=run.length)

    return result

  def Read(self, length):
    """Read from the memory device, null padding the ranges."""
    to_read = min(length, self.size - self.offset)
    result = self.address_space.read(self.offset, to_read)
    self.offset += len(result)

    return result


vfs.VFS_HANDLERS[MemoryVFS.supported_pathtype] = MemoryVFS
