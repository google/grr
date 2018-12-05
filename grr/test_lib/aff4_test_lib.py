#!/usr/bin/env python
"""Classes for AFF4-related testing."""
from __future__ import absolute_import
from __future__ import division


from grr_response_core.lib.rdfvalues import client as rdf_client

from grr.test_lib import test_lib


class AFF4ObjectTest(test_lib.GRRBaseTest):
  """The base class of all aff4 object tests."""

  client_id = rdf_client.ClientURN("C." + "B" * 16)
