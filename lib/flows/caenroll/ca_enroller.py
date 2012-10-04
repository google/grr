#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A flow to enrol new clients."""


from hashlib import sha256
import time


from M2Crypto import ASN1
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509
from grr.client import conf as flags

import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import key_utils
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_string("ca", "ca.key",
                    "The location of the CA key file.")

FLAGS = flags.FLAGS

# Store the CA key as a global for reuse.
CA_KEY = None


class CAEnroler(flow.GRRFlow):
  """Enrol new clients."""

  flow_typeinfo = {"csr": type_info.Proto(jobs_pb2.Certificate)}

  def __init__(self, csr=None, _client=None, *args, **kwargs):
    """Start an enrollment flow with the client.

    Args:
      csr: A Certificate protobuf with the CSR in it.
      _client: The client AFF4 Object.
      *args: passthrough to base class
      **kwargs: passthrough to base class
    """
    self.csr = csr
    self.client = _client
    flow.GRRFlow.__init__(self, *args, **kwargs)

  @flow.StateHandler(next_state="End")
  def Start(self):
    """Sign the CSR from the client."""
    if self.csr.type != jobs_pb2.Certificate.CSR:
      raise IOError("Must be called with CSR")

    req = X509.load_request_string(self.csr.pem)

    # Verify that the CN is of the correct form
    public_key = req.get_pubkey().get_rsa().pub()[1]
    self.cn = "C.%s" % (
        sha256(public_key).digest()[:8].encode("hex"))
    if self.cn != req.get_subject().CN:
      raise IOError("CSR CN does not match public key.")

    logging.info("Will sign CSR for: %s", self.cn)

    cert = self.MakeCert(req)

    # This check is important to ensure that the client id reported in the
    # source of the enrollment request is the same as the one in the
    # certificate.
    if self.cn != self.client_id:
      raise flow.FlowError("Certificate name %s mismatch for client %s",
                           self.cn, self.client_id)

    # Set and write the certificate to the client record.
    certificate_attribute = aff4.FACTORY.RDFValue("RDFX509Cert")(cert.as_pem())
    self.client.Set(self.client.Schema.CERT, certificate_attribute)
    self.client.Close(sync=True)

    # Publish the client enrollment message.
    self.Publish("ClientEnrollment", certificate_attribute.AsProto())

    self.Log("Enrolled %s successfully", self.client_id)

    # This is needed for backwards compatibility.
    # TODO(user): Remove this once all clients are > 2200.
    self.CallClient("SaveCert", pem=cert.as_pem(),
                    type=jobs_pb2.Certificate.CRT, next_state="End")

    # We can not pickle protobufs
    self.csr = None

  def MakeCert(self, req):
    """Make new cert for the client."""
    # code inspired by M2Crypto unit tests

    cert = X509.X509()
    # Use the client CN for a cert serial_id. This will ensure we do
    # not have clashing cert id.
    cert.set_serial_number(int(self.cn.split(".")[1], 16))
    cert.set_version(2)
    cert.set_subject(req.get_subject())
    t = long(time.time()) - 10
    now = ASN1.ASN1_UTCTIME()
    now.set_time(t)
    now_plus_year = ASN1.ASN1_UTCTIME()
    now_plus_year.set_time(t + 60 * 60 * 24 * 365)

    # TODO(user): Enforce certificate expiry time, and when close
    # to expiry force client re-enrolment
    cert.set_not_before(now)
    cert.set_not_after(now_plus_year)

    # Get the CA issuer:
    ca_data = key_utils.GetCert(FLAGS.ca)
    ca_cert = X509.load_cert_string(ca_data)
    cert.set_issuer(ca_cert.get_issuer())
    cert.set_pubkey(req.get_pubkey())

    ca_key = RSA.load_key_string(ca_data)
    key_pair = EVP.PKey(md="sha256")
    key_pair.assign_rsa(ca_key)

    # Sign the certificate
    cert.sign(key_pair, "sha256")

    return cert


enrolment_cache = utils.FastStore(5000)


class Enroler(flow.WellKnownFlow):
  """Manage enrolment requests."""
  well_known_session_id = "CA:Enrol"

  def ProcessMessage(self, message):
    """Begins an enrollment flow for this client.

    Args:
        message: The Certificate sent by the client. Note that this
        message is not authenticated.
    """
    cert = jobs_pb2.Certificate()
    cert.ParseFromString(message.args)

    queue_name, _ = self.well_known_session_id.split(":", 1)

    client_id = message.source

    # It makes no sense to enrol the same client multiple times, so we
    # eliminate duplicates. Note, that we can still enroll clients multiple
    # times due to cache expiration or using multiple enrollers.
    try:
      enrolment_cache.Get(client_id)
      return
    except KeyError:
      enrolment_cache.Put(client_id, 1)

    # Create a new client object for this client.
    client = aff4.FACTORY.Create(client_id, "VFSGRRClient", mode="rw",
                                 token=self.token)

    # Only enroll this client if it has no certificate yet.
    if not client.Get(client.Schema.CERT):
      # Start the enrollment flow for this client.
      flow.FACTORY.StartFlow(client_id=client_id, flow_name="CAEnroler",
                             csr=cert, queue_name=queue_name,
                             _client=client, token=self.token)
