#!/usr/bin/env python
"""Flows for exporting data out of GRR."""



import io
import os
import zipfile

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class Error(Exception):
  pass


class ItemNotExportableError(Error):
  pass


def CollectionItemToAff4Path(item):
  if isinstance(item, rdfvalue.GrrMessage):
    item = item.payload

  if isinstance(item, rdfvalue.StatEntry):
    return item.aff4path
  elif isinstance(item, rdfvalue.FileFinderResult):
    return item.stat_entry.aff4path
  else:
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


class ExportHuntResultsFilesAsZipArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ExportHuntResultsFilesAsZipArgs


class ExportHuntResultFilesAsZip(flow.GRRFlow):
  """Downloads files found by the hunt to a zip file."""

  ACL_ENFORCED = False
  args_type = ExportHuntResultsFilesAsZipArgs

  BATCH_SIZE = 1024

  def ResultsToUrns(self, results):
    for result in results:
      try:
        yield CollectionItemToAff4Path(result)
      except ItemNotExportableError:
        pass

  def DownloadCollectionFiles(self, collection, output_zip, prefix):
    """Download all files from the collection and deduplicate along the way."""

    hashes = set()
    for fd_urn_batch in utils.Grouper(self.ResultsToUrns(collection),
                                      self.BATCH_SIZE):
      self.HeartBeat()

      for fd in aff4.FACTORY.MultiOpen(fd_urn_batch, token=self.token):
        self.state.total_files += 1

        # Any file-like object with data in AFF4 should inherit AFF4Stream.
        if isinstance(fd, aff4.AFF4Stream):
          archive_path = os.path.join(prefix, *fd.urn.Split())
          self.state.archived_files += 1

          sha256_hash = fd.Get(fd.Schema.HASH, rdfvalue.Hash()).sha256
          if not sha256_hash or not self.args.deduplicate:
            self.Log("Written " + archive_path)
            output_zip.WriteFromFD(fd, archive_path, self.state.compression)
            continue

          content_path = os.path.join(prefix, "hashes", str(sha256_hash))
          if sha256_hash not in hashes:
            output_zip.WriteFromFD(fd, content_path, self.state.compression)
            hashes.add(sha256_hash)
            self.Log("Written contents: " + content_path)

          up_prefix = "../" * len(fd.urn.Split())
          output_zip.WriteSymlink(up_prefix + content_path, archive_path)
          self.Log("Written symlink %s -> %s", archive_path,
                   up_prefix + content_path)

  @flow.StateHandler(next_state="CreateZipFile")
  def Start(self):
    """Find a hunt, check permissions and proceed to download the files."""

    # Check permissions first, and if ok, just proceed.
    data_store.DB.security_manager.CheckHuntAccess(
        self.token.RealUID(), self.args.hunt_urn)

    self.state.Register("compression", zipfile.ZIP_DEFLATED)
    self.state.Register("total_files", 0)
    self.state.Register("archived_files", 0)
    self.state.Register("output_zip_urn", None)

    # The actual work is done on the workers.
    self.CallState(next_state="CreateZipFile")

  @flow.StateHandler()
  def CreateZipFile(self, _):
    # Create an output zip file in the temp space.
    with aff4.FACTORY.Create(None, "TempImageFile", token=self.token) as outfd:
      friendly_hunt_name = self.args.hunt_urn.Basename().replace(":", "_")
      outfd.urn = outfd.urn.Add("hunt_%s_%X%X.zip" % (
          friendly_hunt_name, utils.PRNG.GetULong(), utils.PRNG.GetULong()))

      self.Log("Will create output on %s" % outfd.urn)
      self.state.output_zip_urn = outfd.urn

      hunt = aff4.FACTORY.Open(self.args.hunt_urn, aff4_type="GRRHunt",
                               token=self.token)
      hunt_output_urn = hunt.state.context.results_collection_urn

      collection = aff4.FACTORY.Open(
          hunt_output_urn, aff4_type="RDFValueCollection",
          token=self.token)

      buffered_outfd = io.BufferedWriter(RawIOBaseBridge(outfd),
                                         buffer_size=1024 * 1024 * 12)
      with utils.StreamingZipWriter(buffered_outfd, "w",
                                    zipfile.ZIP_DEFLATED) as output_zip:
        self.DownloadCollectionFiles(collection, output_zip, friendly_hunt_name)

  @flow.StateHandler()
  def End(self):
    self.Notify("DownloadFile", self.state.output_zip_urn,
                "Hunt results ready for download (archived %d out of %d "
                "results)" % (self.state.archived_files,
                              self.state.total_files))

    # TODO(user): it would be better to provide a direct download link in the
    # email here, but it requires more work.  The notifications bar creates and
    # submits a form in javascript to achieve the same thing.
    template = """
  <html><body>
  <p>
    The zip archive contains %(archived)s of %(total)s files for hunt
    %(hunt_id)s.  Check the <a href='%(admin_ui)s/'>GRR notification bar</a> for
    download links.
  </p>

  <p>Thanks,</p>
  <p>%(signature)s</p>
  </body></html>"""

    subject = "Hunt results for %s ready for download." % (
        self.args.hunt_urn.Basename())

    if self.token.username != "GRRWorker":

      email_alerts.SendEmail(
          "%s@%s" % (
              self.token.username, config_lib.CONFIG.Get("Logging.domain")),
          "grr-noreply@%s" % config_lib.CONFIG.Get("Logging.domain"), subject,
          template % dict(
              hunt_id=self.args.hunt_urn.Basename(),
              archived=self.state.archived_files,
              total=self.state.total_files,
              admin_ui=config_lib.CONFIG["AdminUI.url"],
              signature=config_lib.CONFIG["Email.signature"]),
          is_html=True)

