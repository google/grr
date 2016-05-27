#!/usr/bin/env python
"""Filestore aff4:/files abstraction layer.

Filestore allows for multiple different filestore modules to register URNs
under aff4:/files to handle new file hash and new file creations.
"""

import hashlib

import logging

from grr.lib import fingerprint
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard as aff4_standard
from grr.lib.rdfvalues import nsrl as rdf_nsrl


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

  def AddFile(self, fd, sync=False, external=True):
    """Create a new file in the file store.

    We delegate the actual file addition to our contained
    implementations. Implementations can either implement the AddFile() method,
    returning a file like object which will be written on, or directly support
    the AddBlobToStore() method which can copy the VFSBlobImage efficiently.

    Args:
      fd: An AFF4 object open for read/write.
      sync: Should the file be synced immediately.
      external: If true, attempt to add files to stores defined as EXTERNAL.
    """
    files_for_write = []

    for sub_store in self.GetChildrenByPriority(allow_external=external):
      new_file = sub_store.AddFile(fd, sync=sync)
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
      child.Close(sync=sync)

  def FindFile(self, fd, external=True):
    """Find an AFF4Stream in the file store.

    We delegate the actual file search to our contained
    implementations. Implementations need to implement the FindFile() method,
    which will return either a list of RDFURN's or a RDFURN.

    Args:
      fd: File open for reading.
      external: If true, attempt to check stores defined as EXTERNAL.

    Returns:
      A list of RDFURNs returned by the contained implementations.
    """
    return_list = []
    for sub_store in self.GetChildrenByPriority(allow_external=external):
      found = sub_store.FindFile(fd)
      if found:
        if isinstance(found, list):
          return_list.extend(found)
        else:
          return_list.append(found)

    return return_list

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    ACTIVE = aff4.Attribute("aff4:filestore_active",
                            rdfvalue.RDFBool,
                            "If true this filestore is active.",
                            default=True)


