#!/usr/bin/env python
"""A flow to enrol new clients."""


import time


from M2Crypto import ASN1
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509

import logging
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


config_lib.DEFINE_option(type_info.PEMPrivateKey(
    name="PrivateKeys.ca_key",
    description="CA private key. Used to sign for client enrollment.",
    ))


class CAEnroler(flow.GRRFlow):
  """Enrol new clients."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFValueType(
          name="csr",
          description="A Certificate RDFValue with the CSR in it.",
          rdfclass=rdfvalue.Certificate,
          default=None),
      )

  def InitFromArguments(self, client=None, *args, **kwargs):
    self.client = client
    super(CAEnroler, self).InitFromArguments(*args, **kwargs)

  @flow.StateHandler(next_state="End")
  def Start(self):
    """Sign the CSR from the client."""
    if self.state.csr.type != rdfvalue.Certificate.Type.CSR:
      raise IOError("Must be called with CSR")

    req = X509.load_request_string(self.state.csr.pem)

    # Verify that the CN is of the correct form. The common name should refer to
    # a client URN.
    public_key = req.get_pubkey().get_rsa().pub()[1]
    self.cn = rdfvalue.ClientURN.FromPublicKey(public_key)
    if self.cn != rdfvalue.ClientURN(req.get_subject().CN):
      raise IOError("CSR CN does not match public key.")

    logging.info("Will sign CSR for: %s", self.cn)

    cert = self.MakeCert(req)

    # This check is important to ensure that the client id reported in the
    # source of the enrollment request is the same as the one in the
    # certificate. We use the ClientURN to ensure this is also of the correct
    # form for a client name.
    if self.cn != self.client_id:
      raise flow.FlowError("Certificate name %s mismatch for client %s",
                           self.cn, self.client_id)

    # Set and write the certificate to the client record.
    certificate_attribute = rdfvalue.RDFX509Cert(cert.as_pem())
    self.client.Set(self.client.Schema.CERT, certificate_attribute)

    first_seen = time.time() * 1e6
    self.client.Set(self.client.Schema.FIRST_SEEN,
                    rdfvalue.RDFDatetime(first_seen))

    self.client.Close(sync=True)

    # Publish the client enrollment message.
    self.Publish("ClientEnrollment", certificate_attribute)

    self.Log("Enrolled %s successfully", self.client_id)

    # This is needed for backwards compatibility.
    # TODO(user): Remove this once all clients are > 2200.
    self.CallClient("SaveCert", pem=cert.as_pem(),
                    type=rdfvalue.Certificate.Type.CRT, next_state="End")

  def MakeCert(self, req):
    """Make new cert for the client."""
    # code inspired by M2Crypto unit tests

    cert = X509.X509()
    # Use the client CN for a cert serial_id. This will ensure we do
    # not have clashing cert id.
    cert.set_serial_number(int(self.cn.Basename().split(".")[1], 16))
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
    ca_data = config_lib.CONFIG["CA.certificate"]
    ca_cert = X509.load_cert_string(ca_data)
    cert.set_issuer(ca_cert.get_issuer())
    cert.set_pubkey(req.get_pubkey())

    ca_key = RSA.load_key_string(config_lib.CONFIG["PrivateKeys.ca_key"])
    key_pair = EVP.PKey(md="sha256")
    key_pair.assign_rsa(ca_key)

    # Sign the certificate
    cert.sign(key_pair, "sha256")

    return cert


enrolment_cache = utils.FastStore(5000)


class Enroler(flow.WellKnownFlow):
  """Manage enrolment requests."""
  well_known_session_id = rdfvalue.SessionID("aff4:/flows/CA:Enrol")

  def ProcessMessage(self, message):
    """Begins an enrollment flow for this client.

    Args:
        message: The Certificate sent by the client. Note that this
        message is not authenticated.
    """
    cert = rdfvalue.Certificate(message.args)

    queue = self.well_known_session_id.Queue()

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
      flow.GRRFlow.StartFlow(client_id=client_id, flow_name="CAEnroler",
                             csr=cert, queue=queue,
                             client=client, token=self.token)
