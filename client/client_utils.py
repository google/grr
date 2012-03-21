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


"""Client utilities."""



import sys

# Select the version of what we want based on the OS:

if sys.platform == "win32":
  from grr.client import client_utils_windows
  FindProxies = client_utils_windows.WinFindProxies
  GetRawDevice = client_utils_windows.WinGetRawDevice
  CanonicalPathToLocalPath = client_utils_windows.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_windows.LocalPathToCanonicalPath
elif sys.platform == "darwin":
  from grr.client import client_utils_osx
  FindProxies = client_utils_osx.OSXFindProxies
  GetRawDevice = client_utils_osx.OSXGetRawDevice
  # Should be the same as linux.
  CanonicalPathToLocalPath = client_utils_osx.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_osx.LocalPathToCanonicalPath
else:
  from grr.client import client_utils_linux
  # Linux platform
  FindProxies = client_utils_linux.LinFindProxies
  GetRawDevice = client_utils_linux.LinGetRawDevice
  CanonicalPathToLocalPath = client_utils_linux.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_linux.LocalPathToCanonicalPath
