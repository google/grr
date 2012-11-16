#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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

"""Test the hunt_view interface."""



import traceback

from grr.lib import aff4
from grr.lib import hunt_test
from grr.lib import test_lib
from grr.lib.flows.general import hunts
from grr.proto import jobs_pb2


def CreateHunts():
  """Create some test hunts."""
  thunt = hunt_test.HuntTest(methodName="run")
  thunt.setUp()
  return thunt


class TestHuntView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestHuntView, self).setUp()
    self.h = CreateHunts()

  def CreateSampleHunt(self):
    self.client_ids = self.h.SetupClients(10)
    hunt = hunts.SampleHunt(token=self.token)

    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    self.foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                     token=self.token)
    for client_id in self.client_ids:
      self.foreman.AssignTasksToClient(client_id)
    return hunt

  def CleanUpState(self):
    self.foreman.Set(self.foreman.Schema.RULES())
    self.foreman.Close()
    self.h.DeleteClients(10)

  def testHuntView(self):
    """Test that we can see all the hunt data."""

    # Create some clients and a hunt to view.
    hunt = self.CreateSampleHunt()
    # Run the hunt.
    client_mock = self.h.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)
    hunt.LogResult(self.client_ids[2], "Result 1")

    # Log an error just with some random traceback.
    hunt.LogClientError(self.client_ids[1], "Client Error 1",
                        traceback.format_exc())

    hunt_obj = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)
    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    self.assertEqual(len(set(started)), 10)

    # Open up and click on View Hunts.
    sel = self.selenium
    sel.open("/")
    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    self.WaitUntil(sel.is_element_present, "css=a[grrtarget=ManageHunts]")
    sel.click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(sel.is_text_present, "SampleHunt")

    # Select a Hunt.
    sel.click("css=td:contains('SampleHunt')")

    # Check we can now see the details.
    self.WaitUntil(sel.is_element_present, "css=table[class=proto_table]")
    self.WaitUntil(sel.is_text_present, "Client Count")
    self.WaitUntil(sel.is_text_present, "Hunt URN")

    # Click the Log Tab.
    sel.click("css=a[renderer=HuntLogRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(sel.is_text_present, "Result 1")

    # Click the Error Tab.
    sel.click("css=a[renderer=HuntErrorRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(sel.is_text_present, "Client Error 1")

    # Click the Rules Tab.
    sel.click("css=a[renderer=HuntRuleRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntRuleRenderer_]")
    self.WaitUntil(sel.is_text_present, "GRR client")

    self.CleanUpState()

  def testHuntDetailView(self):
    """Test the detailed client view works."""
    # Create some clients and a hunt to view.
    hunt = self.CreateSampleHunt()
    # Run the hunt.
    client_mock = self.h.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt.LogClientError(self.client_ids[1], "Client Error 1",
                        traceback.format_exc())

    # Open up and click on View Hunts then the first Hunt.
    sel = self.selenium
    sel.open("/")
    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    sel.click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(sel.is_text_present, "SampleHunt")
    sel.click("css=td:contains('SampleHunt')")

    self.WaitUntil(sel.is_element_present,
                   "css=a[renderer=HuntOverviewRenderer]")

    # Click the Overview Tab then the Details Link.
    sel.click("css=a[renderer=HuntOverviewRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntOverviewRenderer_]")
    self.WaitUntil(sel.is_text_present, "Hunt URN")
    sel.click("css=a[id^=ViewHuntDetails_]")
    self.WaitUntil(sel.is_text_present, "Viewing Hunt W:")

    self.WaitUntil(sel.is_text_present, "COMPLETED")
    self.WaitUntil(sel.is_text_present, "BAD")

    # Select the first client which should have errors.
    sel.click("css=td:contains('%s')" % self.client_ids[1])
    self.WaitUntil(sel.is_element_present,
                   "css=div[id^=HuntClientOverviewRenderer_]")
    self.WaitUntil(sel.is_text_present, "Last Checkin")

    sel.click("css=a:[renderer=HuntLogRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(sel.is_text_present, "No entries")

    sel.click("css=a:[renderer=HuntErrorRenderer]")
    self.WaitUntil(sel.is_element_present, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(sel.is_text_present, "Client Error 1")

    sel.click("css=a:[renderer=HuntHostInformationRenderer]")
    self.WaitUntil(sel.is_element_present,
                   "css=div[id^=HuntHostInformationRenderer_]")
    self.WaitUntil(sel.is_text_present, "CLIENT_INFO")
    self.WaitUntil(sel.is_text_present, "VFSGRRClient")

    self.CleanUpState()
