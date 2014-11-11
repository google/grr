#!/usr/bin/env python
"""URL definitions for GRR Admin Server."""


import mimetypes
import os


from django.conf import urls

from grr import gui
from grr.lib import registry

document_root = os.path.join(os.path.dirname(gui.__file__), "static")
help_root = os.path.join(os.path.dirname(os.path.dirname(gui.__file__)), "docs")

django_base = "django."
view_base = "grr.gui.views."
handler404 = "urls.handler404"
handler500 = view_base + "ServerError"
static_handler = django_base + "views.static.serve"

urlpatterns = urls.patterns(
    "",
    (r"^$", view_base + "Homepage"),
    # Automatic rendering is done here
    (r"^api/.+", view_base + "RenderApi"),
    (r"^render/[^/]+/.*", view_base + "RenderGenericRenderer"),
    (r"^download/[^/]+/.*", view_base + "RenderBinaryDownload"),
    (r"^static/(.*)$", static_handler,
     {"document_root": document_root}),
    (r"^help/(.*)$", view_base + "RenderHelp")
)


class UrlsInit(registry.InitHook):
  pre = []

  def RunOnce(self):
    """Run this once on init."""
    mimetypes.add_type("application/font-woff", ".woff", True)
