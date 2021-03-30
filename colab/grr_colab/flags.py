#!/usr/bin/env python
"""Grr Colab flags definitions."""

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

# TODO(user): Find a better way to handle flags. Despite the fact that in
#  IPython flags are available during extension loading, Jupyter does not
#  propagate flags so for now they have to be specified with
#  `FLAGS.set_default()` method that obviously is not the best solution.
if not FLAGS.is_parsed():
  FLAGS(sys.argv, known_only=True)
