#!/usr/bin/env python
"""Grr Colab flags definitions."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import sys

from absl import flags

FLAGS = flags.FLAGS


flags.DEFINE_string(
    name='grr_http_api_endpoint',
    default=None,
    help='HTTP endpoint for GRR API')

flags.DEFINE_string(
    name='grr_auth_api_user',
    default=None,
    help='GRR API username')

flags.DEFINE_string(
    name='grr_auth_password',
    default=None,
    help='GRR API user password')

flags.DEFINE_string(
    name='grr_admin_ui_url', default=None, help='URL to GRR Admin UI')

if not FLAGS.is_parsed():
  FLAGS(sys.argv)
