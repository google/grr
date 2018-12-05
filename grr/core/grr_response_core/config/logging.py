#!/usr/bin/env python
"""Configuration parameters for logging and error reporting subsystems."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import standard as rdf_standard

config_lib.DEFINE_string(
    "Logging.domain", "localhost",
    "The email domain belonging to this installation. "
    "Leave blank to not restrict email to this domain")

config_lib.DEFINE_list(
    "Logging.engines", ["stderr"], "Enabled logging engines. Valid values are "
    "combinations of stderr,file,syslog,event_log.")

config_lib.DEFINE_bool(
    "Logging.verbose", False, help="If true log more verbosely.")

config_lib.DEFINE_string(
    "Logging.path",
    "%(Config.prefix)/var/log/",
    help="Path to log file directory.")

config_lib.DEFINE_string(
    "Logging.syslog_path",
    "/dev/log",
    help="Path to syslog socket. This can be a unix "
    "domain socket or in a UDP host:port notation.")

config_lib.DEFINE_string(
    "Logging.filename",
    "%(Logging.path)/GRRlog.txt",
    help="Filename of the grr log file.")

config_lib.DEFINE_option(
    type_info.RDFValueType(
        rdfclass=rdf_standard.DomainEmailAddress,
        name="Monitoring.alert_email",
        description="The email address to send events to.",
        default="grr-monitoring@localhost"))

config_lib.DEFINE_option(
    type_info.RDFValueType(
        rdfclass=rdf_standard.DomainEmailAddress,
        name="Monitoring.emergency_access_email",
        description="The email address to notify in an emergency.",
        default="grr-emergency@localhost"))

config_lib.DEFINE_integer("Monitoring.http_port", 0,
                          "Port for stats monitoring server.")

config_lib.DEFINE_integer(
    "Monitoring.http_port_max", None,
    "If set and Monitoring.http_port is in use, attempt "
    "to use ports between Monitoring.http_port and "
    "Monitoring.http_port_max.")
