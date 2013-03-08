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
from grr.client import conf as flags

from grr.lib import config_lib
from grr.lib import log
from grr.lib import rdfvalue
from grr.lib import registry


flags.DEFINE_bool("install", False,
                  "Specify this to install the client.")


class Installer(registry.HookRegistry):
  """A GRR installer plugin.

  Modules can register special actions which only run on installation
  by extending this base class. Execution order is controlled using
  the same mechanism provided by HookRegistry - i.e. by declaring
  "pre" and "order" attributes.
  """

  __metaclass__ = registry.MetaclassRegistry


class InstallerInit(registry.InitHook):
  """Run all installer plugins in their specific dependency list."""
  pre = ["SetUpLogging", "ConfigLibInit", "ClientPlugins"]

  def NotifyServer(self):
    """An emergency function Invoked when the client installation failed."""

    try:
      log_data = open(config_lib.CONFIG["Logging.filename"], "rb").read()
    except (IOError, OSError):
      log_data = ""

    # Start the client and send the server a message, then terminate. The
    # private key may be empty if we did not install properly yet. In this case,
    # the client will automatically generate a random client ID and private key
    # (and the message will be unauthenticated since we never enrolled.).
    client = comms.GRRHTTPClient(
        ca_cert=config_lib.CONFIG["CA.certificate"],
        private_key=config_lib.CONFIG["Client.private_key"])

    client.GetServerCert()
    client.client_worker.SendReply(
        session_id="W:InstallationFailed",
        message_type=rdfvalue.GRRMessage.Enum("STATUS"),
        request_id=0, response_id=0,
        rdf_value=rdfvalue.GrrStatus(
            status=rdfvalue.GrrStatus.Enum("GENERIC_ERROR"),
            error_message="Installation failed.",
            backtrace=log_data[-10000:]))

    client.RunOnce()

  def RunOnce(self):
    """Run all installers.

    If the flag --install is provided, we run all the current installers and
    then exit the process.
    """
    if flags.FLAGS.install:
      # Start to log verbosely.
      flags.FLAGS.verbose = True
      log.SetLogLevels()

      logging.warn("Starting installation procedure for GRR client.")
      try:
        Installer().Init()
      except Exception as e:  # pylint: disable=broad-except
        # Ouch! we failed to install... Not a lot we can do
        # here - just log the error and give up.
        logging.exception("Installation failed: %s", e)

        # Let the server know about this just in case.
        self.NotifyServer()

      # Exit successfully.
      sys.exit(0)


config_lib.DEFINE_list("ClientBuilder.plugins", [],
                       "Plugins that will be loaded during installation.")


class InstallerPlugins(Installer):
  """Load installer plugins on the client.

  These plugins are only loaded during installation. We load very
  early to allow plugins to run at arbitrary points in the
  installation process.
  """

  order = 10

  def RunOnce(self):
    """Load plugins relative to our current binary location."""
    for plugin in config_lib.CONFIG["ClientBuilder.plugins"]:
      config_lib.PluginLoader.LoadPlugin(
          os.path.join(os.path.dirname(sys.executable),
                       plugin))

    # Force the Hook registry to re-calculate hook ordering. Without this, it
    # will be impossible to introduce a new hook through a plugin which honours
    # the normal ordering logic, because the ordering for this run has already
    # been determined before we got called.
    raise StopIteration()
