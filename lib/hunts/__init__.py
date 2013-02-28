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

"""Hunts and hunt implementations."""


# pylint: disable=W0611
# These imports populate the GRRHunt registry
from grr.lib import aff4
from grr.lib.hunts import implementation
from grr.lib.hunts import standard


# Add shortcuts to hunts into this module.
for name, cls in implementation.GRRHunt.classes.items():
  if aff4.issubclass(cls, implementation.GRRHunt):
    globals()[name] = cls
