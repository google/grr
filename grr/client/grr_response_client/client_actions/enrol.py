#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""Actions required for CA enrolment."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_client import actions


class SaveCert(actions.ActionPlugin):
  """Accepts a signed certificate from the server and saves it to disk."""

  def Run(self, args):
    """Receive the certificate and store it to disk."""
    # We dont really care about the certificate any more. The ca_enroller flow
    # is changed to not issue this client action now.
