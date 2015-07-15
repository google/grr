#!/usr/bin/env python
"""API config options."""

from grr.lib import config_lib

config_lib.DEFINE_string("API.RendererACLFile", "",
                         "The file containing API acls, see "
                         "grr/config/api_acls.yaml for an example.")

config_lib.DEFINE_string("API.AuthorizationManager",
                         "SimpleAPIAuthorizationManager",
                         "API Authorization manager class to be used")
