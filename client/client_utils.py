#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""Windows specific actions."""


import sys

# Select the version of what we want based on the OS:
if sys.platform == "win32":
  from grr.client import client_utils_windows
  FindProxies = client_utils_windows.WinFindProxies
  SplitPathspec = client_utils_windows.WinSplitPathspec
elif sys.platform == "darwin":
  from grr.client import client_utils_osx
  FindProxies = client_utils_osx.OSXFindProxies
  SplitPathspec = client_utils_osx.OSXSplitPathspec
else:
  from grr.client import client_utils_linux
  # Linux platform
  FindProxies = client_utils_linux.LinFindProxies
  SplitPathspec = client_utils_linux.LinSplitPathspec
