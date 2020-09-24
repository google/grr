#!/usr/bin/env python
"""Efficient compression of pkg installers.

Use case: store multiple large .pkg with similar and overlaping content in
one zip archive.

Solution: a .pkg file is a XAR archive. A XAR archive contains:

 * a binary header
 * a gzip-compressed XML table of contents
 * the concatenated archived files

The most notable file is named Payload, which is a gzip'ed CPIO archive
containing all the files to be installed.

CPIO archives files as a sequence of (ASCII header, file name, file contents).

References:

 * https://en.wikipedia.org/wiki/Xar_(archiver)
 * https://www.mkssoftware.com/docs/man4/cpio.4.asp
"""

import contextlib
import gzip
import hashlib
import os
import platform
import shutil
import struct
import subprocess
import typing
import xml.dom.minidom
import zlib

from grr_response_core.lib import utils

HASH_FILE_BLOCK_SIZE = 4 * 1024


def _ExtractPayload(payload_path: str, blocks_file_path: str,
                    blocks_dir: str) -> None:
  """Extracts and splits up the Payload file.

  Args:
    payload_path: Path to original payload.
    blocks_file_path: Path to output block index file.
    blocks_dir: Path to directory to write blocks into.
  """
  with contextlib.ExitStack() as stack:
    payload = stack.enter_context(gzip.open(payload_path, "rb"))
    blocks_file = stack.enter_context(open(blocks_file_path, "w"))

    def WriteBlock(data):
      checksum = hashlib.sha1(data).digest().hex()
      with open(os.path.join(blocks_dir, checksum), "wb") as out:
        out.write(data)
      print(checksum, file=blocks_file)

    while True:
      header = payload.read(76)
      WriteBlock(header)
      (magic, name_length_str,
       data_length_str) = struct.unpack("6s53x6s11s", header)
      if magic != b"070707":
        raise ValueError(f"Invalid CPIO header magic: {magic}.")
      name_length = int(name_length_str, 8)
      data_length = int(data_length_str, 8)
      data = payload.read(name_length + data_length)
      WriteBlock(data)
      if data.startswith(b"TRAILER!!"):
        break


def _ExtractXarHeader(xar_path: str, dst_path: str) -> None:
  """Extracts the XAR binary header from a XAR file."""
  with contextlib.ExitStack() as stack:
    xar = stack.enter_context(open(xar_path, "rb"))
    header_prefix = xar.read(6)
    (magic, header_length) = struct.unpack(">4sH", header_prefix)
    if magic != b"xar!":
      raise ValueError("Invalid XAR header magic: {magic}.")
    xar.seek(0)
    header = xar.read(header_length)
    out = stack.enter_context(open(dst_path, "wb"))
    out.write(header)


def _FlattenFiles(src_dir: str, dst_dir: str) -> None:
  for root, _, files in os.walk(src_dir):
    for file in files:
      shutil.move(os.path.join(root, file), os.path.join(dst_dir, file))
  shutil.rmtree(src_dir)


def SplitPkg(pkg_path: str, dst_dir: str, blocks_dir: str) -> None:
  """Decomposes a pkg file into a pair of directories.

  Args:
    pkg_path: Path to input .pkg file.
    dst_dir: Destination directory.
    blocks_dir: Directory to write blocks into.

  Raises:
    RuntimeError: if called on a system different than OSX.

  A pkg file is decomposed and stored into 2 directories (`dst_dir`,
  `blocks_dir`):

   * `dst_dir/header`: XAR binary header
   * `dst_dir/toc`: XAR XML table of contents
   * `dst_dir/files/`: all the files contained in the XAR EXCEPT payload,
      directories flattened.
   * `dst_dir/payload`: a list of files in the `blocks_dir/` directory, which
      if concatenated, produce the `Payload` file
   * `blocks_dir/`: contains fragments of the gunzip'ed `Payload` file

  The `Payload` file is decompressed, decomposed into blocks and stored as
  `blocks_dir/<sha1 of block>`. For each file in the CPIO archive 2 blocks are
  created, one for the ASCI header and another for the (file name,
  file contents) part.

  The `blocks_dir/` directory can be shared by multiple packages, resulting in
  common files being stored once only.

  SplitPkg is implemented using OSX command line tools and will thus run on OSX
  only.
  """

  if platform.system() != "Darwin":
    raise RuntimeError("JoinPkg works only on Mac OSX.")

  utils.EnsureDirExists(dst_dir)
  utils.EnsureDirExists(blocks_dir)

  files_root = os.path.join(dst_dir, "files")
  utils.EnsureDirExists(files_root)

  tmp_files_root = os.path.join(dst_dir, "_files")
  utils.EnsureDirExists(tmp_files_root)

  _ExtractXarHeader(pkg_path, os.path.join(dst_dir, "header"))

  command = ["xar", "--dump-toc=toc", "-f", pkg_path]
  subprocess.check_call(command, cwd=dst_dir)

  command = ["xar", "-x", "-f", pkg_path]
  subprocess.check_call(command, cwd=tmp_files_root)

  _FlattenFiles(tmp_files_root, files_root)

  _ExtractPayload(
      os.path.join(files_root, "Payload"), os.path.join(dst_dir, "payload"),
      blocks_dir)
  os.unlink(os.path.join(files_root, "Payload"))

  with open(os.path.join(dst_dir, "name"), "w") as f:
    f.write(os.path.basename(pkg_path))


