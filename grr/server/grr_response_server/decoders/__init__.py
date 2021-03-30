#!/usr/bin/env python
"""A root module with decoder definitions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import factory
from grr_response_server.decoders import _abstract

AbstractDecoder = _abstract.AbstractDecoder  # pylint: disable=invalid-name


FACTORY = factory.Factory(AbstractDecoder)
