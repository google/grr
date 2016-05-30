#!/usr/bin/env python
"""Configuration parameters for logging and error reporting subsystems."""

from grr.lib import config_lib
from grr.lib import type_info
from grr.lib.rdfvalues import standard

config_lib.DEFINE_string("Logging.domain", "localhost",
                         "The email domain belonging to this installation. "
                         "Leave blank to not restrict email to this domain")

config_lib.DEFINE_list("Logging.engines", ["stderr"],
                       "Enabled logging engines. Valid values are "
                       "combinations of stderr,file,syslog,event_log.")

config_lib.DEFINE_bool("Logging.verbose",
                       False,
                       help="If true log more verbosely.")

config_lib.DEFINE_string("Logging.path",
                         "%(Config.prefix)/var/log/",
                         help="Path to log file directory.")

config_lib.DEFINE_string("Logging.syslog_path",
                         "/dev/log",
                         help="Path to syslog socket. This can be a unix "
                         "domain socket or in a UDP host:port notation.")

config_lib.DEFINE_string("Logging.filename",
                         "%(Logging.path)/GRRlog.txt",
                         help="Filename of the grr log file.")

config_lib.DEFINE_string(
    "Logging.format",
    # Use a literal block here to prevent config system expansion as this should
    # be a python format string.
    "%{%(levelname)s:%(asctime)s %(module)s:%(lineno)s] %(message)s}",
    help="Log line format (using python's standard logging expansions).")

config_lib.DEFINE_string("Logging.service_name",
                         "GRR",
                         help="The service name that will be logged with the "
                         "event log engine.")

config_lib.DEFINE_option(type_info.RDFValueType(
    rdfclass=standard.DomainEmailAddress,
    name="Monitoring.alert_email",
    help="The email address to send events to.",
    default="grr-monitoring@localhost"))

config_lib.DEFINE_option(type_info.RDFValueType(
    rdfclass=standard.DomainEmailAddress,
    name="Monitoring.emergency_access_email",
    help="The email address to notify in an emergency.",
    default="grr-emergency@localhost"))

config_lib.DEFINE_integer("Monitoring.http_port", 0,
                          "Port for stats monitoring server.")

config_lib.DEFINE_integer("Logging.aff4_audit_log_rollover", 60 * 60 * 24 * 14,
                          "Audit log rollover interval in seconds. "
                          "Default is 2 weeks")
