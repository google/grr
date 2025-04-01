#!/usr/bin/env python
"""Configuration parameters for the artifact subsystem."""


from grr_response_core.lib import config_lib

config_lib.DEFINE_list("Artifacts.artifact_dirs", [
    "%(grr_response_core/artifacts@grr-response-core|resource)",
    "%(grr_response_core/artifacts/local@grr-response-core|resource)"
], "A list directories to load artifacts from.")

config_lib.DEFINE_list(
    "Artifacts.netgroup_filter_regexes", [],
    help="Only parse groups that match one of these regexes"
    " from /etc/netgroup files.")

config_lib.DEFINE_list(
    "Artifacts.netgroup_ignore_users", [],
    help="Exclude these users when parsing /etc/netgroup "
    "files.")
