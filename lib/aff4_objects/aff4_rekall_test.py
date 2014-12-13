#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.aff4_rekall."""

import os


from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class AFF4RekallTest(test_lib.AFF4ObjectTest):

  def Disabled_testRenderAsText(self):
    rekall_result_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                      "rekall_pslist_result.dat")
    collection = aff4.FACTORY.Create("aff4:/rekall_response_test",
                                     "RekallResponseCollection",
                                     token=self.token, mode="rw")
    response = rdfvalue.RekallResponse()
    response.json_messages = open(rekall_result_file, "rb").read()
    collection.Add(response)
    text = collection.RenderAsText()
    self.assertTrue("svchost.exe" in text)
    self.assertTrue("** Plugin dlllist **" in text)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
