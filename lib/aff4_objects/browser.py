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


"""GRR specific AFF4 browser analysis objects."""




from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr


class VFSBrowserExtension(aff4_grr.VFSMemoryFile):
  """A extension analysis result."""

  class SchemaCls(aff4_grr.VFSMemoryFile.SchemaCls):
    """The schema for the extension dir."""
    NAME = aff4.Attribute("aff4:extensionname", rdfvalue.RDFString,
                          "The name of the Chrome extension.")

    VERSION = aff4.Attribute("aff4:extensionversion", rdfvalue.RDFString,
                             "The version of the Chrome extension.")

    UPDATEURL = aff4.Attribute("aff4:updateurl", rdfvalue.RDFString,
                               "The update URL for the extension.")

    PERMISSIONS = aff4.Attribute("aff4:permissions", rdfvalue.RDFString,
                                 "The requested permissions.")

    CHROMEID = aff4.Attribute("aff4:chromeid", rdfvalue.RDFString,
                              "The public key hash for the extension.")

    EXTENSIONDIR = aff4.Attribute("aff4:extensiondir", rdfvalue.RDFString,
                                  "The directory where the extension resides.")

  def __init__(self, urn, mode="r", **kwargs):
    super(aff4.AFF4MemoryStream, self).__init__(urn, mode=mode, **kwargs)

    # The client_id is the first element of the URN
    self.client_id = self.urn.Path().split("/")[1]
