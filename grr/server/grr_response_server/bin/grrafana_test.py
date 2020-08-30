#!/usr/bin/env python
# Lint as: python3
"""Unittest for GRRafana HTTP server."""
from absl.testing import absltest
from absl import app

from grr_response_server import fleetspeak_connector
from grr_response_server.bin import grrafana
from grr_response_server import server_startup

from werkzeug import serving as werkzeug_serving
from werkzeug import test as werkzeug_test


# TODO(tsehori): We should implement tests for grrafana.py.
class GrrafanaTest(absltest.TestCase):
  """Test the GRRafana HTTP server."""

  pass
