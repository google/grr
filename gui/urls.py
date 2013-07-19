#!/usr/bin/env python
"""URL definitions for GRR Admin Server."""


import os


from django.conf.urls import defaults

from grr import gui

document_root = os.path.join(os.path.dirname(gui.__file__), "static")

django_base = "django."
view_base = "grr.gui.views."
handler500 = "defaults.handler404"
handler500 = "views.ServerError"

urlpatterns = defaults.patterns(
    "",
    (r"^$", view_base + "Homepage"),
    # Automatic rendering is done here
    (r"^render/[^/]+/.*", view_base + "RenderGenericRenderer"),
    (r"^static/(.*)$", django_base + "views.static.serve",
     {"document_root": document_root}),
)
