#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""


from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server import cronjobs
from grr_response_server import hunt
from grr_response_server.flows.general import discovery as flows_discovery


class InterrogationHuntMixin(object):
  """Mixin that provides logic to start interrogation hunts."""

  def GetOutputPlugins(self):
    """Returns list of OutputPluginDescriptor objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of rdf_output_plugin.OutputPluginDescriptor objects
    """
    return []

  def StartInterrogationHunt(self):
    """Starts an interrogation hunt on all available clients."""
    flow_name = flows_discovery.Interrogate.__name__
    flow_args = flows_discovery.InterrogateArgs(lightweight=False)
    description = "Interrogate run by cron to keep host info fresh."

    hunt_id = hunt.CreateAndStartHunt(
        flow_name,
        flow_args,
        self.username,
        client_limit=0,
        client_rate=config.CONFIG["Cron.interrogate_client_rate"],
        crash_limit=config.CONFIG["Cron.interrogate_crash_limit"],
        description=description,
        duration=config.CONFIG["Cron.interrogate_duration"],
        output_plugins=self.GetOutputPlugins())
    self.Log("Started hunt %s.", hunt_id)


class InterrogateClientsCronJob(cronjobs.SystemCronJobBase,
                                InterrogationHuntMixin):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """

  frequency = rdfvalue.Duration.From(1, rdfvalue.WEEKS)
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration.From(30, rdfvalue.MINUTES)

  def Run(self):
    self.StartInterrogationHunt()
