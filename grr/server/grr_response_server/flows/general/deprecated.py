#!/usr/bin/env python
"""Deprecated flows."""

import logging
from typing import Any

from grr_response_server import flow_base


class AbstractDeprecatedFlow(flow_base.FlowBase):
  """Extend this class to mark a flow as deprecated."""

  deprecated = True

  def __init__(self, *args: Any, **kwargs: Any):
    logging.warning("Deprecated flow %s was called", self.__class__.__name__)


class GetExecutables(AbstractDeprecatedFlow):
  """Stub for deprecated GetExecutables flow."""
