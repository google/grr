#!/usr/bin/env python
"""URL definitions for GRR Admin Server."""


import os


from django.conf import urls

from grr import gui

document_root = os.path.join(os.path.dirname(gui.__file__), "static")
help_root = os.path.join(os.path.dirname(os.path.dirname(gui.__file__)), "docs")

django_base = "django."
view_base = "grr.gui.views."
handler404 = "urls.handler404"
handler500 = "views.ServerError"
static_handler = django_base + "views.static.serve"

urlpatterns = urls.patterns(
    "",
    (r"^$", view_base + "Homepage"),
    # Automatic rendering is done here
    (r"^api/aff4/[^/]+/.*", view_base + "RenderAFF4Object"),
    (r"^render/[^/]+/.*", view_base + "RenderGenericRenderer"),
    (r"^download/[^/]+/.*", view_base + "RenderBinaryDownload"),
    (r"^static/(.*)$", static_handler,
     {"document_root": document_root}),
    (r"^help/(.*)$", view_base + "RenderHelp")
)
