#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""


from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_proto import flows_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import cronjobs
from grr_response_server import hunt
from grr_response_server.flows.general import discovery as flows_discovery
from grr_response_server.models import hunts as models_hunts


class InterrogationHuntMixin(object):
  """Mixin that provides logic to start interrogation hunts."""

  def GetOutputPlugins(
      self,
  ) -> list[output_plugin_pb2.OutputPluginDescriptor]:
    """Returns list of OutputPluginDescriptor objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of OutputPluginDescriptor objects
    """
    return []

  def StartInterrogationHunt(self):
    """Starts an interrogation hunt on all available clients."""
    flow_name = flows_discovery.Interrogate.__name__
    flow_args = flows_pb2.InterrogateArgs(lightweight=False)

    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=flow_name,
        flow_args=flow_args,
        creator=self.username,  # pylint: disable=attribute-error
    )
    hunt_obj.description = "Interrogate run by cron to keep host info fresh."

    hunt_obj.client_limit = 0
    hunt_obj.client_rate = config.CONFIG["Cron.interrogate_client_rate"]

    # The config returns a Duration, but the hunt requires DurationSeconds.
    duration = config.CONFIG["Cron.interrogate_duration"]
    hunt_obj.duration = duration.ToInt(rdfvalue.SECONDS)

    hunt_obj.crash_limit = config.CONFIG["Cron.interrogate_crash_limit"]

    hunt_obj.output_plugins.extend(self.GetOutputPlugins())

    hunt_id = hunt.CreateAndStartHunt(hunt_obj)
    self.Log("Started hunt %s.", hunt_id)


class InterrogateClientsCronJob(cronjobs.SystemCronJobBase,
                                InterrogationHuntMixin):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """

  frequency = rdfvalue.DurationSeconds.From(1, rdfvalue.WEEKS)
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.DurationSeconds.From(30, rdfvalue.MINUTES)

  def Run(self):
    self.StartInterrogationHunt()
