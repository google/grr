#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.aff4_rekall."""


from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class AFF4RekallTest(test_lib.AFF4ObjectTest):

  # pylint: disable=line-too-long
  JSON_MESSAGE = u"""[["l",{}],["m",{"tool_name":"rekall","plugin_name":"dlllist","tool_version":"1.0.2"}],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",448],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",748],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",756],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",888],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",964],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",1052],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",1144],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",1264],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",1624],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",1776],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",2020],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",2644],["f",["*","Unable to read PEB for task.\\n"]],["s",{"name":null}],["f","{0} pid: {1:6}\\n","svchost.exe",2800],["f",["*","Unable to read PEB for task.\\n"]]]"""
  # pylint: enable=line-too-long

  def testRenderAsText(self):
    collection = aff4.FACTORY.Create("aff4:/rekall_response_test",
                                     "RekallResponseCollection",
                                     token=self.token, mode="rw")
    response = rdfvalue.RekallResponse()
    response.json_messages = self.JSON_MESSAGE
    collection.Add(response)
    text = collection.RenderAsText()
    self.assertTrue("svchost.exe" in text)
    self.assertTrue("** Plugin dlllist **" in text)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
