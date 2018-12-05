#!/usr/bin/env python
"""Filestore aff4:/files abstraction layer.

Filestore allows for multiple different filestore modules to register URNs
under aff4:/files to handle new file hash and new file creations.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import logging


from future.utils import iteritems

from grr_response_core.lib import fingerprint
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import nsrl as rdf_nsrl
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server.aff4_objects import aff4_grr


class FileStore(aff4.AFF4Volume):
  """Filestore for files downloaded from clients.

  Modules can register for file content by creating paths under "aff4:/files".
  By default files created in this namespace can be read by users that have the
  URN (hash).  See lib/aff4_objects/user_managers.py.

  Filestores are operated on according to their PRIORITY value, lowest first.
  """
  PATH = rdfvalue.RDFURN("aff4:/files")
  CHUNK_SIZE = 5 * 512 * 1024
  PRIORITY = 99  # default low priority for subclasses
  EXTERNAL = False

  def GetChildrenByPriority(self, allow_external=True):
    """Generator that yields active filestore children in priority order."""
    for child in sorted(self.OpenChildren(), key=lambda x: x.PRIORITY):
      if not allow_external and child.EXTERNAL:
        continue
      if child.Get(child.Schema.ACTIVE):
        yield child

  def AddURNToIndex(self, sha256hash, file_urn):
    for child in self.GetChildrenByPriority():
      child.AddURN(sha256hash, file_urn)

  def AddURN(self, sha256hash, file_urn):
    pass

  def CheckHashes(self, hashes, external=True):
    """Checks a list of hashes for presence in the store.

    Sub stores need to pass back the original HashDigest objects since they
    carry state about the original file source.

    Only unique hashes are checked, if there is duplication in the hashes input
    it is the caller's responsibility to maintain any necessary mappings.

    Args:
      hashes: A list of Hash objects to check.
      external: If true, attempt to check stores defined as EXTERNAL.

    Yields:
      Tuples of (RDFURN, hash object) that exist in the store.
    """
    hashes = set(hashes)
    for child in self.GetChildrenByPriority(allow_external=external):
      for urn, hash_obj in child.CheckHashes(hashes):
        yield urn, hash_obj

        hashes.discard(hash_obj)

      # Nothing to search for, we are done.
      if not hashes:
        break

  def AddFile(self, fd, external=True):
    """Create a new file in the file store.

    We delegate the actual file addition to our contained
    implementations. Implementations can either implement the AddFile() method,
    returning a file like object which will be written on, or directly support
    the AddBlobToStore() method which can copy the VFSBlobImage efficiently.

    Args:
      fd: An AFF4 object open for read/write.
      external: If true, attempt to add files to stores defined as EXTERNAL.
    """
    files_for_write = []

    for sub_store in self.GetChildrenByPriority(allow_external=external):
      new_file = sub_store.AddFile(fd)
      if new_file:
        files_for_write.append(new_file)

    fd.Seek(0)
    while files_for_write:
      # If we got filehandles back, send them the data.
      data = fd.Read(self.CHUNK_SIZE)
      if not data:
        break

      for child in files_for_write:
        child.Write(data)

    for child in files_for_write:
      child.Close()

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    ACTIVE = aff4.Attribute(
        "aff4:filestore_active",
        rdfvalue.RDFBool,
        "If true this filestore is active.",
        default=True)


class FileStoreImage(aff4_grr.VFSBlobImage):
  """The AFF4 files that are stored in the file store area.

  This class is deprecated, the stored files are now just the original
  type we used to download them - VFSBlobImage mostly. No special
  treatment needed anymore.
  """


class FileStoreHash(rdfvalue.RDFURN):
  """Urns returned from HashFileStore.ListHashes()."""

  def __init__(self,
               initializer=None,
               fingerprint_type=None,
               hash_type=None,
               hash_value=None,
               age=None):
    if fingerprint_type:
      initializer = HashFileStore.PATH.Add(fingerprint_type).Add(hash_type).Add(
          hash_value)

    super(FileStoreHash, self).__init__(initializer=initializer, age=age)

    if initializer is not None:
      # TODO(amoser): Parsing URNs to get information about the object
      # is not the right way to do this. We need to find a better way
      # here and remove all the custom deserialization methods.
      self._ParseUrn()

  @classmethod
  def FromSerializedString(cls, value, age=None):
    result = super(FileStoreHash, cls).FromSerializedString(value, age=None)
    result._ParseUrn()  # pylint: disable=protected-access
    return result

  @classmethod
  def FromDatastoreValue(cls, value, age=None):
    result = super(FileStoreHash, cls).FromDatastoreValue(value, age=None)
    result._ParseUrn()  # pylint: disable=protected-access
    return result

  def _ParseUrn(self):
    relative_name = self.RelativeName(HashFileStore.PATH)
    if not relative_name:
      raise ValueError(
          "URN %s is not a hash file store urn. Hash file store "
          "urn should start with %s." % (str(self), str(HashFileStore.PATH)))
    relative_path = relative_name.split("/")
    if (len(relative_path) != 3 or
        relative_path[0] not in HashFileStore.HASH_TYPES or
        relative_path[1] not in HashFileStore.HASH_TYPES[relative_path[0]]):
      raise ValueError(
          "URN %s is not a hash file store urn. Hash file store urn should "
          "look like: "
          "aff4:/files/hash/[fingerprint_type]/[hash_type]/[hash_value]." %
          str(self))

    self.fingerprint_type, self.hash_type, self.hash_value = relative_path


class HashFileStore(FileStore):
  """FileStore that stores files referenced by hash."""

  PATH = rdfvalue.RDFURN("aff4:/files/hash")
  PRIORITY = 2
  EXTERNAL = False
  HASH_TYPES = {
      "generic": ["md5", "sha1", "sha256", "SignedData"],
      "pecoff": ["md5", "sha1"]
  }

  def AddURN(self, sha256hash, file_urn):
    pass
    # Writing these indexes are causing production problems, and
    # they aren't currently used by anything.
    #
    # TODO(user): Implement a way to store this data without
    # melting bigtable or remove it entirely.
    #
    # index_urn = self.PATH.Add("generic/sha256").Add(sha256hash)
    # self._AddToIndex(index_urn, file_urn)

  def _AddToIndex(self, index_urn, file_urn):
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.FileHashIndexAddItem(index_urn, file_urn)

  @classmethod
  def Query(cls, index_urn, target_prefix="", limit=100, token=None):
    """Search the index for matches starting with target_prefix.

    Args:
       index_urn: The index to use. Should be a urn that points to the sha256
         namespace.
       target_prefix: The prefix to match against the index.
       limit: Either a tuple of (start, limit) or a maximum number of results to
         return.
       token: A DB token.

    Returns:
      URNs of files which have the same data as this file - as read from the
      index.
    """
    return data_store.DB.FileHashIndexQuery(
        index_urn, target_prefix, limit=limit)

  @classmethod
  def GetReferencesMD5(cls, md5_hash, target_prefix="", limit=100, token=None):
    urn = aff4.ROOT_URN.Add("files/hash/generic/md5").Add(str(md5_hash))
    fd = aff4.FACTORY.Open(urn, token=token)
    return cls.Query(fd.urn, target_prefix="", limit=100, token=token)

  @classmethod
  def GetReferencesSHA1(cls, sha1_hash, target_prefix="", limit=100,
                        token=None):
    urn = aff4.ROOT_URN.Add("files/hash/generic/sha1").Add(str(sha1_hash))
    fd = aff4.FACTORY.Open(urn, token=token)
    return cls.Query(fd.urn, target_prefix="", limit=100, token=token)

  @classmethod
  def GetReferencesSHA256(cls,
                          sha256_hash,
                          target_prefix="",
                          limit=100,
                          token=None):
    urn = aff4.ROOT_URN.Add("files/hash/generic/sha256").Add(str(sha256_hash))
    fd = aff4.FACTORY.Open(urn, token=token)
    return cls.Query(fd.urn, target_prefix="", limit=100, token=token)

  def CheckHashes(self, hashes):
    """Check hashes against the filestore.

    Blobs use the hash in the schema:
    aff4:/files/hash/generic/sha256/[sha256hash]

    Args:
      hashes: A list of Hash objects to check.

    Yields:
      Tuples of (RDFURN, hash object) that exist in the store.
    """
    hash_map = {}
    for hsh in hashes:
      if hsh.HasField("sha256"):
        # The canonical name of the file is where we store the file hash.
        hash_map[aff4.ROOT_URN.Add("files/hash/generic/sha256").Add(
            str(hsh.sha256))] = hsh

    for metadata in aff4.FACTORY.Stat(list(hash_map)):
      yield metadata["urn"], hash_map[metadata["urn"]]

  def _GetHashers(self, hash_types):
    return [
        getattr(hashlib, hash_type)
        for hash_type in hash_types
        if hasattr(hashlib, hash_type)
    ]

  def _HashFile(self, fd):
    """Look for the required hashes in the file."""
    hashes = data_store_utils.GetFileHashEntry(fd)
    if hashes:
      found_all = True
      for fingerprint_type, hash_types in iteritems(self.HASH_TYPES):
        for hash_type in hash_types:
          if fingerprint_type == "pecoff":
            hash_type = "pecoff_%s" % hash_type
          if not hashes.HasField(hash_type):
            found_all = False
            break
        if not found_all:
          break
      if found_all:
        return hashes

    fingerprinter = fingerprint.Fingerprinter(fd)
    if "generic" in self.HASH_TYPES:
      hashers = self._GetHashers(self.HASH_TYPES["generic"])
      fingerprinter.EvalGeneric(hashers=hashers)
    if "pecoff" in self.HASH_TYPES:
      hashers = self._GetHashers(self.HASH_TYPES["pecoff"])
      if hashers:
        fingerprinter.EvalPecoff(hashers=hashers)

    if not hashes:
      hashes = fd.Schema.HASH()

    for result in fingerprinter.HashIt():
      fingerprint_type = result["name"]
      for hash_type in self.HASH_TYPES[fingerprint_type]:
        if hash_type not in result:
          continue

        if hash_type == "SignedData":
          # There can be several certs in the same file.
          for signed_data in result[hash_type]:
            hashes.signed_data.Append(
                revision=signed_data[0],
                cert_type=signed_data[1],
                certificate=signed_data[2])
          continue

        # Set the hashes in the original object
        if fingerprint_type == "generic":
          hashes.Set(hash_type, result[hash_type])

        elif fingerprint_type == "pecoff":
          hashes.Set("pecoff_%s" % hash_type, result[hash_type])

        else:
          logging.error("Unknown fingerprint_type %s.", fingerprint_type)

    return hashes

  def AddFile(self, fd):
    """Adds a file to the hash file store.

    We take a file in the client space:
      aff4:/C.123123123/fs/os/usr/local/blah

    Hash it, update the hash in the original file if its different to the
    one calculated on the client, and copy the original AFF4 object to

      aff4:/files/hash/generic/sha256/123123123 (canonical reference)

    We then create symlinks for all other hash types:

      aff4:/files/hash/generic/sha1/345345345
      aff4:/files/hash/generic/md5/456456456
      aff4:/files/hash/pecoff/md5/aaaaaaaa (only for PEs)
      aff4:/files/hash/pecoff/sha1/bbbbbbbb (only for PEs)

    When present in PE files, the signing data (revision, cert_type,
    certificate) is added to the original object.

    This can't be done simply in the FileStore.Write() method with fixed hash
    buffer sizes because the authenticode hashes need to track hashing of
    different-sized regions based on the signature information.

    Args:
      fd: File open for reading.

    Raises:
      IOError: If there was an error writing the file.
    """
    hashes = self._HashFile(fd)

    # The empty file is very common, we don't keep the back references for it
    # in the DB since it just takes up too much space.
    empty_hash = ("e3b0c44298fc1c149afbf4c8996fb924"
                  "27ae41e4649b934ca495991b7852b855")
    if hashes.sha256 == empty_hash:
      return

    # Update the hashes field now that we have calculated them all.
    fd.Set(fd.Schema.HASH, hashes)
    fd.Flush()

    # sha256 is the canonical location.
    canonical_urn = self.PATH.Add("generic/sha256").Add(str(hashes.sha256))
    if not list(aff4.FACTORY.Stat([canonical_urn])):
      aff4.FACTORY.Copy(fd.urn, canonical_urn)
      # Remove the STAT entry, it makes no sense to copy it between clients.
      with aff4.FACTORY.Open(
          canonical_urn, mode="rw", token=self.token) as new_fd:
        new_fd.Set(new_fd.Schema.STAT(None))

    self._AddToIndex(canonical_urn, fd.urn)

    for hash_type, hash_digest in hashes.ListSetFields():
      # Determine fingerprint type.
      hash_type = hash_type.name
      # No need to create a symlink for sha256, it's the canonical location.
      if hash_type == "sha256":
        continue
      hash_digest = str(hash_digest)
      fingerprint_type = "generic"
      if hash_type.startswith("pecoff_"):
        fingerprint_type = "pecoff"
        hash_type = hash_type[len("pecoff_"):]
      if hash_type not in self.HASH_TYPES[fingerprint_type]:
        continue

      file_store_urn = self.PATH.Add(fingerprint_type).Add(hash_type).Add(
          hash_digest)

      with aff4.FACTORY.Create(
          file_store_urn, aff4.AFF4Symlink, token=self.token) as symlink:
        symlink.Set(symlink.Schema.SYMLINK_TARGET, canonical_urn)

    # We do not want to be externally written here.
    return None

  @staticmethod
  def ListHashes(age=aff4.NEWEST_TIME):
    """Yields all the hashes in the file store.

    Args:
      age: AFF4 age specification. Only get hits corresponding to the given age
        spec. Should be aff4.NEWEST_TIME or a time range given as a tuple
        (start, end) in microseconds since Jan 1st, 1970. If just a microseconds
        value is given it's treated as the higher end of the range, i.e. (0,
        age). See aff4.FACTORY.ParseAgeSpecification for details.

    Yields:
      FileStoreHash instances corresponding to all the hashes in the file store.

    Raises:
      ValueError: if age was set to aff4.ALL_TIMES.
    """
    if age == aff4.ALL_TIMES:
      raise ValueError("age==aff4.ALL_TIMES is not allowed.")

    urns = []
    for fingerprint_type, hash_types in iteritems(HashFileStore.HASH_TYPES):
      for hash_type in hash_types:
        urns.append(HashFileStore.PATH.Add(fingerprint_type).Add(hash_type))

    for _, values in aff4.FACTORY.MultiListChildren(urns, age=age):
      for value in values:
        yield FileStoreHash(value)

  @classmethod
  def GetClientsForHash(cls, hash_obj, token=None, age=aff4.NEWEST_TIME):
    """Yields client_files for the specified file store hash.

    Args:
      hash_obj: RDFURN that we want to get hits for.
      token: Security token.
      age: AFF4 age specification. Only get hits corresponding to the given age
        spec. Should be aff4.NEWEST_TIME or a time range given as a tuple
        (start, end) in microseconds since Jan 1st, 1970. If just a microseconds
        value is given it's treated as the higher end of the range, i.e. (0,
        age). See aff4.FACTORY.ParseAgeSpecification for details.

    Yields:
      RDFURNs corresponding to a client file that has the hash.

    Raises:
      ValueError: if age was set to aff4.ALL_TIMES.
    """

    if age == aff4.ALL_TIMES:
      raise ValueError("age==aff4.ALL_TIMES is not supported.")

    results = cls.GetClientsForHashes([hash_obj], token=token, age=age)
    for _, client_files in results:
      for client_file in client_files:
        yield client_file

  @classmethod
  def GetClientsForHashes(cls, hashes, token=None, age=aff4.NEWEST_TIME):
    """Yields (hash, client_files) pairs for all the specified hashes.

    Args:
      hashes: List of RDFURN's.
      token: Security token.
      age: AFF4 age specification. Only get hits corresponding to the given age
        spec. Should be aff4.NEWEST_TIME or a time range given as a tuple
        (start, end) in microseconds since Jan 1st, 1970. If just a microseconds
        value is given it's treated as the higher end of the range, i.e. (0,
        age). See aff4.FACTORY.ParseAgeSpecification for details.

    Yields:
      (hash, client_files) tuples, where hash is a FileStoreHash instance and
      client_files is a list of RDFURN's corresponding to client files that
      have the hash.

    Raises:
      ValueError: if age was set to aff4.ALL_TIMES.
    """
    if age == aff4.ALL_TIMES:
      raise ValueError("age==aff4.ALL_TIMES is not supported.")
    timestamp = aff4.FACTORY.ParseAgeSpecification(age)

    index_objects = list(aff4.FACTORY.MultiOpen(hashes, token=token))
    index_locations = {}
    for o in index_objects:
      index_locations.setdefault(o.urn, []).append(o.symlink_urn)
    for hash_obj, client_files in data_store.DB.FileHashIndexQueryMultiple(
        index_locations, timestamp=timestamp):
      symlinks = index_locations[hash_obj]
      for original_hash in symlinks:
        hash_obj = original_hash or hash_obj
        yield (FileStoreHash(hash_obj), client_files)


class NSRLFile(FileStoreImage):
  """Represents a file from the NSRL database."""

  class SchemaCls(FileStoreImage.SchemaCls):
    """Schema class for NSRLFile."""

    # We do not need child indexes since the NSRL database is quite big.
    ADD_CHILD_INDEX = False

    # Make the default SIZE argument as unversioned.
    SIZE = aff4.Attribute(
        "aff4:size",
        rdfvalue.RDFInteger,
        "The total size of available data for this stream.",
        "size",
        default=0,
        versioned=False)
    TYPE = aff4.Attribute(
        "aff4:type",
        rdfvalue.RDFString,
        "The name of the AFF4Object derived class.",
        "type",
        versioned=False)
    NSRL = aff4.Attribute(
        "aff4:nsrl", rdf_nsrl.NSRLInformation, versioned=False)


class NSRLFileStore(HashFileStore):
  """FileStore with NSRL hashes."""

  PATH = rdfvalue.RDFURN("aff4:/files/nsrl")
  PRIORITY = 1
  EXTERNAL = False

  FILE_TYPES = {
      "M": rdf_nsrl.NSRLInformation.FileType.MALICIOUS_FILE,
      "S": rdf_nsrl.NSRLInformation.FileType.SPECIAL_FILE,
      "": rdf_nsrl.NSRLInformation.FileType.NORMAL_FILE
  }

  def GetChildrenByPriority(self, allow_external=True):
    return

  @staticmethod
  def ListHashes(token=None, age=aff4.NEWEST_TIME):
    return

  def AddURN(self, sha256hash, file_urn):
    return

  def NSRLInfoForSHA1s(self, hashes):
    urns = {self.PATH.Add(h): h for h in hashes}
    return {
        urns[obj.urn]: obj
        for obj in aff4.FACTORY.MultiOpen(urns, token=self.token)
    }

  def CheckHashes(self, hashes, unused_external=True):
    """Checks a list of hashes for presence in the store.

    Only unique sha1 hashes are checked, if there is duplication in the hashes
    input it is the caller's responsibility to maintain any necessary mappings.

    Args:
      hashes: A list of Hash objects to check.
      unused_external: Ignored.

    Yields:
      Tuples of (RDFURN, hash object) that exist in the store.
    """
    hash_map = {}
    for hsh in hashes:
      if hsh.HasField("sha1"):
        hash_urn = self.PATH.Add(str(hsh.sha1))
        logging.debug("Checking URN %s", str(hash_urn))
        hash_map[hash_urn] = hsh

    for metadata in aff4.FACTORY.Stat(list(hash_map)):
      yield metadata["urn"], hash_map[metadata["urn"]]

  def AddHash(self, sha1, md5, crc, file_name, file_size, product_code_list,
              op_system_code_list, special_code):
    """Adds a new file from the NSRL hash database.

    We create a new subject in:
      aff4:/files/nsrl/<sha1>
    with all the other arguments as attributes.

    Args:
      sha1: SHA1 digest as a hex encoded string.
      md5: MD5 digest as a hex encoded string.
      crc: File CRC as an integer.
      file_name: Filename.
      file_size: Size of file.
      product_code_list: List of products this file is part of.
      op_system_code_list: List of operating systems this file is part of.
      special_code: Special code (malicious/special/normal file).
    """
    file_store_urn = self.PATH.Add(sha1)

    special_code = self.FILE_TYPES.get(special_code, self.FILE_TYPES[""])

    with aff4.FACTORY.Create(
        file_store_urn, NSRLFile, mode="w", token=self.token) as fd:
      fd.Set(
          fd.Schema.NSRL(
              sha1=sha1.decode("hex"),
              md5=md5.decode("hex"),
              crc32=crc,
              file_name=file_name,
              file_size=file_size,
              product_code=product_code_list,
              op_system_code=op_system_code_list,
              file_type=special_code))

  def AddFile(self, fd):
    """AddFile is not used for the NSRLFileStore."""
    return None


class FileStoreInit(registry.InitHook):
  """Create filestore aff4 paths."""

  pre = [aff4_grr.GRRAFF4Init]

  def Run(self):
    """Create FileStore and HashFileStore namespaces."""
    if not data_store.AFF4Enabled():
      return

    try:
      filestore = aff4.FACTORY.Create(
          FileStore.PATH, FileStore, mode="rw", token=aff4.FACTORY.root_token)
      filestore.Close()
      hash_filestore = aff4.FACTORY.Create(
          HashFileStore.PATH,
          HashFileStore,
          mode="rw",
          token=aff4.FACTORY.root_token)
      hash_filestore.Close()
      nsrl_filestore = aff4.FACTORY.Create(
          NSRLFileStore.PATH,
          NSRLFileStore,
          mode="rw",
          token=aff4.FACTORY.root_token)
      nsrl_filestore.Close()
    except access_control.UnauthorizedAccess:
      # The aff4:/files area is ACL protected, this might not work on components
      # that have ACL enforcement.
      pass
