#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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

"""Tests for the Timeline viewer flow."""



from grr.client import vfs

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestTimelineView(test_lib.GRRSeleniumTest):
  """Test the timeline view."""

  @staticmethod
  def CreateTimelineFixture():
    """Creates a new timeline fixture we can play with."""
    # Create a client for testing
    client_id = "C.0000000000000001"

    token = access_control.ACLToken("test", "fixture")

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)
    fd.Set(fd.Schema.CERT(config_lib.CONFIG["Client.certificate"]))
    fd.Close()

    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.RDFPathSpec.Enum("OS")] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("ListDirectory")
    output_path = "analysis/Timeline/MAC"

    for _ in test_lib.TestFlowHelper(
        "RecursiveListDirectory", client_mock, client_id=client_id,
        pathspec=rdfvalue.RDFPathSpec(
            path="/", pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
        token=token):
      pass

    # Now make a timeline
    for _ in test_lib.TestFlowHelper(
        "MACTimes", client_mock, client_id=client_id, token=token,
        path="aff4:/%s/" % client_id, output=output_path):
      pass

  def setUp(self):
    test_lib.GRRSeleniumTest.setUp(self)

    # Create a new collection
    self.CreateTimelineFixture()

  def testTimelineViewer(self):
    sel = self.selenium
    # Open the main page
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "client_query")
    sel.type("client_query", "0001")
    sel.click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")

    # Go to Browse VFS
    self.WaitUntil(sel.is_element_present,
                   "css=a:contains('Browse Virtual Filesystem')")
    sel.click("css=a:contains('Browse Virtual Filesystem')")

    # Navigate to the analysis directory
    self.WaitUntil(sel.is_element_present, "css=#_analysis")
    sel.click("css=#_analysis ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "link=Timeline")
    sel.click("link=Timeline")

    self.WaitUntil(sel.is_element_present,
                   "css=span[type=subject]:contains(\"MAC\")")
    sel.click("css=span[type=subject]:contains(\"MAC\")")

    self.WaitUntil(sel.is_element_present, "css=td:contains(\"TIMELINE\")")
    self.assert_("View details" in sel.get_text("css=td div.default_view a"))

    sel.click("css=a:contains(\"View details\")")

    self.WaitUntil(sel.is_element_present, "container_query")

    sel.type("css=input#container_query",
             "subject contains bash and timestamp > 2010")

    # Use the hidden submit button to issue the query. Ordinarily users have to
    # press enter here as they do not see the submit button. But pressing enter
    # does not work with chrome.
    sel.click("css=#toolbar_main form[name=query_form] button[type=submit]")

    self.WaitUntilContains("2011-03-07 12:50:20",
                           sel.get_text, "css=tbody tr:first")

    sel.click("css=tbody tr:first td")

    self.WaitUntilContains("2011-03-07 12:50:20", sel.get_text,
                           "css=.tab-content h3")

    # Check that the embedded stat proto is properly presented
    self.assertTrue("2011-03-07 12:50:20" in sel.get_text(
        "css=td.proto_value tr:contains(st_atime) td.proto_value"))
