#!/usr/bin/env python
"""Tests for grr.parsers.wmi_parser."""

import platform
import unittest

from grr.lib import flags
from grr.lib.parsers import wmi_parser
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import wmi as rdf_wmi
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class WMIParserTest(flow_test_lib.FlowTestsBaseclass):

  @unittest.skipIf(
      platform.system() == "Darwin",
      ("IPv6 address strings are cosmetically slightly different on OS X, "
       "and we only expect this parsing code to run on Linux or maybe Windows"))
  def testInterfaceParsing(self):
    parser = wmi_parser.WMIInterfacesParser()
    rdf_dict = rdf_protodict.Dict()
    mock_config = client_test_lib.WMIWin32NetworkAdapterConfigurationMock
    wmi_properties = mock_config.__dict__.iteritems()
    for key, value in wmi_properties:
      if not key.startswith("__"):
        try:
          rdf_dict[key] = value
        except TypeError:
          rdf_dict[key] = "Failed to encode: %s" % value

    result_list = list(parser.Parse(None, rdf_dict, None))
    self.assertEqual(len(result_list), 2)
    for result in result_list:
      if isinstance(result, rdf_client.Interface):
        self.assertEqual(len(result.addresses), 4)
        self.assertItemsEqual(
            [x.human_readable_address for x in result.addresses], [
                "192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
                "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
                "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"
            ])

        self.assertItemsEqual(
            [x.human_readable_address
             for x in result.dhcp_server_list], ["192.168.1.1"])

        self.assertEqual(result.dhcp_lease_expires.AsMicrosecondsSinceEpoch(),
                         1409008979123456)
        self.assertEqual(result.dhcp_lease_obtained.AsMicrosecondsSinceEpoch(),
                         1408994579123456)

      elif isinstance(result, rdf_client.DNSClientConfiguration):
        self.assertItemsEqual(result.dns_server, [
            "192.168.1.1", "192.168.255.81", "192.168.128.88"
        ])

        self.assertItemsEqual(result.dns_suffix, [
            "blah.example.com", "ad.example.com", "internal.example.com",
            "example.com"
        ])

  def testWMIActiveScriptEventConsumerParser(self):
    parser = wmi_parser.WMIActiveScriptEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    rdf_dict["CreatorSID"] = [
        1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 152, 18, 57, 8, 206, 29, 80, 44,
        70, 38, 82, 8, 244, 1, 0, 0
    ]
    rdf_dict["KillTimeout"] = 0
    rdf_dict["MachineName"] = None
    rdf_dict["MaximumQueueSize"] = None
    rdf_dict["Name"] = "SomeName"
    rdf_dict["ScriptFilename"] = None
    rdf_dict["ScriptingEngine"] = "VBScript"
    rdf_dict["ScriptText"] = r"""Dim objFS, objFile
Set objFS = CreateObject("Scripting.FileSystemObject")
Set objFile = objFS.OpenTextFile("C:\temp.log", 8, true)
objFile.WriteLine "Time: " & Now & "; Entry made by: ASEC"
objFile.WriteLine "Application closed. UserModeTime: " &
TargetEvent.TargetInstance.UserModeTime &_ "; KernelModeTime: " &
TargetEvent.TargetInstance.KernelModeTime & " [hundreds of nanoseconds]"
objFile.Close"""

    result_list = list(parser.Parse(None, rdf_dict, None))
    self.assertEqual(len(result_list), 1)
    result = result_list[0]
    self.assertEqual(result.CreatorSID,
                     "S-1-5-21-137958040-743448014-139601478-500")
    self.assertEqual(result.MaximumQueueSize, 0)
    self.assertFalse(result.ScriptFilename)

  def testWMIEventConsumerParserDoesntFailOnMalformedSIDs(self):
    parser = wmi_parser.WMIActiveScriptEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    tests = [
        [1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0],
        "(1, 2, 3)",  # Older clients (3.0.0.3) return a the SID like this
        1,
        {
            1: 2
        },
        (1, 2)
    ]

    for test in tests:
      rdf_dict["CreatorSID"] = test
      result_list = list(parser.Parse(None, rdf_dict, None))
      self.assertEqual(len(result_list), 1)

  def testWMIEventConsumerParserDoesntFailOnUnknownField(self):
    parser = wmi_parser.WMIActiveScriptEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    rdf_dict["NonexistentField"] = "Abcdef"
    rdf_dict["Name"] = "Test event consumer"
    results = list(parser.Parse(None, rdf_dict, None))
    self.assertEqual(2, len(results))
    # Anomalies yield first
    self.assertEqual(results[0].__class__, rdf_anomaly.Anomaly)
    self.assertEqual(results[1].__class__, rdf_wmi.WMIActiveScriptEventConsumer)

  def testWMIEventConsumerParser_EmptyConsumersYieldBlank(self):
    parser = wmi_parser.WMIActiveScriptEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    result_list = list(parser.Parse(None, rdf_dict, None))
    self.assertEqual(1, len(result_list))
    self.assertEqual(True, not result_list[0])

  def testWMIEventConsumerParserRaisesWhenNonEmptyDictReturnedEmpty(self):
    parser = wmi_parser.WMIActiveScriptEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    rdf_dict["NonexistentField"] = "Abcdef"
    with self.assertRaises(ValueError):
      for output in parser.Parse(None, rdf_dict, None):
        self.assertEqual(output.__class__, rdf_anomaly.Anomaly)

  def testWMICommandLineEventConsumerParser(self):
    parser = wmi_parser.WMICommandLineEventConsumerParser()
    rdf_dict = rdf_protodict.Dict()
    rdf_dict["CommandLineTemplate"] = "cscript KernCap.vbs"
    rdf_dict["CreateNewConsole"] = False
    rdf_dict["CreateNewProcessGroup"] = False
    rdf_dict["CreateSeparateWowVdm"] = False
    rdf_dict["CreateSharedWowVdm"] = False
    rdf_dict["CreatorSID"] = [
        1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 133, 116, 119, 185, 124, 13, 122,
        150, 111, 189, 41, 154, 244, 1, 0, 0
    ]
    rdf_dict["DesktopName"] = None
    rdf_dict["ExecutablePath"] = None
    rdf_dict["FillAttribute"] = None
    rdf_dict["ForceOffFeedback"] = False
    rdf_dict["ForceOnFeedback"] = False
    rdf_dict["KillTimeout"] = 0
    rdf_dict["MachineName"] = None
    rdf_dict["MaximumQueueSize"] = None
    rdf_dict["Name"] = "BVTConsumer"
    rdf_dict["Priority"] = 32
    rdf_dict["RunInteractively"] = False
    rdf_dict["ShowWindowCommand"] = None
    rdf_dict["UseDefaultErrorMode"] = False
    rdf_dict["WindowTitle"] = None
    rdf_dict["WorkingDirectory"] = "C:\\tools\\kernrate"
    rdf_dict["XCoordinate"] = None
    rdf_dict["XNumCharacters"] = None
    rdf_dict["XSize"] = None
    rdf_dict["YCoordinate"] = None
    rdf_dict["YNumCharacters"] = None
    rdf_dict["YSize"] = None

    result_list = list(parser.Parse(None, rdf_dict, None))
    self.assertEqual(len(result_list), 1)
    result = result_list[0]
    self.assertEqual(result.CreatorSID,
                     "S-1-5-21-3111613573-2524581244-2586426735-500")
    self.assertEqual(result.CommandLineTemplate, "cscript KernCap.vbs")
    self.assertEqual(result.Name, "BVTConsumer")
    self.assertEqual(result.KillTimeout, 0)
    self.assertEqual(result.FillAttribute, 0)
    self.assertEqual(result.FillAttributes, 0)
    self.assertFalse(result.ForceOffFeedback)
    self.assertFalse(result.ForceOnFeedback)


class BinarySIDToStringSIDTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(BinarySIDToStringSIDTest, self).setUp()

    self.tests = [
        ["", []],
        ["S-1", [1]],
        ["S-1-5", [1, 5, 0, 0, 0, 0, 0, 5]],
        ["S-1-5-21", [1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0]],
        # Same as before but truncated.
        [None, [1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0]],
        # Even more truncation
        [None, [1, 5, 0, 0, 0, 0, 0, 5, 21, 0]],
        # All subauthorities truncated
        ["S-1-5", [1, 5, 0, 0, 0, 0, 0, 5]],
        # 5 subauthorities
        [
            "S-1-5-21-3111613573-2524581244-2586426735-500", [
                1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 133, 116, 119, 185, 124,
                13, 122, 150, 111, 189, 41, 154, 244, 1, 0, 0
            ]
        ],
        # Last subauthority truncated
        [
            None, [
                1, 5, 0, 0, 0, 0, 0, 5, 21, 0, 0, 0, 133, 116, 119, 185, 124,
                13, 122, 150, 111, 189, 41, 154, 244
            ]
        ],
    ]

  def testConversion(self):
    for expected_value, binary in self.tests:
      binary_sid = "".join([chr(x) for x in binary])

      if expected_value is None:
        # Test is meant to raise
        self.assertRaises(ValueError, wmi_parser.BinarySIDtoStringSID,
                          binary_sid)
      else:
        self.assertEqual(
            wmi_parser.BinarySIDtoStringSID(binary_sid), expected_value)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
