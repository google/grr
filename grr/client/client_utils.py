#!/usr/bin/env python
"""Client utilities."""



import sys

# pylint: disable=g-import-not-at-top
if sys.platform == "win32":
  from grr.client import client_utils_windows as _client_utils
elif sys.platform == "darwin":
  from grr.client import client_utils_osx as _client_utils
else:
  from grr.client import client_utils_linux as _client_utils
# pylint: enable=g-import-not-at-top

# pylint: disable=g-bad-name
CanonicalPathToLocalPath = _client_utils.CanonicalPathToLocalPath
LocalPathToCanonicalPath = _client_utils.LocalPathToCanonicalPath
FindProxies = _client_utils.FindProxies
GetRawDevice = _client_utils.GetRawDevice
NannyController = _client_utils.NannyController
KeepAlive = _client_utils.KeepAlive
VerifyFileOwner = _client_utils.VerifyFileOwner
AddStatEntryExtFlags = _client_utils.AddStatEntryExtFlags
# pylint: enable=g-bad-name
