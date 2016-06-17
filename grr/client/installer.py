#!/usr/bin/env python
"""This is the GRR client installer module.

GRR allows several installers to be registered as plugins. The
installers are executed when the client is deployed to a target system
in their specified order (according to the registry plugin system).

Installers are usually used to upgrade existing clients and setup
clients in unusual situations.
"""
import logging
import os
import sys

from grr.client import comms
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import flows as rdf_flows


class Installer(registry.HookRegistry):
  """A GRR installer plugin.

  Modules can register special actions which only run on installation
  by extending this base class. Execution order is controlled using
  the same mechanism provided by HookRegistry - i.e. by declaring
  "pre" and "order" attributes.
  """

  __metaclass__ = registry.MetaclassRegistry


def InstallerNotifyServer():
  """An emergency function Invoked when the client installation failed."""
  # We make a temporary emergency config file to contain the new client id. Note
  # that the notification callback does not really mean anything to us, since
  # the client is not installed and we dont have basic interrogate information.
  config_lib.CONFIG.SetWriteBack("temp.yaml")

  try:
    log_data = open(config_lib.CONFIG["Installer.logfile"], "rb").read()
  except (IOError, OSError):
    log_data = ""

  # Start the client and send the server a message, then terminate. The
  # private key may be empty if we did not install properly yet. In this case,
  # the client will automatically generate a random client ID and private key
  # (and the message will be unauthenticated since we never enrolled.).
  comms.CommsInit().RunOnce()

  client = comms.GRRHTTPClient(
      ca_cert=config_lib.CONFIG["CA.certificate"],
      private_key=config_lib.CONFIG.Get("Client.private_key"))

  client.client_worker.SendReply(
      session_id=rdfvalue.FlowSessionID(flow_name="InstallationFailed"),
      message_type=rdf_flows.GrrMessage.Type.STATUS,
      request_id=0,
      response_id=0,
      rdf_value=rdf_flows.GrrStatus(
          status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
          error_message="Installation failed.",
          backtrace=log_data[-10000:]))

  client.RunOnce()


def RunInstaller():
  """Run all registered installers.

  Run all the current installers and then exit the process.
  """

  try:
    os.makedirs(os.path.dirname(config_lib.CONFIG["Installer.logfile"]))
  except OSError:
    pass

  # Always log to the installer logfile at debug level. This way if our
  # installer fails we can send detailed diagnostics.
  handler = logging.FileHandler(config_lib.CONFIG["Installer.logfile"],
                                mode="wb")

  handler.setLevel(logging.DEBUG)

  # Add this to the root logger.
  logging.getLogger().addHandler(handler)

  # Ordinarily when the client starts up, the local volatile
  # configuration is read. Howevwer, when running the installer, we
  # need to ensure that only the installer configuration is used so
  # nothing gets overridden by local settings. We there must reload
  # the configuration from the flag and ignore the Config.writeback
  # location.
  config_lib.CONFIG.Initialize(filename=flags.FLAGS.config, reset=True)
  config_lib.CONFIG.AddContext(
      "Installer Context", "Context applied when we run the client installer.")

  logging.warn("Starting installation procedure for GRR client.")
  try:
    Installer().Init()
  except Exception as e:  # pylint: disable=broad-except
    # Ouch! we failed to install... Not a lot we can do
    # here - just log the error and give up.
    logging.exception("Installation failed: %s", e)

    # Let the server know about this just in case.
    InstallerNotifyServer()

    # Error return status.
    sys.exit(-1)

  # Exit successfully.
  sys.exit(0)
