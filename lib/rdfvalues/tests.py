#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""GRR rdfvalue tests.

This module loads and registers all the tests for the RDFValue implementations.
"""



# These need to register plugins so, pylint: disable=W0611
from grr.lib.rdfvalues import basic_test
from grr.lib.rdfvalues import crypto_test
from grr.lib.rdfvalues import paths_test
from grr.lib.rdfvalues import protodict_test
from grr.lib.rdfvalues import stats_test
