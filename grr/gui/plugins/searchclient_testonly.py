#!/usr/bin/env python
"""Test renderer for searchclient_test.py."""

from grr.gui import renderers


class CanaryTestRenderer(renderers.TemplateRenderer):
  """Sample canary-aware renderer."""

  layout_template = renderers.Template("""
{% if canary_mode %}
CANARY MODE IS ON
{% else %}
CANARY MODE IS OFF
{% endif %}
""")
