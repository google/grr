#!/usr/bin/env python
"""A module with the blob sink."""

import logging

from grr_response_server import data_store
from grr_response_server.sinks import abstract
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2


class BlobSink(abstract.Sink):
  """A sink that accepts blobs (e.g. file parts) from the GRR agents."""

  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    blob = rrg_blob_pb2.Blob()
    blob.ParseFromString(parcel.payload.value)

    logging.info(
        "Received a blob of %s bytes from '%s'",
        len(blob.data),
        client_id,
    )

    assert data_store.BLOBS is not None
    data_store.BLOBS.WriteBlobWithUnknownHash(blob.data)
