#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""The GRR client agent.

This file contains configuration options which are used by the various
clients. These options are here since code needs to know about them, even if the
specific client version is not imported. For example, some of these options are
used only by the windows client.
"""


from grr.lib import config_lib

# Windows Client configuration options.

# The following configuration options are defined here but are used in
# the windows nanny code (grr/client/nanny/windows_nanny.h).
config_lib.DEFINE_string("Nanny.child_binary", "GRR.exe",
                         help="The location to the client binary.")

config_lib.DEFINE_string("Nanny.child_command_line", "%(Nanny.child_binary)",
                         help="The command line to launch the client binary.")

config_lib.DEFINE_string("Nanny.service_name", "GRR Service",
                         help="The name of the nanny.")

config_lib.DEFINE_string("Nanny.service_description", "GRR Service",
                         help="The description of the nanny service.")

config_lib.DEFINE_string("Nanny.service_key", r"%(Client.config_key)",
                         help="The registry key of the nanny service.")

config_lib.DEFINE_string("Nanny.service_key_hive", r"%(Client.config_hive)",
                         help="The registry key of the nanny service.")

config_lib.DEFINE_string("Client.config_hive", r"HKEY_LOCAL_MACHINE",
                         help="The registry hive where the client "
                         "configuration will be stored.")

config_lib.DEFINE_string("Client.config_key", r"Software\\GRR",
                         help="The registry key where  client configuration "
                         "will be stored.")

config_lib.DEFINE_string("Nanny.nanny_binary",
                         r"%(Client.install_path)\\%(service_binary_name)",
                         help="The full location to the nanny binary.")

config_lib.DEFINE_string("Nanny.service_binary_name",
                         "%(Client.name)service.exe",
                         help="The executable name of the nanny binary.")
