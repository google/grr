#!/usr/bin/env python
#
# Copyright 2015 Google Inc. All Rights Reserved.
#
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
"""Acceleration module for semantic protobuf parsing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from distutils.core import Extension
from distutils.core import setup

SOURCES = ["accelerated.c"]

setup(
    name="grr",
    version="0.1",
    long_description="Semantic protobufs are smart protocol buffers.",
    license="Apache 2.0",
    author="Michael Cohen",
    ext_modules=[Extension(
        "_semantic",
        SOURCES,)],)