class FileStoreImage(aff4_grr.VFSBlobImage):
  """The AFF4 files that are stored in the file store area.

  Files in the file store are essentially blob images, containing indexes to the
  client files which matches their hash.

  It is possible to query for all clients which match a specific hash or a
  prefix of the aff4 path to the files on these clients.

  e.g. on the console, you can query for all clients with a hash like this:

  In [31]: fd = aff4.FACTORY.Open("aff4:/files/hash/generic/sha256/2663a09072b9e
  a027ff1e3e3d21d351152c2534c2fe960a765c5321bfb7b6b25")

  In [32]: list(fd.Query("aff4:/C"))
  Out[32]: [<aff4:/C.f2614de8d636797e/fs/os/usr/share/gimp/2.0/images/wilber.png
  age=1970-01-01 00:00:00>]
  """

  class SchemaCls(aff4_grr.VFSBlobImage.SchemaCls):
    # The file store does not need to version file content.
    HASHES = aff4.Attribute("aff4:hashes",
                            aff4_standard.HashList,
                            "List of hashes of each chunk in this file.",
                            versioned=False)

  def AddIndex(self, target):
    """Adds an indexed reference to the target URN."""
    if "w" not in self.mode:
      raise IOError("FileStoreImage %s is not in write mode.", self.urn)
    predicate = ("index:target:%s" % target).lower()
    data_store.DB.MultiSet(self.urn, {predicate: target},
                           token=self.token,
                           replace=True,
                           sync=False)

  def Query(self, target_prefix="", limit=100):
    """Search the index for matches starting with target_prefix.

    Args:
       target_prefix: The prefix to match against the index.

       limit: Either a tuple of (start, limit) or a maximum number of results to
         return.

    Yields:
      URNs of files which have the same data as this file - as read from the
      index.
    """
    # Make the full prefix.
    prefix = ["index:target:%s" % target_prefix.lower()]
    if isinstance(limit, (tuple, list)):
      start, length = limit  # pylint: disable=unpacking-non-sequence

    else:
      start = 0
      length = limit

    # Get all the unique hits
    for i, (_, hit, _) in enumerate(data_store.DB.ResolvePrefix(
        self.urn, prefix, token=self.token,
        limit=limit)):

      if i < start:
        continue

      if i >= start + length:
        break

      yield rdfvalue.RDFURN(hit)


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

    relative_name = self.RelativeName(HashFileStore.PATH)
    if not relative_name:
      raise ValueError("URN %s is not a hash file store urn. Hash file store "
                       "urn should start with %s." %
                       (str(self), str(HashFileStore.PATH)))

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
  HASH_TYPES = {"generic": ["md5", "sha1", "sha256", "SignedData"],
                "pecoff": ["md5", "sha1"]}
  FILE_HASH_TYPE = FileStoreHash

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
        hash_map[aff4.ROOT_URN.Add("files/hash/generic/sha256").Add(str(
            hsh.sha256))] = hsh

    for metadata in aff4.FACTORY.Stat(list(hash_map), token=self.token):
      yield metadata["urn"], hash_map[metadata["urn"]]

  def _GetHashers(self, hash_types):
    return [getattr(hashlib, hash_type) for hash_type in hash_types
            if hasattr(hashlib, hash_type)]

  def _HashFile(self, fd):
    """Look for the required hashes in the file."""
    hashes = fd.Get(fd.Schema.HASH)
    if hashes:
      found_all = True
      for fingerprint_type, hash_types in self.HASH_TYPES.iteritems():
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
            hashes.signed_data.Append(revision=signed_data[0],
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

    try:
      fd.Set(hashes)
    except IOError:
      pass
    return hashes

  def AddFile(self, fd, sync=False):
    """Hash the content of an AFF4Stream and create FileStoreImage objects.

    We take a file in the client space:
      aff4:/C.123123123/fs/os/usr/local/blah

    Hash it, update the hash in the original file if its different to the
    one calculated on the client, and create FileStoreImages at the following
    URNs (if they don't already exist):

      aff4:/files/hash/generic/sha256/123123123 (canonical reference)
      aff4:/files/hash/generic/sha1/345345345
      aff4:/files/hash/generic/md5/456456456
      aff4:/files/hash/pecoff/md5/aaaaaaaa (only for PEs)
      aff4:/files/hash/pecoff/sha1/bbbbbbbb (only for PEs)

    When present in PE files, the signing data (revision, cert_type,
    certificate) is added to the original client-space blobimage.

    This can't be done simply in the FileStore.Write() method with fixed hash
    buffer sizes because the authenticode hashes need to track hashing of
    different-sized regions based on the signature information.

    Args:
      fd: File open for reading.
      sync: Should the file be synced immediately.

    Raises:
      IOError: If there was an error writing the file.
    """
    file_store_files = []

    hashes = self._HashFile(fd)

    # The empty file is very common, we don't keep the back references for it
    # in the DB since it just takes up too much space.
    empty_hash = ("e3b0c44298fc1c149afbf4c8996fb924"
                  "27ae41e4649b934ca495991b7852b855")
    if hashes.sha256 == empty_hash:
      return

    for hash_type, hash_digest in hashes.ListSetFields():

      # Determine fingerprint type.
      hash_digest = str(hash_digest)
      hash_type = hash_type.name
      fingerprint_type = "generic"
      if hash_type.startswith("pecoff_"):
        fingerprint_type = "pecoff"
        hash_type = hash_type[len("pecoff_"):]
      if hash_type not in self.HASH_TYPES[fingerprint_type]:
        continue

      # These files are all created through async write so they should be
      # fast.
      file_store_urn = self.PATH.Add(fingerprint_type).Add(hash_type).Add(
          hash_digest)

      file_store_fd = aff4.FACTORY.Create(file_store_urn,
                                          FileStoreImage,
                                          mode="w",
                                          token=self.token)
      file_store_fd.FromBlobImage(fd)
      file_store_fd.AddIndex(fd.urn)

      file_store_files.append(file_store_fd)

    # Write the hashes attribute to all the created files..
    for file_store_fd in file_store_files:
      file_store_fd.Set(hashes)
      file_store_fd.Close(sync=sync)

    # We do not want to be externally written here.
    return None

  def FindFile(self, fd):
    """Find an AFF4Stream in the file store.

    We take a file in the client space:
      aff4:/C.123123123/fs/os/usr/local/blah

    Hash it and then find the matching RDFURN's:

      aff4:/files/hash/generic/sha256/123123123 (canonical reference)
      aff4:/files/hash/generic/sha1/345345345
      aff4:/files/hash/generic/md5/456456456
      aff4:/files/hash/pecoff/md5/aaaaaaaa (only for PEs)
      aff4:/files/hash/pecoff/sha1/bbbbbbbb (only for PEs)

    Args:
      fd: File open for reading.

    Returns:
      A list of RDFURN's corresponding to the input file.
    """
    hashes = self._HashFile(fd)

    urns_to_check = []

    for hash_type, hash_digest in hashes.ListSetFields():
      hash_digest = str(hash_digest)
      hash_type = hash_type.name

      fingerprint_type = "generic"
      if hash_type.startswith("pecoff_"):
        fingerprint_type = "pecoff"
        hash_type = hash_type[len("pecoff_"):]
      if hash_type not in self.HASH_TYPES[fingerprint_type]:
        continue

      file_store_urn = self.PATH.Add(fingerprint_type).Add(hash_type).Add(
          hash_digest)

      urns_to_check.append(file_store_urn)

    return [data["urn"]
            for data in aff4.FACTORY.Stat(urns_to_check,
                                          token=self.token)]

  @staticmethod
  def ListHashes(token=None, age=aff4.NEWEST_TIME):
    """Yields all the hashes in the file store.

    Args:
      token: Security token, instance of ACLToken.
      age: AFF4 age specification. Only get hits corresponding to the given
           age spec. Should be aff4.NEWEST_TIME or a time range given as a
           tuple (start, end) in microseconds since Jan 1st, 1970. If just
           a microseconds value is given it's treated as the higher end of the
           range, i.e. (0, age). See aff4.FACTORY.ParseAgeSpecification for
           details.

    Yields:
      FileStoreHash instances corresponding to all the hashes in the file store.

    Raises:
      ValueError: if age was set to aff4.ALL_TIMES.
    """
    if age == aff4.ALL_TIMES:
      raise ValueError("age==aff4.ALL_TIMES is not allowed.")

    urns = []
    for fingerprint_type, hash_types in HashFileStore.HASH_TYPES.iteritems():
      for hash_type in hash_types:
        urns.append(HashFileStore.PATH.Add(fingerprint_type).Add(hash_type))

    for _, values in aff4.FACTORY.MultiListChildren(urns, token=token, age=age):
      for value in values:
        yield FileStoreHash(value)

  @classmethod
  def GetClientsForHash(cls, hash_obj, token=None, age=aff4.NEWEST_TIME):
    """Yields client_files for the specified file store hash.

    Args:
      hash_obj: RDFURN that we want to get hits for.
      token: Security token.
      age: AFF4 age specification. Only get hits corresponding to the given
           age spec. Should be aff4.NEWEST_TIME or a time range given as a
           tuple (start, end) in microseconds since Jan 1st, 1970. If just
           a microseconds value is given it's treated as the higher end of the
           range, i.e. (0, age). See aff4.FACTORY.ParseAgeSpecification for
           details.

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
      age: AFF4 age specification. Only get hits corresponding to the given
           age spec. Should be aff4.NEWEST_TIME or a time range given as a
           tuple (start, end) in microseconds since Jan 1st, 1970. If just
           a microseconds value is given it's treated as the higher end of the
           range, i.e. (0, age). See aff4.FACTORY.ParseAgeSpecification for
           details.

    Yields:
      (hash, client_files) tuples, where hash is a FILE_HASH_TYPE instance and
      client_files is a list of RDFURN's corresponding to client files that
      have the hash.

    Raises:
      ValueError: if age was set to aff4.ALL_TIMES.
    """
    if age == aff4.ALL_TIMES:
      raise ValueError("age==aff4.ALL_TIMES is not supported.")
    timestamp = aff4.FACTORY.ParseAgeSpecification(age)

    for hash_obj, client_files in data_store.DB.MultiResolvePrefix(
        hashes, "index:target:",
        token=token, timestamp=timestamp):
      yield (cls.FILE_HASH_TYPE(hash_obj), [file_urn
                                            for _, file_urn, _ in client_files])


class NSRLFileStoreHash(rdfvalue.RDFURN):
  """Urns returned from NSRLFileStore.GetClientsForHashes()."""

  def __init__(self, initializer=None, hash_value=None, age=None):
    initializer = NSRLFileStore.PATH.Add(hash_value)

    super(NSRLFileStoreHash, self).__init__(initializer=initializer, age=age)

    relative_name = self.RelativeName(NSRLFileStore.PATH)
    if not relative_name:
      raise ValueError("URN %s is not a hash file store urn. Hash file store "
                       "urn should start with %s." %
                       (str(self), str(NSRLFileStore.PATH)))

    relative_path = relative_name.split("/")
    if len(relative_path) != 1:
      raise ValueError("URN %s is not a NSRL file store urn.", str(self))
    self.hash_value = relative_path[0]
    self.fingerprint_type = "generic"
    self.hash_type = "sha1"


class NSRLFile(FileStoreImage):
  """Represents a file from the NSRL database."""

  class SchemaCls(FileStoreImage.SchemaCls):
    """Schema class for NSRLFile."""

    # We do not need child indexes since the NSRL database is quite big.
    ADD_CHILD_INDEX = False

    # Make the default SIZE argument as unversioned.
    SIZE = aff4.Attribute("aff4:size",
                          rdfvalue.RDFInteger,
                          "The total size of available data for this stream.",
                          "size",
                          default=0,
                          versioned=False)
    TYPE = aff4.Attribute("aff4:type",
                          rdfvalue.RDFString,
                          "The name of the AFF4Object derived class.",
                          "type",
                          versioned=False)
    NSRL = aff4.Attribute("aff4:nsrl",
                          rdf_nsrl.NSRLInformation,
                          versioned=False)


class NSRLFileStore(HashFileStore):
  """FileStore with NSRL hashes."""

  PATH = rdfvalue.RDFURN("aff4:/files/nsrl")
  PRIORITY = 1
  EXTERNAL = False
  FILE_HASH_TYPE = NSRLFileStoreHash

  FILE_TYPES = {"M": rdf_nsrl.NSRLInformation.FileType.MALICIOUS_FILE,
                "S": rdf_nsrl.NSRLInformation.FileType.SPECIAL_FILE,
                "": rdf_nsrl.NSRLInformation.FileType.NORMAL_FILE}

  def GetChildrenByPriority(self, allow_external=True):
    return

  @staticmethod
  def ListHashes(token=None, age=aff4.NEWEST_TIME):
    return

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
        logging.info("Checking URN %s", str(hash_urn))
        hash_map[hash_urn] = hsh

    for metadata in aff4.FACTORY.Stat(list(hash_map), token=self.token):
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

    with aff4.FACTORY.Create(file_store_urn,
                             "NSRLFile",
                             mode="w",
                             token=self.token) as fd:
      fd.Set(fd.Schema.NSRL(sha1=sha1.decode("hex"),
                            md5=md5.decode("hex"),
                            crc32=crc,
                            file_name=file_name,
                            file_size=file_size,
                            product_code=product_code_list,
                            op_system_code=op_system_code_list,
                            file_type=special_code))

  def FindFile(self, fd):
    """Hash an AFF4Stream and find the RDFURN with the same hash.

    Args:
      fd: File open for reading.

    Returns:
      A RDFURN to the file in file store or False if not found.
    """
    hashes = self._HashFile(fd)
    if not hashes:
      return False

    hash_urn = self.PATH.Add(str(hashes.sha1))

    for data in aff4.FACTORY.Stat([hash_urn], token=self.token):
      return data["urn"]

    return False

  def AddFile(self, fd, sync=False):
    """Hash the AFF4Stream and add it to the NSRLFile's index.

    We take a file in the client space:
      aff4:/C.123123123/fs/os/usr/local/blah

    Hash it and check if there is a corresponsing
    NSRLFile at the following URN:

      aff4:/files/nsrl/123123123

    Next, we add the file to the NSRL index, so we know which clients have
    the file.

    Args:
      fd: File open for reading.
      sync: Should the file be synced immediately.

    Returns:
      The URN of the NSRL file if it was found in the store.
    """
    hash_urn = self.FindFile(fd)
    if not hash_urn:
      return False

    # Open file and add 'fd' to the index.
    try:
      with aff4.FACTORY.Open(hash_urn,
                             "NSRLFile",
                             mode="w",
                             token=self.token) as hash_fd:
        hash_fd.AddIndex(fd.urn)
        return hash_urn
    except aff4.InstantiationError:
      pass
    return False


class FileStoreInit(registry.InitHook):
  """Create filestore aff4 paths."""

  pre = ["GRRAFF4Init"]

  def Run(self):
    """Create FileStore and HashFileStore namespaces."""
    try:
      filestore = aff4.FACTORY.Create(FileStore.PATH,
                                      FileStore,
                                      mode="rw",
                                      token=aff4.FACTORY.root_token)
      filestore.Close()
      hash_filestore = aff4.FACTORY.Create(HashFileStore.PATH,
                                           HashFileStore,
                                           mode="rw",
                                           token=aff4.FACTORY.root_token)
      hash_filestore.Close()
      nsrl_filestore = aff4.FACTORY.Create(NSRLFileStore.PATH,
                                           NSRLFileStore,
                                           mode="rw",
                                           token=aff4.FACTORY.root_token)
      nsrl_filestore.Close()
    except access_control.UnauthorizedAccess:
      # The aff4:/files area is ACL protected, this might not work on components
      # that have ACL enforcement.
      pass
