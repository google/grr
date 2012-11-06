#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""URL definitions for GRR Admin Server."""


import os


from django.conf.urls import defaults
from grr import gui
from grr.gui import views
from grr.lib import stats


document_root = os.path.join(os.path.dirname(gui.__file__), "static")

django_base = "django."
view_base = "grr.gui.views."
handler404 = "defaults.handler404"
handler500 = "views.ServerError"

urlpatterns = defaults.patterns(
    "",
    (r"^$", view_base + "Homepage"),
    # Automatic rendering is done here
    (r"^render/[^/]+/.*", view_base + "RenderGenericRenderer"),
    (r"^static/(.*)$", django_base + "views.static.serve",
     {"document_root": document_root}),
)

