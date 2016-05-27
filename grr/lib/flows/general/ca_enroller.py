#!/usr/bin/env python
"""A flow to enrol new clients."""


import time


from M2Crypto import ASN1
from M2Crypto import EVP
from M2Crypto import X509

import logging
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class CAEnrolerArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CAEnrolerArgs


class CAEnroler(flow.GRRFlow):
  """Enrol new clients."""

  args_type = CAEnrolerArgs

  @flow.StateHandler(next_state="End")
  def Start(self):
    """Sign the CSR from the client."""
    client = aff4.FACTORY.Create(self.client_id,
                                 aff4_grr.VFSGRRClient,
                                 mode="rw",
                                 token=self.token)

    if self.args.csr.type != rdf_crypto.Certificate.Type.CSR:
      raise IOError("Must be called with CSR")

    req = X509.load_request_string(self.args.csr.pem)

    # Verify the CSR. This is not strictly necessary but doesn't harm either.
    if req.verify(req.get_pubkey()) != 1:
      raise flow.FlowError("CSR for client %s did not verify: %s" %
                           (self.client_id, req.as_pem()))

    # Verify that the CN is of the correct form. The common name should refer
    # to a client URN.
    public_key = req.get_pubkey().get_rsa().pub()[1]
    self.cn = rdf_client.ClientURN.FromPublicKey(public_key)
    if self.cn != rdf_client.ClientURN(req.get_subject().CN):
      raise IOError("CSR CN %s does not match public key %s." %
                    (rdf_client.ClientURN(req.get_subject().CN), self.cn))

    logging.info("Will sign CSR for: %s", self.cn)

    cert = self.MakeCert(self.cn, req)

    # This check is important to ensure that the client id reported in the
    # source of the enrollment request is the same as the one in the
    # certificate. We use the ClientURN to ensure this is also of the correct
    # form for a client name.
    if self.cn != self.client_id:
      raise flow.FlowError("Certificate name %s mismatch for client %s",
                           self.cn, self.client_id)

    # Set and write the certificate to the client record.
    certificate_attribute = rdf_crypto.RDFX509Cert(cert.as_pem())
    client.Set(client.Schema.CERT, certificate_attribute)
    client.Set(client.Schema.FIRST_SEEN, rdfvalue.RDFDatetime().Now())

    index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                aff4_type=client_index.ClientIndex,
                                object_exists=True,
                                mode="rw",
                                token=self.token)
    index.AddClient(client)
    client.Close(sync=True)

    # Publish the client enrollment message.
    self.Publish("ClientEnrollment", certificate_attribute.common_name)

    self.Log("Enrolled %s successfully", self.client_id)

  def MakeCert(self, cn, req):
    """Make new cert for the client."""
    # code inspired by M2Crypto unit tests

    cert = X509.X509()
    # Use the client CN for a cert serial_id. This will ensure we do
    # not have clashing cert id.
    cert.set_serial_number(int(cn.Basename().split(".")[1], 16))
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
    ca_cert = config_lib.CONFIG["CA.certificate"].GetX509Cert()
    cert.set_issuer(ca_cert.get_issuer())
    cert.set_pubkey(req.get_pubkey())

    ca_key = config_lib.CONFIG["PrivateKeys.ca_key"].GetPrivateKey()
    key_pair = EVP.PKey(md="sha256")
    key_pair.assign_rsa(ca_key)

    # Sign the certificate
    cert.sign(key_pair, "sha256")

    return cert


enrolment_cache = utils.FastStore(5000)


class Enroler(flow.WellKnownFlow):
  """Manage enrolment requests."""
  well_known_session_id = rdfvalue.SessionID(queue=queues.ENROLLMENT,
                                             flow_name="Enrol")

  def ProcessMessage(self, message):
    """Begins an enrollment flow for this client.

    Args:
        message: The Certificate sent by the client. Note that this
        message is not authenticated.
    """
    cert = rdf_crypto.Certificate(message.payload)

    queue = self.well_known_session_id.Queue()

    client_id = message.source

    # It makes no sense to enrol the same client multiple times, so we
    # eliminate duplicates. Note, that we can still enroll clients multiple
    # times due to cache expiration.
    try:
      enrolment_cache.Get(client_id)
      return
    except KeyError:
      enrolment_cache.Put(client_id, 1)

    # Create a new client object for this client.
    client = aff4.FACTORY.Create(client_id,
                                 aff4_grr.VFSGRRClient,
                                 mode="rw",
                                 token=self.token)

    # Only enroll this client if it has no certificate yet.
    if not client.Get(client.Schema.CERT):
      # Start the enrollment flow for this client.
      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="CAEnroler",
                             csr=cert,
                             queue=queue,
                             token=self.token)
