#!/usr/bin/env python
"""Client actions related to administrating the client and its configuration."""


import os
import platform
import socket
import time


import psutil

import logging

from grr.client import actions
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import stats


class Echo(actions.ActionPlugin):
  """Returns a message to the server."""
  in_rdfvalue = rdfvalue.EchoRequest
  out_rdfvalue = rdfvalue.LogMessage

  def Run(self, args):
    self.SendReply(args)


class GetHostname(actions.ActionPlugin):
  """Retrieves the host name of the client."""
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, unused_args):
    self.SendReply(string=socket.gethostname())


class GetPlatformInfo(actions.ActionPlugin):
  """Retrieves platform information."""
  out_rdfvalue = rdfvalue.Uname

  def Run(self, unused_args):
    """Populate platform information into a Uname response."""
    uname = platform.uname()
    fqdn = socket.getfqdn()
    system = uname[0]
    if system == "Windows":
      service_pack = platform.win32_ver()[2]
      kernel = uname[3]                           # 5.1.2600
      release = uname[2]                          # XP, 2000, 7
      version = uname[3] + service_pack           # 5.1.2600 SP3, 6.1.7601 SP1
    elif system == "Darwin":
      kernel = uname[2]                           # 12.2.0
      release = "OSX"                             # OSX
      version = platform.mac_ver()[0]             # 10.8.2
    elif system == "Linux":
      kernel = uname[2]                           # 3.2.5
      release = platform.linux_distribution()[0]  # Ubuntu
      version = platform.linux_distribution()[1]  # 12.04

    self.SendReply(system=system,
                   node=uname[1],
                   release=release,
                   version=version,
                   machine=uname[4],              # x86, x86_64
                   kernel=kernel,
                   fqdn=fqdn)


class Kill(actions.ActionPlugin):
  """A client action for terminating (killing) the client.

  Used for testing process respawn.
  """
  out_rdfvalue = rdfvalue.GrrMessage

  def Run(self, unused_arg):
    """Run the kill."""
    # Send a message back to the service to say that we are about to shutdown.
    reply = rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.ReturnedStatus.OK)
    # Queue up the response message, jump the queue.
    self.SendReply(reply, message_type=rdfvalue.GrrMessage.Type.STATUS,
                   priority=rdfvalue.GrrMessage.Priority.HIGH_PRIORITY + 1)

    # Give the http thread some time to send the reply.
    self.grr_worker.Sleep(10)

    # Die ourselves.
    logging.info("Dying on request.")
    os._exit(242)  # pylint: disable=protected-access


class Hang(actions.ActionPlugin):
  """A client action for simulating the client becoming unresponsive (hanging).

  Used for testing nanny terminating the client.
  """
  in_rdfvalue = rdfvalue.DataBlob

  def Run(self, arg):
    # Sleep a really long time.
    time.sleep(arg.integer or 6000)


class BusyHang(actions.ActionPlugin):
  """A client action that burns cpu cycles. Used for testing cpu limits."""
  in_rdfvalue = rdfvalue.DataBlob

  def Run(self, arg):
    duration = 5
    if arg and arg.integer:
      duration = arg.integer
    end = time.time() + duration
    while time.time() < end:
      pass


class Bloat(actions.ActionPlugin):
  """A client action that uses lots of memory for testing."""
  in_rdfvalue = rdfvalue.DataBlob

  def Run(self, arg):

    iterations = arg.integer or 1024  # Gives 1 gb.

    l = []

    for _ in range(iterations):
      l.append("X" * 1048576)  # 1 mb.

    time.sleep(60)


