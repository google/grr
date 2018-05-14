#!/usr/bin/env python
"""Client actions related to administrating the client and its configuration."""

import logging
import os
import platform
import socket
import time
import traceback


import cryptography
from cryptography.hazmat.backends import openssl

import pkg_resources
import psutil
import pytsk3

from grr import config
from grr_response_client import actions
from grr_response_client.client_actions import tempfiles
from grr.lib import config_lib
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict


class Echo(actions.ActionPlugin):
  """Returns a message to the server."""
  in_rdfvalue = rdf_client.EchoRequest
  out_rdfvalues = [rdf_client.LogMessage]

  def Run(self, args):
    self.SendReply(args)


class GetHostname(actions.ActionPlugin):
  """Retrieves the host name of the client."""
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_args):
    self.SendReply(rdf_protodict.DataBlob(string=socket.gethostname()))


class GetPlatformInfo(actions.ActionPlugin):
  """Retrieves platform information."""
  out_rdfvalues = [rdf_client.Uname]

  def Run(self, unused_args):
    """Populate platform information into a Uname response."""
    self.SendReply(rdf_client.Uname.FromCurrentSystem())


class Kill(actions.ActionPlugin):
  """A client action for terminating (killing) the client.

  Used for testing process respawn.
  """
  out_rdfvalues = [rdf_flows.GrrMessage]

  def Run(self, unused_arg):
    """Run the kill."""
    # Send a message back to the service to say that we are about to shutdown.
    reply = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    # Queue up the response message, jump the queue.
    self.SendReply(
        reply,
        message_type=rdf_flows.GrrMessage.Type.STATUS,
        priority=rdf_flows.GrrMessage.Priority.HIGH_PRIORITY + 1)

    # Give the http thread some time to send the reply.
    self.grr_worker.Sleep(10)

    # Die ourselves.
    logging.info("Dying on request.")
    os._exit(242)  # pylint: disable=protected-access


class Hang(actions.ActionPlugin):
  """A client action for simulating the client becoming unresponsive (hanging).

  Used for testing nanny terminating the client.
  """
  in_rdfvalue = rdf_protodict.DataBlob

  def Run(self, arg):
    # Sleep a really long time.
    time.sleep(arg.integer or 6000)


class BusyHang(actions.ActionPlugin):
  """A client action that burns cpu cycles. Used for testing cpu limits."""
  in_rdfvalue = rdf_protodict.DataBlob

  def Run(self, arg):
    duration = 5
    if arg and arg.integer:
      duration = arg.integer
    end = time.time() + duration
    while time.time() < end:
      pass


class Bloat(actions.ActionPlugin):
  """A client action that uses lots of memory for testing."""
  in_rdfvalue = rdf_protodict.DataBlob

  def Run(self, arg):

    iterations = arg.integer or 1024  # Gives 1 gb.

    l = []

    for _ in range(iterations):
      l.append("X" * 1048576)  # 1 mb.

    time.sleep(60)


class GetConfiguration(actions.ActionPlugin):
  """Retrieves the running configuration parameters."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_protodict.Dict]

  BLOCKED_PARAMETERS = ["Client.private_key"]

  def Run(self, unused_arg):
    """Retrieve the configuration except for the blocked parameters."""

    out = self.out_rdfvalues[0]()
    for descriptor in config.CONFIG.type_infos:
      if descriptor.name in self.BLOCKED_PARAMETERS:
        value = "[Redacted]"
      else:
        try:
          value = config.CONFIG.Get(descriptor.name, default=None)
        except (config_lib.Error, KeyError, AttributeError, ValueError) as e:
          logging.info("Config reading error: %s", e)
          continue

      if value is not None:
        out[descriptor.name] = value

    self.SendReply(out)


class GetLibraryVersions(actions.ActionPlugin):
  """Retrieves version information for installed libraries."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_protodict.Dict]

  def GetSSLVersion(self):
    return openssl.backend.openssl_version_text()

  def GetCryptographyVersion(self):
    return cryptography.__version__

  def GetPSUtilVersion(self):
    return ".".join(map(utils.SmartUnicode, psutil.version_info))

  def GetProtoVersion(self):
    return pkg_resources.get_distribution("protobuf").version

  def GetTSKVersion(self):
    return pytsk3.TSK_VERSION_STR

  def GetPyTSKVersion(self):
    return pytsk3.get_version()

  library_map = {
      "pytsk": GetPyTSKVersion,
      "TSK": GetTSKVersion,
      "cryptography": GetCryptographyVersion,
      "SSL": GetSSLVersion,
      "psutil": GetPSUtilVersion,
  }

  error_str = "Unable to determine library version: %s"

  def Run(self, unused_arg):
    result = self.out_rdfvalues[0]()
    for lib, f in self.library_map.iteritems():
      try:
        result[lib] = f(self)
      except Exception:  # pylint: disable=broad-except
        result[lib] = self.error_str % traceback.format_exc()

    self.SendReply(result)


