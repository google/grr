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

"""Actions required for CA enrolment."""



from grr.client import actions
from grr.client import conf
from grr.proto import jobs_pb2

FLAGS = conf.PARSER.flags


class SaveCert(actions.ActionPlugin):
  """Accepts a signed certificate from the server and saves it to disk."""
  in_protobuf = jobs_pb2.Certificate
  out_protobuf = jobs_pb2.Certificate

  def Run(self, args):
    """Receive the certificate and store it to disk."""
    # TODO(user): Validate this cert is ok
    if args.pem:
      # There is a valid certificate
      self.grr_context.StoreCert(args.pem)

      # Now loads the new certs on the client, and updates the client's
      # common name. The client will not receive any messages going to
      # the old CN any longer - only messages to the new CN.
      self.grr_context.LoadCertificates()

    else:
      # Send the server our CSR again (Should we regenerate it here?)
      self.SendReply(pem=self.grr_context.communicator.csr,
                     type=jobs_pb2.Certificate.CSR)
