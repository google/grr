#!/usr/bin/env python
"""A root module with decoder definitions."""

from grr_response_core.lib import factory
from grr_response_server.decoders import _abstract

AbstractDecoder = _abstract.AbstractDecoder  # pylint: disable=invalid-name


FACTORY = factory.Factory(AbstractDecoder)
