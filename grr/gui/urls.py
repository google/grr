#!/usr/bin/env python
"""URL definitions for GRR Admin Server."""


import mimetypes


from django.conf import urls

from grr.lib import config_lib
from grr.lib import registry

django_base = "django."
view_base = "grr.gui.views."
handler404 = "urls.handler404"
handler500 = view_base + "ServerError"
static_handler = django_base + "views.static.serve"


def GetURLPatterns():
  return [
      (r"^$", view_base + "Homepage"),
      # Automatic rendering is done here
      (r"^api/.+", view_base + "RenderApi"),
      (r"^render/[^/]+/.*", view_base + "RenderGenericRenderer"),
      (r"^download/[^/]+/.*", view_base + "RenderBinaryDownload"),
      (r"^static/(.*)$", static_handler,
       {"document_root": config_lib.CONFIG["AdminUI.document_root"]}),
      (r"^local/static/(.*)$", static_handler,
       {"document_root": config_lib.CONFIG["AdminUI.local_document_root"]}),
      (r"^help/(.*)$", view_base + "RenderHelp")
  ]


urlpatterns = []


class UrlsInit(registry.InitHook):
  pre = []

  def RunOnce(self):
    """Run this once on init."""
    mimetypes.add_type("application/font-woff", ".woff", True)
    urlpatterns.extend([urls.url(prefix="", *x) for x in GetURLPatterns()])
