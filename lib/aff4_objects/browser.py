#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

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
