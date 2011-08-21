#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""Well known flows.

These are predefined static flows that are core to the operation of
the whole system. They have a well known session id so any client can
send messages to these flows without being contacted first.
"""


import time

from grr.lib import data_store
from grr.lib import flow
from grr.proto import jobs_pb2


class Ping(flow.WellKnownFlow):
  """A handler for ping messages."""
  well_known_session_id = "W:Ping"

  @flow.StateHandler(jobs_pb2.PrintStr)
  def ProcessMessage(self, message):
    """Update the last ping time in the datastore."""
    print "Received ping from %s at %s: %s" % (
        self.message.source,
        time.time(),
        message.data)

    #TODO(user): Can this go away?
    data_store.DB.Set(self.message.source,
                      data_store.DB.schema.PING,
                      str(time.time()))
