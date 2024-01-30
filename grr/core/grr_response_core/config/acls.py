#!/usr/bin/env python
"""Settings for ACLs/approvals system."""


from grr_response_core.lib import config_lib

config_lib.DEFINE_string(
    "ACL.approvers_config_file", "%(Config.directory)/approvers.yaml",
    "File that defines who can approve access to "
    "clients with certain labels.")

config_lib.DEFINE_integer("ACL.approvers_required", 2,
                          "The number of approvers required for access.")

config_lib.DEFINE_string(
    "ACL.group_access_manager_class", "NoGroupAccess",
    "This class handles interfacing with corporate group"
    "directories for granting access. Override with a "
    "class that understands your LDAP/AD/whatever setup.")

config_lib.DEFINE_integer(
    "ACL.token_expiry",
    28 * 24 * 60 * 60,
    "The default duration in seconds of a valid approval token. "
    "Default of four weeks.",
)

config_lib.DEFINE_integer(
    "ACL.token_max_expiry",
    367 * 24 * 60 * 60,
    "The maximum duration in seconds of a valid approval token. "
    "Default 1 leap year and 1 day.",
)
