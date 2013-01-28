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

"""Test the collection viewer interface."""

from grr.client import conf as flags

from grr.client import vfs
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib

FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG


class TestContainerViewer(test_lib.GRRSeleniumTest):
  """Test the collection viewer interface."""

  @staticmethod
  def CreateCollectionFixture():
    """Creates a new collection we can play with."""
    # Create a client for testing
    client_id = "C.0000000000000004"
    token = data_store.ACLToken("test", "Fixture")

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)
    fd.Set(fd.Schema.CERT, aff4.FACTORY.RDFValue("RDFX509Cert")(
        CONFIG["Test.Test_Client_Cert"]))
    fd.Close()

    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.RDFPathSpec.Enum("OS")] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("Find")
    output_path = "aff4:/%s/analysis/FindFlowTest" % client_id

    findspec = rdfvalue.RDFFindSpec(path_regex="bash")
    findspec.pathspec.path = "/"
    findspec.pathspec.pathtype = rdfvalue.RDFPathSpec.Enum("OS")

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=client_id,
        findspec=findspec, token=token, output=output_path):
      pass

    # Make the view a bit more interesting
    fd = aff4.FACTORY.Open(output_path, mode="rw", token=token)
    fd.CreateView(["stat.st_mtime", "type", "stat.st_size", "size", "Age"])
    fd.Close()

  def setUp(self):
    super(TestContainerViewer, self).setUp()

    # Create a new collection
    self.CreateCollectionFixture()

  def testContainerViewer(self):
    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    sel.type("css=input[name=q]", "0004")
    sel.click("css=input[type=submit]")

    self.WaitUntilEqual(u"C.0000000000000004",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0004')")

    # Go to Browse VFS
    self.WaitUntil(sel.is_element_present,
                   "css=a:contains('Browse Virtual Filesystem')")
    sel.click("css=a:contains('Browse Virtual Filesystem')")

    # Navigate to the analysis directory
    self.WaitUntil(sel.is_element_present, "link=analysis")
    sel.click("link=analysis")

    self.WaitUntil(sel.is_element_present,
                   "css=span[type=subject]:contains(\"FindFlowTest\")")
    sel.click("css=span[type=subject]:contains(\"FindFlowTest\")")

    self.WaitUntil(sel.is_element_present, "css=td:contains(\"VIEW\")")
    self.assert_("View details" in sel.get_text(
        "css=a[href=\"#"
        "c=C.0000000000000004&"
        "container=aff4%3A%2FC.0000000000000004%2Fanalysis%2FFindFlowTest&"
        "main=ContainerViewer&"
        "reason=\"]"))

    sel.click("css=a:contains(\"View details\")")

    self.WaitUntil(sel.is_element_present, "css=button[id=export]")

    self.WaitUntil(sel.is_element_present, "css=#_C_2E0000000000000004")
    sel.click("css=#_C_2E0000000000000004 ins.jstree-icon")

    self.WaitUntil(sel.is_element_present,
                   "css=#_C_2E0000000000000004-fs")
    sel.click("css=#_C_2E0000000000000004-fs ins.jstree-icon")

    self.WaitUntil(sel.is_element_present,
                   "css=#_C_2E0000000000000004-fs-os")
    sel.click("css=#_C_2E0000000000000004-fs-os ins.jstree-icon")

    # Navigate to the bin C.0000000000000001 directory
    self.WaitUntil(sel.is_element_present, "link=c")
    sel.click("link=c")

    # Check the filter string
    self.assertEqual("subject startswith 'aff4:/C.0000000000000004/fs/os/c/'",
                     sel.get_value("query"))

    # We should have exactly 4 files
    self.WaitUntilEqual(4, sel.get_css_count, "css=.tableContainer  tbody > tr")

    # Check the rows
    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin %(client_id)s/bash",
        sel.get_text("css=.tableContainer  tbody > tr:nth(0) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin %(client_id)s/rbash",
        sel.get_text("css=.tableContainer  tbody > tr:nth(1) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin/bash",
        sel.get_text("css=.tableContainer  tbody > tr:nth(2) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin/rbash",
        sel.get_text("css=.tableContainer  tbody > tr:nth(3) td:nth(1)"))

    # Check that query filtering works (Pressing enter)
    sel.type("query", "stat.st_size < 5000")
    sel.click("css=form:contains('Query') input[type=submit]")

    # This should be fixed eventually and the test turned back on.
    self.WaitUntilContains("Filtering by subfields is not implemented yet.",
                           sel.get_text, "css=#footer")

    # self.WaitUntilEqual("4874", sel.get_text,
    #                    "css=.tableContainer  tbody > tr:nth(0) td:nth(4)")

    # We should have exactly 1 file
    # self.assertEqual(
    #    1, sel.get_css_count("css=.tableContainer  tbody > tr"))
