#!/usr/bin/env python
"""A module that provides access to the GUI rendering system."""

# pylint: disable=unused-import
from grr.gui import django_lib
# pylint: enable=unused-import

from grr.lib import registry


renderers = None  # Will be imported at initialization time.


class RenderingInit(registry.InitHook):
  """Initialize the Django environment."""

  pre = ["DjangoInit", "StatsInit"]

  def RunOnce(self):
    # TODO(user): This is a huge hack but necessary because getting django
    # importing correct is very hard. We really should think about decoupling
    # the templating system better.
    global renderers  # pylint: disable=global-variable-not-assigned
    # pylint: disable=g-import-not-at-top, unused-variable, redefined-outer-name
    from grr.gui import renderers
    # pylint: enable=g-import-not-at-top, unused-variable, redefined-outer-name
