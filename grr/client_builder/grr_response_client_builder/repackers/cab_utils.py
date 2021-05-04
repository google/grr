#!/usr/bin/env python
"""Support for repacking a CAB file."""

# This code is based on the following specification [MS-CAB]:
#
# http://download.microsoft.com/download/4/d/a/4da14f27-b4ef-4170-a6e6-5b1ef85b1baa/[ms-cab].pdf

import os
import shutil
import struct
from typing import BinaryIO, Optional, List
import zlib


class Error(Exception):
  pass


def _Checksum(data: bytes) -> int:
  """Computes a checksum according to [MS-CAB]."""

  result = 0
  word_struct = struct.Struct("<I")
  pos = 0
  while pos < len(data):
    part = data[pos:pos + 4]
    if len(part) == 4:
      result ^= word_struct.unpack(part)[0]
    elif len(part) == 3:
      result ^= (part[0] << 16) | (part[1] << 8) | part[2]
    elif len(part) == 2:
      result ^= (part[0] << 8) | part[1]
    elif len(part) == 1:
      result ^= part[0]
    pos += 4
  return result


class StructBase:
  """Base class for structs from [MS-CAB].

  The struct is represented by a byte array. Subclasses define accessors to
  parse and modify the underlying byte array.
  """

  SIZE = 0
  """Size of the struct."""

  def __init__(self, f: Optional[BinaryIO] = None):
    if f is None:
      self.data = b"\x00" * self.SIZE
    else:
      self.data = f.read(self.SIZE)

  def Write(self, f: BinaryIO) -> None:
    f.write(self.data)

  def Size(self) -> int:
    return len(self.data)


class Field:
  """Descriptor for accessing a field in a `StructBase`."""

  def __init__(self, offset: int, size: int):
    self._offset = offset
    if size == 2:
      self._struct = struct.Struct("<H")
    elif size == 4:
      self._struct = struct.Struct("<I")
    else:
      raise Error(f"Unsupportd field size: {size}.")

  def __get__(self, obj: StructBase, objtype=None) -> int:
    return self._struct.unpack(obj.data[self._offset:self._offset +
                                        self._struct.size])[0]

  def __set__(self, obj: StructBase, value: int) -> None:
    data = self._struct.pack(value)
    obj.data = obj.data[:self._offset] + data + obj.data[self._offset +
                                                         len(data):]


class CfHeader(StructBase):
  """CfHeader struct from [MS-CAB]."""

  SIZE = 0x24

  cb_cabinet = Field(8, 4)
  coff_files = Field(16, 4)
  c_folders = Field(26, 2)
  c_files = Field(28, 2)
  flags = Field(30, 2)


class CfFolder(StructBase):
  """CfFolder struct from [MS-CAB]."""

  SIZE = 8

  coff_cab_start = Field(0, 4)
  c_cf_data = Field(4, 2)
  type_compress = Field(6, 2)

  def __init__(self, index: int, f: Optional[BinaryIO] = None):
    super().__init__(f)
    self.index = index


class CfFile(StructBase):
  """CfFile struct from [MS-CAB]."""

  SIZE = 16

  cb_file = Field(0, 4)
  uoff_folder_start = Field(4, 4)
  i_folder = Field(8, 2)

  def __init__(self, f: Optional[BinaryIO] = None):
    super().__init__(f)
    # Read null-terminated file name.
    if f is not None:
      name = []
      for _ in range(256):
        c = f.read(1)
        name.append(c)
        if c == b"\x00":
          break
      self.data += b"".join(name)

  @property
  def name(self):
    return self.data[self.SIZE:-1].decode("utf-8")


