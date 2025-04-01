#!/usr/bin/env python
"""A BlobStore backed by Google Cloud Storage."""

from collections.abc import Iterable
import logging
from typing import Optional

from google.cloud import exceptions
from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY

from grr_response_core import config
from grr_response_server import blob_store
from grr_response_server.models import blobs as models_blobs


class ConfigError(Exception):
  """Raised when the GCS blob store config is invalid."""


class GCSBlobStore(blob_store.BlobStore):
  """A BlobStore implementation backed by Google Cloud Storage."""

  def __init__(self):
    """Instantiates a new GCSBlobStore."""

    for var in ("Blobstore.gcs.project", "Blobstore.gcs.bucket"):
      if not config.CONFIG[var]:
        raise ConfigError(f"Missing config value for {var}")

    project = config.CONFIG["Blobstore.gcs.project"]
    bucket_name = config.CONFIG["Blobstore.gcs.bucket"]
    blob_prefix = config.CONFIG["Blobstore.gcs.blob_prefix"]

    self._client = storage.Client(project=project)

    self._bucket = self._client.bucket(bucket_name)
    self._blob_prefix = blob_prefix

  def _GetFilename(self, blob_id: models_blobs.BlobID) -> str:
    hex_blob_id = bytes(blob_id).hex()
    return f"{self._blob_prefix}{hex_blob_id}"

  def WriteBlobs(
      self, blob_id_data_map: dict[models_blobs.BlobID, bytes]
  ) -> None:
    """Creates or overwrites blobs."""
    for blob_id, blob in blob_id_data_map.items():
      filename = self._GetFilename(blob_id)

      try:
        b = self._bucket.blob(filename)
        try:
          # Overwriting existing blobs may cause GCS to throttle our requests.
          # That is particularly bad, since write requests run on the
          # (Fleetspeak) message receipt hot path, but will thus get semi-stuck
          # in a throttling-induced-error/retry cycle. To mitigate that, we'll
          # only go ahead with the upload if we couldn't successfully determine
          # that the blob was already present in the blob store bucket.
          # Note: using a try/catch-all block here because we only care if the
          # blob existence check is successful or not; on any error, we'll just
          # proceed with the upload.
          if b.exists():
            continue
        except Exception as e:  # pylint: disable=broad-exception-caught
          logging.error(
              "Error while checking if blob %s exists: %s", blob_id, e
          )
        logging.debug("Writing blob '%s' as '%s'", blob_id, filename)
        b.upload_from_string(
            data=blob,
            content_type="application/octet-stream",
            retry=DEFAULT_RETRY,
        )
      except Exception as e:  # pylint: disable=broad-exception-caught
        logging.exception(
            "Unable to write blob %s to datastore, %s", blob_id, e
        )

  def ReadBlob(self, blob_id: models_blobs.BlobID) -> Optional[bytes]:
    """Reads the blob contexts, identified by the given BlobID."""
    filename = self._GetFilename(blob_id)
    try:
      b = self._bucket.blob(filename)
      return b.download_as_bytes(retry=DEFAULT_RETRY)
    except exceptions.NotFound:
      return None
    except Exception as e:
      logging.error("Unable to read blob %s, %s", blob_id, e)
      raise

  def ReadBlobs(
      self, blob_ids: Iterable[models_blobs.BlobID]
  ) -> dict[models_blobs.BlobID, Optional[bytes]]:
    """Reads all blobs, specified by blob_ids, returning their contents."""
    return {blob_id: self.ReadBlob(blob_id) for blob_id in blob_ids}

  def CheckBlobExists(self, blob_id: models_blobs.BlobID) -> bool:
    """Checks if a blob with a given BlobID exists."""
    filename = self._GetFilename(blob_id)
    try:
      b = self._bucket.blob(filename)
      return b.exists(retry=DEFAULT_RETRY)
    except Exception as e:
      logging.error("Unable to check for blob %s, %s", blob_id, e)
      raise

  def CheckBlobsExist(
      self, blob_ids: Iterable[models_blobs.BlobID]
  ) -> dict[models_blobs.BlobID, bool]:
    """Checks if blobs for the given identifiers already exist."""
    return {blob_id: self.CheckBlobExists(blob_id) for blob_id in blob_ids}
