#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Client actions related to administrating the client and its configuration."""


import os
import platform
import socket
import time


import psutil

import logging

from grr.client import actions
from grr.client import client_config
from grr.client import conf
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
                   kernel=kernel)


class Kill(actions.ActionPlugin):
  """A client action for terminating (killing) the client.

  Used for testing process respawn.
  """
  out_rdfvalue = rdfvalue.GRRMessage

  def Run(self, unused_arg):
    """Run the kill."""
    # Send a message back to the service to say that we are about to shutdown.
    reply = rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.Enum("OK"))
    # Queue up the response message, jump the queue.
    self.SendReply(reply, message_type=rdfvalue.GRRMessage.Enum("STATUS"),
                   priority=rdfvalue.GRRMessage.Enum("HIGH_PRIORITY") + 1)

    # Give the http thread some time to send the reply.
    self.grr_worker.Sleep(10)

    # Die ourselves.
    logging.info("Dying on request.")
    os._exit(242)  # pylint: disable=W0212


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
    end = time.time() + (arg.integer or 5)
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


class GetConfig(actions.ActionPlugin):
  """Retrieves the running configuration parameters."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.GRRConfig

  def Run(self, unused_arg):
    out = rdfvalue.GRRConfig()
    for field in out.DESCRIPTOR.fields_by_name:
      if hasattr(conf.FLAGS, field):
        setattr(out, field, getattr(conf.FLAGS, field))
    self.SendReply(out)


class UpdateConfig(actions.ActionPlugin):
  """Updates configuration parameters on the client."""
  in_rdfvalue = rdfvalue.GRRConfig

  UPDATEABLE_FIELDS = ["compression",
                       "foreman_check_frequency",
                       "location",
                       "max_post_size",
                       "max_out_queue",
                       "poll_min",
                       "poll_max",
                       "poll_slew",
                       "rss_max",
                       "verbose"]

  def Run(self, arg):
    """Does the actual work."""
    updated_keys = []
    disallowed_fields = []

    for field, value in arg.ListFields():
      if field in self.UPDATEABLE_FIELDS:
        setattr(conf.FLAGS, field, value)
        updated_keys.append(field)
      else:
        disallowed_fields.append(field)

    if disallowed_fields:
      logging.warning("Received an update request for restricted field(s) %s.",
                      ",".join(disallowed_fields))
    try:
      conf.PARSER.UpdateConfig(updated_keys)
    except (IOError, OSError):
      pass


class GetClientInfo(actions.ActionPlugin):
  """Obtains information about the GRR client installed."""
  out_rdfvalue = rdfvalue.ClientInformation

  def Run(self, unused_args):

    self.SendReply(
        client_name=client_config.GRR_CLIENT_NAME,
        client_version=client_config.GRR_CLIENT_VERSION,
        build_time=client_config.GRR_CLIENT_BUILDTIME,
        )


class GetClientStats(actions.ActionPlugin):
  """This retrieves some stats about the GRR process."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.ClientStats

  def Run(self, unused_arg):
    """Returns the client stats."""
    proc = psutil.Process(os.getpid())
    meminfo = proc.get_memory_info()
    response = rdfvalue.ClientStats(
        RSS_size=meminfo[0],
        VMS_size=meminfo[1],
        memory_percent=proc.get_memory_percent(),
        bytes_received=stats.STATS.Get("grr_client_received_bytes"),
        bytes_sent=stats.STATS.Get("grr_client_sent_bytes"),
        create_time=long(proc.create_time * 1e6),
        boot_time=long(psutil.BOOT_TIME * 1e6))

    samples = self.grr_worker.stats_collector.cpu_samples
    for (timestamp, user, system, percent) in samples:
      sample = rdfvalue.CpuSample(
          timestamp=long(timestamp * 1e6),
          user_cpu_time=user,
          system_cpu_time=system,
          cpu_percent=percent)
      response.cpu_samples.Append(sample)

    samples = self.grr_worker.stats_collector.io_samples
    for (timestamp, read_bytes, write_bytes) in samples:
      sample = rdfvalue.IOSample(
          timestamp=long(timestamp * 1e6),
          read_bytes=read_bytes,
          write_bytes=write_bytes)
      response.io_samples.Append(sample)

    self.Send(response)

  def Send(self, response):
    self.SendReply(response)


class GetClientStatsAuto(GetClientStats):
  """This class is used to send the reply to a well known flow on the server."""

  def Send(self, response):
    self.grr_worker.SendReply(response,
                              session_id="W:Stats",
                              response_id=0,
                              request_id=0,
                              priority=rdfvalue.GRRMessage.Enum("LOW_PRIORITY"),
                              message_type=rdfvalue.GRRMessage.Enum("MESSAGE"),
                              require_fastpoll=False)


class SendStartupInfo(actions.ActionPlugin):

  in_rdfvalue = None
  out_rdfvalue = rdfvalue.StartupInfo

  well_known_session_id = "aff4:/flows/W:Startup"

  def Run(self, unused_arg, ttl=None):
    """Returns the startup information."""

    response = rdfvalue.StartupInfo(
        boot_time=long(psutil.BOOT_TIME * 1e6),
        client_info=rdfvalue.ClientInformation(
            client_name=client_config.GRR_CLIENT_NAME,
            client_version=client_config.GRR_CLIENT_VERSION,
            build_time=client_config.GRR_CLIENT_BUILDTIME))

    self.grr_worker.SendReply(response,
                              session_id=self.well_known_session_id,
                              response_id=0,
                              request_id=0,
                              priority=rdfvalue.GRRMessage.Enum("LOW_PRIORITY"),
                              message_type=rdfvalue.GRRMessage.Enum("MESSAGE"),
                              require_fastpoll=False,
                              ttl=ttl)
