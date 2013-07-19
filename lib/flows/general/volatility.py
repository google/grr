#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A general flow to run Volatility plugins."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info


class VolatilityPlugins(flow.GRRFlow):
  """A flow to run Volatility plugins.

  This flow runs a volatility plugin. It relies on a memory driver
  being loaded on the client or it will fail.
  """
  category = "/Volatility/"
  response_obj = "VolatilityResponse"

  # Allow running these plugins on any version or OS.
  plugin_whitelist = ["raw2dmp", "imagecopy"]

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.VolatilityRequestType(
          description="A request for the client's volatility subsystem."),

      type_info.String(
          description="""
The path to the output container for this flow. Will be created
under the client. supports format variables {u}, {p} and {t} for
user, plugin and time. E.g. /analysis/{p}/{u}-{t}.""",
          name="output",
          default="analysis/{p}/{u}-{t}"),

      type_info.String(
          description="A comma separated list of plugins.",
          name="plugins",
          default=""),
      )

  def GetPlugins(self):
    return self.state.plugins.split(",")

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    """Call the client with the volatility actions."""
    plugin_list = self.GetPlugins()
    for plugin in plugin_list:
      if plugin not in self.state.request.args:
        self.state.request.args[plugin] = {}

      # Also support this deprecated request method for old clients.
      self.state.request.plugins.Append(plugin)

    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    # Disable running everything but the raw2dmp action for non-windows and for
    # windows 2000.
    # This will need revision once we add further volatility support.
    system = client.Get(client.Schema.SYSTEM)
    version = str(client.Get(client.Schema.OS_VERSION))

    plugin_list = set(plugin_list)
    whitelist = set(self.plugin_whitelist)
    # If not all requested plugins are whitelisted...
    if not plugin_list.issubset(whitelist):
      if system == "Windows":
        if version[0:3] <= "5.0":
          raise flow.FlowError("Cannot run volatility on versions < Win2K")
      else:
        raise flow.FlowError(
            "Volatility on non-Windows only supports plugins %s." %
            self.plugin_whitelist)

    self.CallClient("VolatilityAction", self.state.request,
                    next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the results."""
    self.state.Register("output_urn", None)
    if not responses.success:
      self.Log("Error running plugins: %s.", responses.status)
      return

    self.Log("Client returned %s responses." % len(responses))

    for response in responses:
      output = self.state.output.format(t=time.time(),
                                        u=self.state.context.user,
                                        p=response.plugin)

      self.state.output_urn = self.client_id.Add(output)

      fd = aff4.FACTORY.Create(self.state.output_urn, self.response_obj,
                               mode="rw", token=self.token)

      fd.Set(fd.Schema.DESCRIPTION("Volatility plugin by %s: %s" % (
          self.state.context.user, str(self.state.request))))

      fd.Set(fd.Schema.RESULT(response))

      fd.Close()

  @flow.StateHandler()
  def End(self):
    if not self.state.output_urn:
      self.state.output_urn = self.client_id
    self.Notify("ViewObject", self.state.output_urn,
                "Ran volatility modules %s" % self.GetPlugins())


class Mutexes(VolatilityPlugins):
  """A flow to retrieve mutexes on Windows.

  This flow uses a volatility plugin to find mutexes. It relies
  on a memory driver being loaded on the client or it will fail.

  Args:
    device: Name of the device the memory driver created.
    output: The path to the output container for this find. Will be created
            under the client. supports format variables {u} and {t} for user and
            time. E.g. /analysis/mutexes/{u}-{t}.
  """

  flow_typeinfo = VolatilityPlugins.flow_typeinfo.Remove("plugins")

  def GetPlugins(self):
    return ["mutantscan"]
