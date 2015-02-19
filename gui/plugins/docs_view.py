#!/usr/bin/env python
"""Documentation-related renderers."""

from grr.gui import renderers


class ApiDocumentation(renderers.AngularDirectiveRenderer):
  description = "HTTP API documentation"
  directive = "grr-api-docs"
