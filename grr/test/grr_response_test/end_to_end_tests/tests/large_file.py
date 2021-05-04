#!/usr/bin/env python
"""End-to-end tests for the large file collection flow."""
import contextlib
import datetime
import io
from typing import IO
from typing import Iterator
from typing import NamedTuple

from absl import flags
from absl.testing import absltest
from google.cloud import storage
import requests

from grr_response_core.lib.util import aead
from grr_response_core.lib.util import io as ioutil
from grr_response_proto import jobs_pb2
from grr_response_proto import large_file_pb2
from grr_response_test.end_to_end_tests import test_base

# TODO: Get rid of these flags (e.g. by including credentials into
# a resource file in the repository).

FLAG_gcs_creds_file = flags.DEFINE_string(
    name="gcs_creds_file",
    default="",
    help="A path to the JSON file with credentials to the GCS service account.",
)

FLAG_gcs_bucket = flags.DEFINE_string(
    name="gcs_bucket",
    default="",
    help="A name of the GCS bucket to use.",
)


class TestCollectLargeFileLinux(test_base.EndToEndTest):
  """A class for Linux-specific large file collection tests."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testBinBash(self):
    signed_url = SignedURL.Generate(prefix="bash")

    args = large_file_pb2.CollectLargeFileFlowArgs()
    args.path_spec.pathtype = jobs_pb2.PathSpec.OS
    args.path_spec.path = "/bin/bash"
    args.signed_url = signed_url.writer

    flow = self.RunFlowAndWait("CollectLargeFileFlow", args=args).Get()
    encrypytion_key = flow.GetLargeFileEncryptionKey()

    with Stream(signed_url.reader, encrypytion_key) as stream:
      content = stream.read()

    # Bash executable should have the "GNU bash" string somewhere inside (e.g.
    # for the help purposes).
    self.assertIn("GNU bash".encode("ascii"), content)


class TestCollectLargeFileWindows(test_base.EndToEndTest):
  """A class for Windows-specific large file collection tests."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testSystem32MRT(self):
    signed_url = SignedURL.Generate(prefix="MRT")

    args = large_file_pb2.CollectLargeFileFlowArgs()
    args.path_spec.pathtype = jobs_pb2.PathSpec.OS
    args.path_spec.path = r"C:\Windows\System32\MRT.exe"
    args.signed_url = signed_url.writer

    flow = self.RunFlowAndWait("CollectLargeFileFlow", args=args).Get()
    encryption_key = flow.GetLargeFileEncryptionKey()

    with Stream(signed_url.reader, encryption_key) as stream:
      content = stream.read(1 << 20)

    # Microsoft Removal Tool should have plenty of references to "Microsoft"
    # inside its binary code.
    self.assertIn("Microsoft".encode("ascii"), content)

  def testMFT(self):
    signed_url = SignedURL.Generate(prefix="$MFT")

    args = large_file_pb2.CollectLargeFileFlowArgs()
    args.path_spec.pathtype = jobs_pb2.PathSpec.NTFS
    args.path_spec.path = r"C:\$MFT"
    args.signed_url = signed_url.writer

    flow = self.RunFlowAndWait("CollectLargeFileFlow", args=args).Get()
    encryption_key = flow.GetLargeFileEncryptionKey()

    with Stream(signed_url.reader, encryption_key) as stream:
      content = stream.read(32 * 1024 * 1024)

    # Each MFT file has a "FILE" magic at the beginning.
    self.assertStartsWith(content, b"FILE")

    # It should also have references to Windows somewhere.
    self.assertIn("Windows".encode("ascii"), content)


class SignedURL(NamedTuple):
  """A signed URL pair for reading and writing to the same object."""
  reader: str
  writer: str

  @classmethod
  def Generate(cls, prefix: str) -> "SignedURL":
    """Generates a signed URL pair to a unique resource.

    Args:
      prefix: A prefix for the name of the file.

    Returns:
      A signed URL pair.
    """
    if not FLAG_gcs_creds_file.value:
      raise absltest.SkipTest("GCS credentials file not specified")
    if not FLAG_gcs_bucket.value:
      raise absltest.SkipTest("GCS bucket not specified")

    now = datetime.datetime.now()

    client = storage.Client.from_service_account_json(FLAG_gcs_creds_file.value)
    bucket = client.bucket(FLAG_gcs_bucket.value)
    blob = bucket.blob(f"{prefix}_{now.strftime('%Y%m%d_%H%M_%S')}")

    reader = blob.generate_signed_url(
        version="v4",
        method="GET",
        expiration=datetime.timedelta(hours=6),
    )

    writer = blob.generate_signed_url(
        version="v4",
        method="RESUMABLE",
        expiration=datetime.timedelta(hours=6),
    )

    return SignedURL(reader=reader, writer=writer)


@contextlib.contextmanager
def Stream(url: str, encryption_key: bytes) -> Iterator[IO[bytes]]:
  """Streams a decrypted large file from the given URL."""
  with requests.get(url, stream=True) as streamer:
    stream = ioutil.Unchunk(streamer.iter_content(io.DEFAULT_BUFFER_SIZE))
    yield aead.Decrypt(stream, encryption_key)