class GetConfiguration(actions.ActionPlugin):
  """Retrieves the running configuration parameters."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.Dict

  BLOCKED_PARAMETERS = ["Client.private_key"]

  def Run(self, unused_arg):
    """Retrieve the configuration except for the blocked parameters."""

    out = self.out_rdfvalue()
    for descriptor in config_lib.CONFIG.type_infos:
      if descriptor.name in self.BLOCKED_PARAMETERS:
        value = "[Redacted]"
      else:
        try:
          value = config_lib.CONFIG.Get(descriptor.name, default=None)
        except (config_lib.Error, KeyError, AttributeError, ValueError) as e:
          logging.info("Config reading error: %s", e)
          continue

      if value is not None:
        out[descriptor.name] = value

    self.SendReply(out)


class UpdateConfiguration(actions.ActionPlugin):
  """Updates configuration parameters on the client."""
  in_rdfvalue = rdfvalue.Dict

  UPDATEABLE_FIELDS = ["Client.compression",
                       "Client.foreman_check_frequency",
                       "Client.control_urls",
                       "Client.max_post_size",
                       "Client.max_out_queue",
                       "Client.poll_min",
                       "Client.poll_max",
                       "Client.poll_slew",
                       "Client.rss_max"]

  def Run(self, arg):
    """Does the actual work."""
    disallowed_fields = []

    for field, value in arg.items():
      if field in self.UPDATEABLE_FIELDS:
        config_lib.CONFIG.Set(field, value)

      else:
        disallowed_fields.append(field)

    if disallowed_fields:
      logging.warning("Received an update request for restricted field(s) %s.",
                      ",".join(disallowed_fields))

    try:
      config_lib.CONFIG.Write()
    except (IOError, OSError):
      pass


def GetClientInformation():
  return rdfvalue.ClientInformation(
      client_name=config_lib.CONFIG["Client.name"],
      client_description=config_lib.CONFIG["Client.description"],
      client_version=int(config_lib.CONFIG["Client.version_numeric"]),
      build_time=config_lib.CONFIG["Client.build_time"],
      labels=config_lib.CONFIG.Get("Client.labels", default=None))


class GetClientInfo(actions.ActionPlugin):
  """Obtains information about the GRR client installed."""
  out_rdfvalue = rdfvalue.ClientInformation

  def Run(self, unused_args):
    self.SendReply(GetClientInformation())


class GetClientStats(actions.ActionPlugin):
  """This retrieves some stats about the GRR process."""
  in_rdfvalue = rdfvalue.GetClientStatsRequest
  out_rdfvalue = rdfvalue.ClientStats

  def Run(self, arg):
    """Returns the client stats."""
    if arg is None:
      arg = rdfvalue.GetClientStatsRequest()

    proc = psutil.Process(os.getpid())
    meminfo = proc.memory_info()
    response = rdfvalue.ClientStats(
        RSS_size=meminfo[0],
        VMS_size=meminfo[1],
        memory_percent=proc.memory_percent(),
        bytes_received=stats.STATS.GetMetricValue(
            "grr_client_received_bytes"),
        bytes_sent=stats.STATS.GetMetricValue(
            "grr_client_sent_bytes"),
        create_time=long(proc.create_time() * 1e6),
        boot_time=long(psutil.boot_time() * 1e6))

    samples = self.grr_worker.stats_collector.cpu_samples
    for (timestamp, user, system, percent) in samples:
      if arg.start_time < timestamp < arg.end_time:
        sample = rdfvalue.CpuSample(
            timestamp=timestamp,
            user_cpu_time=user,
            system_cpu_time=system,
            cpu_percent=percent)
        response.cpu_samples.Append(sample)

    samples = self.grr_worker.stats_collector.io_samples
    for (timestamp, read_bytes, write_bytes) in samples:
      if arg.start_time < timestamp < arg.end_time:
        sample = rdfvalue.IOSample(
            timestamp=timestamp,
            read_bytes=read_bytes,
            write_bytes=write_bytes)
        response.io_samples.Append(sample)

    self.Send(response)

  def Send(self, response):
    self.SendReply(response)


class GetClientStatsAuto(GetClientStats):
  """This class is used to send the reply to a well known flow on the server."""

  def Send(self, response):
    self.grr_worker.SendReply(
        response,
        session_id=rdfvalue.SessionID("aff4:/flows/W:Stats"),
        response_id=0,
        request_id=0,
        priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
        message_type=rdfvalue.GrrMessage.Type.MESSAGE,
        require_fastpoll=False)


class SendStartupInfo(actions.ActionPlugin):

  in_rdfvalue = None
  out_rdfvalue = rdfvalue.StartupInfo

  well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:Startup")

  def Run(self, unused_arg, ttl=None):
    """Returns the startup information."""
    logging.debug("Sending startup information.")

    response = rdfvalue.StartupInfo(
        boot_time=long(psutil.boot_time() * 1e6),
        client_info=GetClientInformation())

    self.grr_worker.SendReply(
        response,
        session_id=self.well_known_session_id,
        response_id=0,
        request_id=0,
        priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
        message_type=rdfvalue.GrrMessage.Type.MESSAGE,
        require_fastpoll=False,
        ttl=ttl)