class CfData(StructBase):
  """CfData struct from [MS-CAB]."""

  SIZE = 8

  csum = Field(0, 4)
  cb_data = Field(4, 2)
  cb_uncomp = Field(6, 2)

  def __init__(self, f: Optional[BinaryIO] = None):
    super().__init__(f)
    if f is not None:
      # Read compressed data.
      self.data += f.read(self.cb_data)

  def Uncompress(self, zdict: Optional[bytes] = None) -> bytes:
    if self.compressed[:2] != b"\x43\x4b":
      raise Error("Compressed data is missing header.")
    decompress_obj = zlib.decompressobj(-zlib.MAX_WBITS, zdict=zdict)
    data = decompress_obj.decompress(self.compressed[2:])
    data += decompress_obj.flush()
    return data

  def ComputeChecksum(self) -> int:
    return _Checksum(self.data[4:])

  @classmethod
  def FromUncompressedData(cls, data: bytes) -> "CfData":
    """Creates a CfData block from uncompressed data."""
    result = CfData()
    result.cb_uncomp = len(data)
    compress_obj = zlib.compressobj(-1, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = b"\x43\x4b" + compress_obj.compress(
        data) + compress_obj.flush()
    if len(compressed) > 0x8000:
      raise Error(f"Compressed data is too large: {len(compressed)}.")
    result.cb_data = len(compressed)
    result.data += compressed
    result.csum = result.ComputeChecksum()
    return result

  @classmethod
  def FromZero(cls, data_len: int) -> "CfData":
    """Creates a CfData block containing `data_len` zero bytes."""
    result = CfData()
    result.cb_uncomp = data_len
    result.cb_data = data_len
    result.csum = 0
    result.data += b"\x00" * data_len
    return result

  @property
  def compressed(self) -> bytes:
    return self.data[self.SIZE:]


class Cab:
  """Represents a CAB file.

  The CAB file can be extracted, modified, and packed to a new CAB file.
  """

  def __init__(self, cab_path: str, temp_path: str) -> None:
    with open(cab_path, "rb") as f:
      self._cab_path = cab_path
      self._temp_path = temp_path

      if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
      os.mkdir(temp_path)
      os.mkdir(self.file_path_base)
      os.mkdir(self._folder_path_base)

      self._cf_header = CfHeader(f)
      self._cf_folders = []
      self._cf_files = []

      if self._cf_header.flags != 0:
        raise Error(f"Unsupported flags in CfHeader: {self._cf_header.flags}")

      for cf_folder in self._cf_folders:
        if cf_folder.type_compress != 1:
          raise Error(
              f"Unsupported compression type: {cf_folder.type_compress}")

      for i in range(self._cf_header.c_folders):
        cf_folder = CfFolder(i, f)
        self._cf_folders.append(cf_folder)

      for i in range(self._cf_header.c_files):
        cf_file = CfFile(f)
        self._cf_files.append(cf_file)

  def _ExtractFolders(self) -> None:
    """Extracts folders from this CAB file into `self._folder_path_base`."""
    zdict = b""
    with open(self._cab_path, "rb") as f:
      for cf_folder in self._cf_folders:
        f.seek(cf_folder.coff_cab_start)
        with open(self._FolderPath(cf_folder), "wb") as out_file:
          for _ in range(cf_folder.c_cf_data):
            cf_data = CfData(f)
            actual_csum = cf_data.ComputeChecksum()
            if cf_data.csum != actual_csum:
              raise Error("Bad CfData checksum. "
                          f"Got {actual_csum}, expected {cf_data.csum}.")
            data = cf_data.Uncompress(zdict)
            out_file.write(data)
            zdict = data

  def ExtractFiles(self) -> None:
    """Extracts files from this CAB archive into `self.file_path_base`."""
    self._ExtractFolders()
    for cf_file in self._cf_files:
      with open(self._FolderPath(self._cf_folders[cf_file.i_folder]),
                "rb") as in_file:
        with open(self._FilePath(cf_file), "wb") as out_file:
          in_file.seek(cf_file.uoff_folder_start)
          remaining = cf_file.cb_file
          data = in_file.read(cf_file.cb_file)
          if len(data) != cf_file.cb_file:
            raise Error("Short data read. "
                        f"Expected: {cf_file.cb_file}, got: {len(data)}.")
          out_file.write(data)

  def _IsExtracted(self) -> bool:
    if self._cf_folders:
      return os.path.exists(self._FolderPath(self._cf_folders[0]))
    return True

  def _PackFile(self, cf_file: CfFile, folder_file: BinaryIO,
                folder_offset: int) -> int:
    """Packs a single file into a folder file.

    Args:
      cf_file: The CfFile to pack.
      folder_file: Destination folder file.
      folder_offset: Current offset in output folder.

    Returns:
      the number of CfData blocks used.
    """
    num_cf_data = 0
    cf_file.uoff_folder_start = folder_offset
    with open(self._FilePath(cf_file), "rb") as in_file:
      while True:
        # The maximum for both compressed and uncompressed data is 0x8000.
        # The compressed data can be larger than the uncompressed data (if it
        # is not well compressible), so add room of 0x100 for the compressed
        # data to grow.
        data = in_file.read(0x8000 - 0x100)
        if not data:
          break
        cf_data = CfData.FromUncompressedData(data)
        cf_data.Write(folder_file)
        num_cf_data += 1
      cf_file.cb_file = in_file.tell()
      return num_cf_data

  def _PackFolder(self, cf_folder: CfFolder, cab_pos: int) -> int:
    """Packs a single folder into a folder file.

    Args:
      cf_folder: CfFolder to pack.
      cab_pos: Current position in output CAB file.

    Returns:
      the size of the resulting folder file.
    """
    num_cf_data = 0
    folder_offset = 0
    with open(self._FolderPath(cf_folder), "wb") as folder_file:
      for cf_file in self._cf_files:
        if cf_file.i_folder == cf_folder.index:
          num_cf_data += self._PackFile(cf_file, folder_file, folder_offset)
          folder_offset += cf_file.cb_file
      cf_folder.coff_cab_start = cab_pos
      cf_folder.c_cf_data = num_cf_data
      return folder_file.tell()

  def _Pack(self, dest_path: str) -> None:
    """Packs the CAB file from files in the temporary directory."""
    with open(dest_path, "wb") as cab_file:
      self._cf_header.Write(cab_file)
      for cf_folder in self._cf_folders:
        cf_folder.Write(cab_file)
      for cf_file in self._cf_files:
        cf_file.Write(cab_file)
      for cf_folder in self._cf_folders:
        with open(self._FolderPath(cf_folder), "rb") as folder_file:
          while True:
            data = folder_file.read(1024 * 1024)
            if not data:
              break
            cab_file.write(data)

  def Pack(self, dest_path: str) -> None:
    """Creates a new CAB files from files in the temporary directory."""

    if not self._IsExtracted():
      raise ValueError("ExtractFiles() must be called before Pack().")

    # Calculate where files and folders start in CAB file.
    cab_pos = self._cf_header.Size()
    cab_pos += sum([cf_folder.Size() for cf_folder in self._cf_folders])
    self._cf_header.coff_files = cab_pos
    cab_pos += sum([cf_file.Size() for cf_file in self._cf_files])

    # Pack each folder into folder file.
    for cf_folder in self._cf_folders:
      cab_pos += self._PackFolder(cf_folder, cab_pos)

    self._cf_header.cb_cabinet = cab_pos

    # Create CAB file from metadata and folder files.
    self._Pack(dest_path)

  @property
  def _folder_path_base(self) -> str:
    """Directory containing the extracted folders."""
    return os.path.join(self._temp_path, "folders")

  def _FolderPath(self, cf_folder: CfFolder) -> str:
    return os.path.join(self._folder_path_base, str(cf_folder.index))

  @property
  def file_path_base(self) -> str:
    """Directory containing the extracted files."""
    return os.path.join(self._temp_path, "files")

  def _FilePath(self, cf_file: CfFile) -> str:
    return os.path.join(self.file_path_base, cf_file.name)

  def WriteFile(self, name: str, data: bytes) -> None:
    """Replaces the contents of an extracted file."""
    if not self._IsExtracted():
      raise ValueError("ExtractFiles() must be called before WriteFile().")
    path = os.path.join(self.file_path_base, name)
    if not os.path.exists(path):
      raise Error("File doesn't exist in CAB: {name}.")
    with open(path, "wb") as f:
      f.write(data)


def PadCabFile(src_cab_path: str, dst_cab_path: str, new_size: int):
  """Pads a CAB file to a larger CAB file of `new_size`."""
  with open(src_cab_path, "rb") as src_cab:
    with open(dst_cab_path, "wb") as dst_cab:
      _PadCabFile(src_cab, dst_cab, new_size)


def _CfDataSizes(total_size: int) -> List[int]:
  """Computes the number/sizes of CfData blocks needed to fill `total_size` bytes."""
  # The padding has to be split into CfData blocks of maximum data size
  # of 0x8000.

  cf_data_sizes = []
  remaining = total_size
  while remaining > 0:
    cf_data_size = CfData.SIZE + min(remaining, 0x8000)
    cf_data_sizes.append(cf_data_size)
    remaining -= cf_data_size

  # Since each CfData block has a minimum size of CfData.SIZE, the total size
  # of the blocks might be too large now.
  # Shring the first block until the total padding size matches.

  while sum(cf_data_sizes) > total_size:
    cf_data_sizes[0] -= 1
    if cf_data_sizes[0] < CfData.SIZE:
      raise Error("Padding failed to shrink first CfData.")

  return cf_data_sizes


def _PadCabFile(src_cab: BinaryIO, dst_cab: BinaryIO, new_size: int):
  """Pads a CAB file to a larger CAB file of `new_size`."""

  # Pads the CAB file by appending a folder filled with zeros.
  # A CfFolder is inserted into the "middle" of the file, so all subsequent
  # offsets need to be moved by the size of a CfFolder.
  # The actual folder data is appended at the end of the file.

  cf_header = CfHeader(src_cab)
  old_size = cf_header.cb_cabinet
  padding_size = new_size - cf_header.cb_cabinet

  if padding_size < CfFolder.SIZE:
    raise Error(f"Padding size is too small: {padding_size}.")

  cf_header.cb_cabinet = new_size
  cf_header.coff_files += CfFolder.SIZE
  cf_header.c_folders += 1
  cf_header.Write(dst_cab)

  for i in range(cf_header.c_folders - 1):
    cf_folder = CfFolder(i, src_cab)
    cf_folder.coff_cab_start += CfFolder.SIZE
    cf_folder.Write(dst_cab)

  cf_data_sizes = _CfDataSizes(padding_size - CfFolder.SIZE)

  padding_folder = CfFolder(cf_header.c_folders - 1)
  padding_folder.coff_cab_start = old_size + CfFolder.SIZE
  padding_folder.c_cf_data = len(cf_data_sizes)
  padding_folder.Write(dst_cab)

  for _ in range(cf_header.c_files):
    cf_file = CfFile(src_cab)
    cf_file.Write(dst_cab)

  while True:
    data = src_cab.read(1024 * 1024)
    if not data:
      break
    dst_cab.write(data)

  for cf_data_size in cf_data_sizes:
    cf_data = CfData.FromZero(cf_data_size - CfData.SIZE)
    cf_data.Write(dst_cab)
