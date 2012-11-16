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


"""A general flow to run Volatility plugins."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.proto import jobs_pb2


class VolatilityPlugins(flow.GRRFlow):
  """A flow to run Volatility plugins.

  This flow runs a volatility plugin. It relies on a memory driver
  being loaded on the client or it will fail.

  Args:
    plugins: A list of plugins to run.
    device: Name of the device the memory driver created.
    output: The path to the output container for this find. Will be created
            under the client. supports format variables {u}, {p} and {t} for
            user, plugin and time. E.g. /analysis/{p}/{u}-{t}.
  """

  category = "/Volatility/"

  out_protobuf = jobs_pb2.VolatilityResponse
  flow_typeinfo = {"profile": type_info.StringOrNone()}

  response_obj = "VolatilityResponse"

  def __init__(self, plugins="modules,dlllist,pslist", devicepath=r"\\.\pmem",
               profile=None, output="analysis/{p}/{u}-{t}", **kw):
    super(VolatilityPlugins, self).__init__(**kw)
    device = jobs_pb2.Path(path=devicepath, pathtype=jobs_pb2.Path.MEMORY)
    self.request = jobs_pb2.VolatilityRequest(device=device)
    self.plugins = plugins
    for plugin in plugins.split(","):
      self.request.plugins.append(plugin.strip())
    if profile:
      self.request.profile = profile
    self.output = output
    self.output_urn = ""

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    self.CallClient("VolatilityAction", self.request, next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    if not responses.success:
      self.Log("Error running plugins: %s.", responses.status)
      return

    for response in responses:
      output = self.output.format(t=time.time(), u=self.user, p=response.plugin)
      self.output_urn = aff4.ROOT_URN.Add(self.client_id).Add(output)

      fd = aff4.FACTORY.Create(self.output_urn, self.response_obj, mode="rw",
                               token=self.token)

      fd.Set(fd.Schema.DESCRIPTION("Volatility plugin by %s: %s" % (
          self.user, str(self.request))))

      fd.Set(fd.Schema.RESULT(response))

      fd.Close()

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.output_urn,
                "Ran volatility modules %s" % self.plugins)


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

  def __init__(self, devicepath=r"\\.\pmem", profile=None,
               output="analysis/{p}/{u}-{t}", **kw):
    super(Mutexes, self).__init__(plugins="mutantscan", devicepath=devicepath,
                                  profile=profile, output=output, **kw)
