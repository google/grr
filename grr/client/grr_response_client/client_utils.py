#!/usr/bin/env python
"""Client utilities."""

import sys

# pylint: disable=g-import-not-at-top
if sys.platform == "win32":
  from grr_response_client import client_utils_windows as _client_utils
elif sys.platform == "darwin":
  from grr_response_client import client_utils_osx as _client_utils
else:
  from grr_response_client import client_utils_linux as _client_utils
# pylint: enable=g-import-not-at-top

# pylint: disable=g-bad-name
AddStatEntryExtAttrs = _client_utils.AddStatEntryExtAttrs
CanonicalPathToLocalPath = _client_utils.CanonicalPathToLocalPath
FindProxies = _client_utils.FindProxies
GetRawDevice = _client_utils.GetRawDevice
KeepAlive = _client_utils.KeepAlive
LocalPathToCanonicalPath = _client_utils.LocalPathToCanonicalPath
MemoryRegions = _client_utils.MemoryRegions
NannyController = _client_utils.NannyController
OpenProcessForMemoryAccess = _client_utils.OpenProcessForMemoryAccess
VerifyFileOwner = _client_utils.VerifyFileOwner
# pylint: enable=g-bad-name
