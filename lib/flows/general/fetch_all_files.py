#!/usr/bin/env python
"""Find certain types of files, compute hashes, and fetch unknown ones."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class FetchAllFiles(flow.GRRFlow):
  """This flow finds files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/fp/(generic|pecoff)/<hashname>/<hashvalue>.
  There may also be a symlink from the original file to the retrieved
  content.
  """

  category = "/Filesystem/"
  CHUNK_SIZE = 512 * 1024
  _MAX_FETCHABLE_SIZE = 100 * 1024 * 1024

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Bool(
          description=("This causes the computation of Authenticode "
                       "hashes, and their use for deduplicating file fetches."),
          name="pecoff",
          default=True),

      type_info.FindSpecType(
          description=("Which files to search for. The default is to search "
                       "the entire system for files with an executable "
                       "extension."),
          name="findspec",
          default=rdfvalue.RDFFindSpec(
              pathspec=rdfvalue.PathSpec(
                  path="/",
                  pathtype=rdfvalue.PathSpec.PathType.OS),
              path_regex=r"\.(exe|com|bat|dll|msi|sys|scr|pif)$")
          ),
      )

  @flow.StateHandler(next_state="IterateFind")
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_found", 0)
    self.state.Register("files_hashed", 0)
    self.state.Register("files_to_fetch", 0)
    self.state.Register("files_fetched", 0)
    self.state.Register("fd_store", {})

    self.CallClient("Find", self.state.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["IterateFind", "CheckFingerprint"])
  def IterateFind(self, responses):
    """Iterate through find responses, and spawn fingerprint requests."""
    if not responses.success:
      # We just stop the find iteration, the flow goes on.
      self.Log("Failed Find: %s", responses.status)
      return

    for response in responses:
      # Create the file in the VFS
      vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          response.hit.pathspec, self.client_id)
      response.hit.aff4path = utils.SmartUnicode(vfs_urn)

      if stat.S_ISREG(response.hit.st_mode):
        self.state.files_found += 1

        tuples = []
        tuples.append(rdfvalue.FingerprintTuple(
            fp_type=rdfvalue.FingerprintTuple.Type.FPT_GENERIC,
            hashers=[rdfvalue.FingerprintTuple.Hash.SHA256]))

        if self.state.pecoff:
          tuples.append(rdfvalue.FingerprintTuple(
              fp_type=rdfvalue.FingerprintTuple.Type.FPT_PE_COFF,
              hashers=[rdfvalue.FingerprintTuple.Hash.MD5,
                       rdfvalue.FingerprintTuple.Hash.SHA1]))

        fingerspec = rdfvalue.FingerprintRequest(pathspec=response.hit.pathspec,
                                                 tuples=tuples)

        self.CallClient("FingerprintFile", fingerspec,
                        next_state="CheckFingerprint",
                        request_data=dict(hit=response.hit))

    # In the future, might talk to parent to tell number of file stated / bytes
    # hashed / bytes fetched, so that the hunt knows what's going on?
    if responses.iterator.state != rdfvalue.Iterator.State.FINISHED:
      self.state.findspec.iterator.CopyFrom(responses.iterator)
      self.CallClient("Find", self.state.findspec, next_state="IterateFind")

    else:
      self.Log("Found %d files.", self.state.files_found)

  @flow.StateHandler(next_state="WriteBuffer")
  def CheckFingerprint(self, responses):
    """Having a fingerprint, check if it is new and if so, fetch the file."""
    if not responses.success:
      # We just stop the find iteration, the flow goes on.
      self.Log("Failed Fingerprint: %s", responses.status)
      return

    # There is only one element ever.
    self.state.files_hashed += 1
    response = responses.First()
    hit = responses.request_data["hit"]
    vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        hit.pathspec, self.client_id)

    # Create the symlink for the deduped hash in the client namespace.
    fd = aff4.FACTORY.Create(vfs_urn, "VFSFileSymlink", mode="w",
                             token=self.token)
    fingerprint = fd.Schema.FINGERPRINT(response)

    fd.Set(fd.Schema.STAT(hit))
    fd.Set(fd.Schema.PATHSPEC(hit.pathspec))
    fd.Set(fingerprint)

    for fp_type, hash_type in [("pecoff", "sha1"), ("generic", "sha256")]:
      fp = fingerprint.GetFingerprint(fp_type)
      if fp is not None:
        fp_hash = fp.GetItem(hash_type)
        if fp_hash is None:
          continue

        urn = aff4.ROOT_URN.Add("FP").Add(fp_type).Add(hash_type).Add(
            fp_hash.encode("hex"))
        break

    # Set the URN for the delegate.
    fd.Set(fd.Schema.DELEGATE(urn))
    fd.Close(sync=False)

    # Let's see if the fingerprint (with content) already exists.
    # If yes, we are done.
    try:
      aff4.FACTORY.Open(urn, aff4_type="HashImage", mode="r", token=self.token)
    except IOError:
      fd = aff4.FACTORY.Create(urn, "HashImage", mode="w", token=self.token)
      fd.Set(fd.Schema.CONTENT_LOCK(self.session_id))
      fd.SetChunksize(self.CHUNK_SIZE)
      fd.Set(fingerprint)

      # Ensure we flush here as a lock on the object. There is a small race here
      # but the worst that could happen is that we fetch the same file from two
      # clients.
      fd.Flush(sync=True)

      fd_key = utils.SmartStr(urn)
      self.state.fd_store[fd_key] = fd

      # If the binary is too large we just ignore it.
      file_size = hit.st_size
      if file_size > self._MAX_FETCHABLE_SIZE:
        self.Log("%s too large to fetch. Size=%d", vfs_urn, file_size)
        return

      # We just fetch ALL the chunks now.
      self.state.files_to_fetch += 1
      offset = 0
      while offset < file_size:
        self.CallClient("TransferBuffer", pathspec=hit.pathspec, offset=offset,
                        length=self.CHUNK_SIZE, next_state="WriteBuffer",
                        request_data=dict(fd_key=fd_key, size=file_size))
        offset += self.CHUNK_SIZE

    if not int(self.state.files_hashed % 100):
      self.Log("Hashed %d files.", self.state.files_hashed)

  @flow.StateHandler()
  def WriteBuffer(self, responses):
    if not responses.success:
      # Silently ignore failures in block-fetches
      # Might want to clean up the 'broken' fingerprint file here.
      return

    response = responses.First()
    fd_key = responses.request_data["fd_key"]
    fd = self.state.fd_store.get(fd_key)
    if not fd:
      self.Log("Missing fd_key from store: %s", fd_key)
    else:
      size = responses.request_data["size"]

      fd.AddBlob(response.data, response.length)
      if response.offset + response.length >= size:
        # File done.
        del self.state.fd_store[fd_key]
        fd.Close(sync=False)
        self.state.files_fetched += 1
        if not int(self.state.files_fetched % 100):
          self.Log("Fetched %d of %d files.", self.state.files_fetched,
                   self.state.files_to_fetch)

# A cron job should check on these symlinks, and make sure the file content
# actually matches the advertised hash. Also true for hashImage files?
