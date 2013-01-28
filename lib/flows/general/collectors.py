#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""These flows are designed for high performance transfers."""



from grr.lib import aff4
from grr.lib import artifact
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import type_info


class ArtifactCollectorFlow(flow.GRRFlow):
  """Flow that takes a list of artifacts and collects them.

  NOTE!!!! the artifact_object is not preserved across Collect and
  Process phases. It is reinitialized as it is used in an async process.
  """

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.List(
          description="A list of Artifact class names.",
          name="artifact_list",
          validator=type_info.String(),
          ),
      type_info.Bool(
          description="Whether raw filesystem access should be used.",
          name="use_tsk",
          default=True)
      )

  @flow.StateHandler(next_state="ProcessCollected")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = self.client.Get(self.client.Schema.SYSTEM)

    self.artifact_class_names = self.artifact_list
    self.collected_count = 0
    self.failed_count = 0

    for cls_name in self.artifact_class_names:
      artifact_cls = self._GetArtifactClassFromName(cls_name)
      artifact_obj = artifact_cls(self, use_tsk=self.use_tsk)

      self._current_artifact = cls_name
      artifact_obj.Collect()
      self._current_artifact = None

  @flow.StateHandler()
  def ProcessCollected(self, responses):
    """Each individual collector will call back into here."""
    flow_name = self.__class__.__name__
    artifact_cls_name = responses.request_data["artifact_name"]
    if responses.success:
      self.Log("Artifact %s completed successfully in flow %s",
               artifact_cls_name, flow_name)
      self.collected_count += 1
    else:
      self.Log("Artifact %s collection failed. Flow %s failed to complete",
               artifact_cls_name, flow_name)
      self.failed_count += 1
      return

    # Now we've finished collection process the results.
    artifact_cls = self._GetArtifactClassFromName(artifact_cls_name)
    artifact_obj = artifact_cls(self, use_tsk=self.use_tsk)
    artifact_obj.Process(responses)

  def _GetArtifactClassFromName(self, name):
    if name not in artifact.Artifact.classes:
      raise RuntimeError("ArtifactCollectorFlow failed due to invalid Artifact"
                         " %s" % name)
    return artifact.Artifact.classes[name]

  def GetFiles(self, path_list, path_type):
    """Get a set of files."""
    for path in path_list:
      artifact_cls = self._GetArtifactClassFromName(self._current_artifact)
      path_args = artifact_cls.PATH_ARGS
      new_path = flow_utils.InterpolatePath(path, self.client,
                                            path_args=path_args)

      self.CallFlow(
          "GetFile", pathspec=rdfvalue.RDFPathSpec(
              path=new_path, pathtype=path_type),
          request_data={"artifact_name": self._current_artifact},
          next_state="ProcessCollected"
          )

  def GetFile(self, path, path_type):
    """Get a set of files."""
    self.GetFiles([path], path_type=path_type)

  @flow.StateHandler()
  def End(self):
    self.Notify("FlowStatus", self.client_id,
                "Completed artifact collection of %s. Collected %d. Errors %d."
                % (self.artifact_class_names, self.collected_count,
                   self.failed_count))