class UpdateConfiguration(actions.ActionPlugin):
  """Updates configuration parameters on the client."""
  in_rdfvalue = rdf_protodict.Dict

  UPDATABLE_FIELDS = {"Client.foreman_check_frequency",
                      "Client.server_urls",
                      "Client.max_post_size",
                      "Client.max_out_queue",
                      "Client.poll_min",
                      "Client.poll_max",
                      "Client.rss_max"}  # pyformat: disable

  def _UpdateConfig(self, filtered_arg, config_obj):
    for field, value in filtered_arg.items():
      config_obj.Set(field, value)

    try:
      config_obj.Write()
    except (IOError, OSError):
      pass

  def Run(self, arg):
    """Does the actual work."""
    try:
      if self.grr_worker.client.FleetspeakEnabled():
        raise ValueError("Not supported on Fleetspeak enabled clients.")
    except AttributeError:
      pass

    smart_arg = {utils.SmartStr(field): value for field, value in arg.items()}

    disallowed_fields = [
        field for field in smart_arg.keys()
        if field not in UpdateConfiguration.UPDATABLE_FIELDS
    ]

    if disallowed_fields:
      raise ValueError("Received an update request for restricted field(s) %s."
                       % ",".join(disallowed_fields))

    if platform.system() != "Windows":
      # Check config validity before really applying the changes. This isn't
      # implemented for our Windows clients though, whose configs are stored in
      # the registry, as opposed to in the filesystem.

      canary_config = config.CONFIG.CopyConfig()

      # Prepare a temporary file we'll write changes to.
      with tempfiles.CreateGRRTempFile(mode="w+") as temp_fd:
        temp_filename = temp_fd.name

      # Write canary_config changes to temp_filename.
      canary_config.SetWriteBack(temp_filename)
      self._UpdateConfig(smart_arg, canary_config)

      try:
        # Assert temp_filename is usable by loading it.
        canary_config.SetWriteBack(temp_filename)
      # Wide exception handling passed here from config_lib.py...
      except Exception:  # pylint: disable=broad-except
        logging.warning("Updated config file %s is not usable.", temp_filename)
        raise

      # If temp_filename works, remove it (if not, it's useful for debugging).
      os.unlink(temp_filename)

    # The changes seem to work, so push them to the real config.
    self._UpdateConfig(smart_arg, config.CONFIG)


def GetClientInformation():
  return rdf_client.ClientInformation(
      client_name=config.CONFIG["Client.name"],
      client_description=config.CONFIG["Client.description"],
      client_version=int(config.CONFIG["Source.version_numeric"]),
      build_time=config.CONFIG["Client.build_time"],
      labels=config.CONFIG.Get("Client.labels", default=None))


class GetClientInfo(actions.ActionPlugin):
  """Obtains information about the GRR client installed."""
  out_rdfvalues = [rdf_client.ClientInformation]

  def Run(self, unused_args):
    self.SendReply(GetClientInformation())


class GetClientStats(actions.ActionPlugin):
  """This retrieves some stats about the GRR process."""
  in_rdfvalue = rdf_client.GetClientStatsRequest
  out_rdfvalues = [rdf_client.ClientStats]

  def Run(self, arg):
    """Returns the client stats."""
    if arg is None:
      arg = rdf_client.GetClientStatsRequest()

    proc = psutil.Process(os.getpid())
    meminfo = proc.memory_info()
    boot_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(psutil.boot_time())
    create_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(proc.create_time())
    response = rdf_client.ClientStats(
        RSS_size=meminfo.rss,
        VMS_size=meminfo.vms,
        memory_percent=proc.memory_percent(),
        bytes_received=stats.STATS.GetMetricValue("grr_client_received_bytes"),
        bytes_sent=stats.STATS.GetMetricValue("grr_client_sent_bytes"),
        create_time=create_time,
        boot_time=boot_time)

    response.cpu_samples = self.grr_worker.stats_collector.CpuSamplesBetween(
        start_time=arg.start_time, end_time=arg.end_time)
    response.io_samples = self.grr_worker.stats_collector.IOSamplesBetween(
        start_time=arg.start_time, end_time=arg.end_time)

    self.Send(response)

  def Send(self, response):
    self.SendReply(response)


class GetClientStatsAuto(GetClientStats):
  """This class is used to send the reply to a well known flow on the server."""

  def Send(self, response):
    self.grr_worker.SendReply(
        rdf_client.ClientStats.Downsampled(response),
        session_id=rdfvalue.SessionID(queue=queues.STATS, flow_name="Stats"),
        response_id=0,
        request_id=0,
        priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
        message_type=rdf_flows.GrrMessage.Type.MESSAGE,
        require_fastpoll=False)


class SendStartupInfo(actions.ActionPlugin):

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.StartupInfo]

  well_known_session_id = rdfvalue.SessionID(flow_name="Startup")

  def Run(self, unused_arg, ttl=None):
    """Returns the startup information."""
    logging.debug("Sending startup information.")
    boot_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(psutil.boot_time())
    response = rdf_client.StartupInfo(
        boot_time=boot_time, client_info=GetClientInformation())

    self.grr_worker.SendReply(
        response,
        session_id=self.well_known_session_id,
        response_id=0,
        request_id=0,
        priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
        message_type=rdf_flows.GrrMessage.Type.MESSAGE,
        require_fastpoll=False,
        ttl=ttl)
