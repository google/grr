#!/usr/bin/env python
"""Flows for exporting data out of GRR."""



import io
import os
import zipfile

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.lib.flows.general import collectors
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class Error(Exception):
  pass


class ItemNotExportableError(Error):
  pass


def CollectionItemToAff4Path(item):
  """Converts given RDFValue to an RDFURN of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    item = item.payload

  if isinstance(item, rdf_client.StatEntry):
    return item.aff4path
  elif isinstance(item, file_finder.FileFinderResult):
    return item.stat_entry.aff4path
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return item.downloaded_file.aff4path

  raise ItemNotExportableError()


# pylint: disable=invalid-name
class RawIOBaseBridge(io.RawIOBase):
  """Bridge between python descriptor-like objects and RawIOBase interface."""

  def __init__(self, fd):  # pylint: disable=super-init-not-called
    self.fd = fd

  def writable(self):
    return True

  def seekable(self):
    return True

  def tell(self):
    return self.fd.tell()

  def seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def write(self, b):
    data = b.tobytes()
    self.fd.write(data)
    return len(data)

  def close(self):
    self.fd.close()

  def flush(self):
    self.fd.flush()
# pylint: enable=invalid-name


class ExportCollectionFilesAsArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExportCollectionFilesAsArchiveArgs


class ExportCollectionFilesAsArchive(flow.GRRFlow):
  """Downloads files referenced in a collection to a zip or tar file."""

  args_type = ExportCollectionFilesAsArchiveArgs

  BATCH_SIZE = 5000

  ACL_ENFORCED = False

  def ResultsToUrns(self, results):
    for result in results:
      try:
        yield CollectionItemToAff4Path(result)
      except ItemNotExportableError:
        pass

  def DownloadCollectionFiles(self, collection, output_writer, prefix):
    """Download all files from the collection and deduplicate along the way."""

    hashes = set()
    batch_index = 0
    for fd_urn_batch in utils.Grouper(
        self.ResultsToUrns(collection), self.BATCH_SIZE):

      for fd in aff4.FACTORY.MultiOpen(fd_urn_batch, token=self.token):
        self.HeartBeat()
        self.state.total_files += 1

        # Any file-like object with data in AFF4 should inherit AFF4Stream.
        if isinstance(fd, aff4.AFF4Stream):
          archive_path = os.path.join(prefix, *fd.urn.Split())

          sha256_hash = fd.Get(fd.Schema.HASH, rdf_crypto.Hash()).sha256
          if not sha256_hash:
            continue
          self.state.archived_files += 1

          content_path = os.path.join(prefix, "hashes", str(sha256_hash))
          if sha256_hash not in hashes:
            # Make sure size of the original file is passed. It's required
            # when output_writer is StreamingTarWriter.
            st = os.stat_result((0644, 0, 0, 0, 0, 0, fd.size, 0, 0, 0))
            output_writer.WriteFromFD(fd, content_path, st=st)
            hashes.add(sha256_hash)

          up_prefix = "../" * len(fd.urn.Split())
          output_writer.WriteSymlink(up_prefix + content_path, archive_path)

      batch_index += 1
      self.Log("Processed batch %d (batch size %d).", batch_index,
               self.BATCH_SIZE)

  @flow.StateHandler(next_state="CreateArchive")
  def Start(self):
    """Register state variables and proceed to download the files."""

    # TODO(user): URN hackery should go away after ACL system is refactored.
    first_component = self.args.collection_urn.Split()[0]
    if first_component == "hunts":
      pass
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(first_component):
      data_store.DB.security_manager.CheckClientAccess(self.token.RealUID(),
                                                       first_component)
    else:
      raise access_control.UnauthorizedAccess(
          "Collection URN points to neither clients nor hunts "
          "namespaces: %s" % utils.SmartStr(self.args.collection_urn))

    self.state.Register("total_files", 0)
    self.state.Register("archived_files", 0)
    self.state.Register("output_archive_urn", None)
    self.state.Register("output_size", 0)

    # The actual work is done on the workers.
    self.CallState(next_state="CreateArchive")

  @flow.StateHandler()
  def CreateArchive(self, _):
    # Create an output zip or tar file in the temp space.
    with aff4.FACTORY.Create(None,
                             standard.TempImageFile,
                             token=self.token) as outfd:
      if self.args.format == self.args.ArchiveFormat.ZIP:
        file_extension = "zip"
      elif self.args.format == self.args.ArchiveFormat.TAR_GZ:
        file_extension = "tar.gz"
      else:
        raise ValueError("Unknown archive format: %s" % self.args.format)

      outfd.urn = outfd.urn.Add("%s_%X%X.%s" % (self.args.target_file_prefix,
                                                utils.PRNG.GetULong(),
                                                utils.PRNG.GetULong(),
                                                file_extension))

      self.Log("Will create output on %s" % outfd.urn)
      self.state.output_archive_urn = outfd.urn

      collection = aff4.FACTORY.Open(self.args.collection_urn, token=self.token)

      buffered_outfd = io.BufferedWriter(
          RawIOBaseBridge(outfd),
          buffer_size=1024 * 1024 * 12)
      if self.args.format == self.args.ArchiveFormat.ZIP:
        streaming_writer = utils.StreamingZipWriter(buffered_outfd, "w",
                                                    zipfile.ZIP_DEFLATED)
      elif self.args.format == self.args.ArchiveFormat.TAR_GZ:
        streaming_writer = utils.StreamingTarWriter(buffered_outfd, "w:gz")
      else:
        raise ValueError("Unknown archive format: %s" % self.args.format)

      with streaming_writer:
        self.DownloadCollectionFiles(collection, streaming_writer,
                                     self.args.target_file_prefix)

      self.state.output_size = rdfvalue.ByteSize(outfd.size)

  @flow.StateHandler()
  def End(self):
    self.Notify("DownloadFile", self.state.output_archive_urn,
                "%s (archived %d out of %d results, archive size is %s)" %
                (self.args.notification_message, self.state.archived_files,
                 self.state.total_files, self.state.output_size))

    # TODO(user): it would be better to provide a direct download link in the
    # email here, but it requires more work.  The notifications bar creates and
    # submits a form in javascript to achieve the same thing.
    template = """
  <html><body>
  <p>
    %(notification_message)s: archived %(archived)s of %(total)s files.
    Check the <a href='%(admin_ui)s/'>GRR notification bar</a> for
    download links.
  </p>

  <p>Thanks,</p>
  <p>%(signature)s</p>
  </body></html>"""

    subject = "%s." % self.args.notification_message

    creator = self.state.context.creator
    email_alerts.EMAIL_ALERTER.SendEmail(
        "%s@%s" % (creator, config_lib.CONFIG.Get("Logging.domain")),
        "grr-noreply@%s" % config_lib.CONFIG.Get("Logging.domain"),
        subject,
        template % dict(notification_message=self.args.notification_message,
                        archived=self.state.archived_files,
                        total=self.state.total_files,
                        admin_ui=config_lib.CONFIG["AdminUI.url"],
                        signature=config_lib.CONFIG["Email.signature"]),
        is_html=True)