def _BuildPayload(src_payload_path: str, dst_payload_path: str,
                  blocks_dir: str) -> None:
  with contextlib.ExitStack() as stack:
    dst_payload = stack.enter_context(gzip.open(dst_payload_path, "wb"))
    block_index = stack.enter_context(open(src_payload_path, "r"))
    for block_hash in block_index:
      block_hash = block_hash.strip("\n")
      with open(os.path.join(blocks_dir, block_hash), "rb") as block:
        shutil.copyfileobj(block, dst_payload)


def _XmlChild(node: xml.dom.minidom.Element,
              name: str) -> xml.dom.minidom.Element:
  children = node.getElementsByTagName(name)
  child = children[0]
  return child


def _XmlChildValue(node: xml.dom.minidom.Element, name: str) -> str:
  text_nodes = _XmlChild(node, name).childNodes
  return text_nodes[0].data


def _SetXmlChildValue(node: xml.dom.minidom.Element, name: str,
                      value: typing.Any) -> None:
  text_nodes = _XmlChild(node, name).childNodes
  text_nodes[0].data = str(value)


def _SetXmlChildAttribute(node: xml.dom.minidom.Element, name: str,
                          attribute: str, value: typing.Any) -> None:
  _XmlChild(node, name).setAttribute(attribute, str(value))


def _HashFile(path: str) -> bytes:
  hasher = hashlib.sha1()
  with open(path, "rb") as f:
    while True:
      block = f.read(HASH_FILE_BLOCK_SIZE)
      if not block:
        break
      hasher.update(block)
  return hasher.digest()


class _BuildTocResult(typing.NamedTuple):
  toc: bytes
  file_order: typing.List[str]


def _BuildToc(src_toc_path: str, files_dir: str) -> _BuildTocResult:
  """Creates a new XAR table of contents.

  Args:
    src_toc_path: Path to source TOC file.
    files_dir: Path to directory containing files of this XAR archive.

  Returns:
    The new TOC and a sorted list of file names, to be written into the XAR
    in that specific order.
  """

  file_order = []
  dom = xml.dom.minidom.parse(src_toc_path)

  _SetXmlChildAttribute(dom, "checksum", "style", "sha1")
  checksum_elem = _XmlChild(dom, "checksum")
  _SetXmlChildValue(checksum_elem, "offset", 0)
  _SetXmlChildValue(checksum_elem, "size", hashlib.sha1().digest_size)

  current_offset = hashlib.sha1().digest_size

  file_elems = dom.getElementsByTagName("file")
  for file_elem in file_elems:
    name = _XmlChildValue(file_elem, "name")
    file_type = _XmlChildValue(file_elem, "type")
    if file_type != "file":
      continue
    file_path = os.path.join(files_dir, name)
    size = os.path.getsize(file_path)
    file_order.append(name)
    _SetXmlChildValue(file_elem, "offset", current_offset)
    _SetXmlChildValue(file_elem, "size", size)
    _SetXmlChildValue(file_elem, "length", size)
    checksum = _HashFile(file_path).hex()
    _SetXmlChildValue(file_elem, "archived-checksum", checksum)
    _SetXmlChildAttribute(file_elem, "archived-checksum", "style", "sha1")
    _SetXmlChildValue(file_elem, "extracted-checksum", checksum)
    _SetXmlChildAttribute(file_elem, "extracted-checksum", "style", "sha1")
    _SetXmlChildAttribute(file_elem, "encoding", "style",
                          "application/octet-stream")
    current_offset += size
  return _BuildTocResult(toc=dom.toxml("utf-8"), file_order=file_order)


def _BuildHeader(src_header_path: str, toc_size: int,
                 toc_compressed_size: int) -> bytes:
  with open(src_header_path, "rb") as src_header:
    header = src_header.read()
    header = header[:8] + struct.pack(">QQL", toc_compressed_size, toc_size,
                                      1) + header[28:]
    return header


def JoinPkg(src_dir: str, blocks_dir: str, dst_path: str) -> None:
  # pyformat: disable
  """Recreates a .pkg file from a pair of directories.

  Args:
    src_dir: Directory containing decomposed .pkg file.
    blocks_dir: Directory containing blocks.
    dst_path: Path to destination .pkg file.

  Mode of operation:

  * Builds and gzip's the `Payload` file.
  * Creates a new XAR table of contents:
    * Patches the new size and checksum of the `Payload` file.
    * Since the size of the `Payload` file likely changed, recalculates the
      offset of all the other files.
    * Since most of the files other than `Payload` are small, for simplicity,
      we don't compress them. Their encoding and checksum has to be adjusted.
  * Concatenates the XAR header, the XAR table of contents, the checksum of
    the table of contents and the files.

  JoinPkg is portable code.
  """
  # pyformat: enable

  def SrcDir(*components):
    return os.path.join(src_dir, *components)

  _BuildPayload(SrcDir("payload"), SrcDir("files", "Payload"), blocks_dir)
  toc, files_order = _BuildToc(SrcDir("toc"), SrcDir("files"))
  toc_compressed = zlib.compress(toc)
  header = _BuildHeader(SrcDir("header"), len(toc), len(toc_compressed))
  with open(dst_path, "wb") as dst:
    dst.write(header)
    dst.write(toc_compressed)
    dst.write(hashlib.sha1(toc_compressed).digest())
    for file_name in files_order:
      with open(SrcDir("files", file_name), "rb") as file:
        shutil.copyfileobj(file, dst)
