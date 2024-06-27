#!/usr/bin/env python
"""Deprecated flows."""

import logging
from grr_response_server import flow_base


class AbstractDeprecatedFlow(flow_base.FlowBase):
  """Extend this class to mark a flow as deprecated."""

  deprecated = True

  def __init__(self, *args, **kwargs):
    logging.warning("Deprecated flow %s was called", self.__class__.__name__)


class GetExecutables(AbstractDeprecatedFlow):
  """Stub for deprecated GetExecutables flow."""
