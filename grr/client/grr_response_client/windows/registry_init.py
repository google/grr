#!/usr/bin/env python
"""This module contains windows specific client code."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# These need to register plugins so, pylint: disable=unused-import
from grr_response_client.windows import installers
from grr_response_client.windows import regconfig
