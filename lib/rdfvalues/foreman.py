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

"""RDFValue instances related to the foreman implementation."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class ForemanRuleAction(rdfvalue.RDFProto):
  _proto = jobs_pb2.ForemanRuleAction

  rdf_map = dict(argv=rdfvalue.RDFProtoDict)


class ForemanAttributeRegex(rdfvalue.RDFProto):
  _proto = jobs_pb2.ForemanAttributeRegex


class ForemanAttributeInteger(rdfvalue.RDFProto):
  _proto = jobs_pb2.ForemanAttributeInteger


class ForemanRule(rdfvalue.RDFProto):
  """A Foreman rule RDF value."""
  _proto = jobs_pb2.ForemanRule

  rdf_map = dict(regex_rules=ForemanAttributeRegex,
                 integer_rules=ForemanAttributeInteger,
                 actions=ForemanRuleAction,
                 created=rdfvalue.RDFDatetime,
                 expires=rdfvalue.RDFDatetime,
                 description=rdfvalue.RDFString)

  @property
  def hunt_id(self):
    """Returns hunt id of this rule's actions or None if there's none."""
    for action in self.actions or []:
      if action.hunt_id is not None:
        return action.hunt_id


class ForemanRules(rdfvalue.RDFValueArray):
  """A list of rules that the foreman will apply."""
  rdf_type = ForemanRule
