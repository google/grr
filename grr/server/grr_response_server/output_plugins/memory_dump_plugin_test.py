#!/usr/bin/env python
"""Tests AbstractMemoryDumpPlugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.output_plugins import memory_dump_plugin
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib

TMPFILE = rdf_paths.PathSpec.PathType.TMPFILE
POSITIONAL_ARGS = 0


class MemoryDumpOutputPlugin(memory_dump_plugin.AbstractMemoryDumpOutputPlugin):
  name = "memory_dump_output_plugin"
  description = "Test Plugin for MemoryDump Output."

  def OutputMemoryDump(self, process_dump, client_id):
    pass


class AbstractMemoryDumpPluginTest(test_lib.GRRBaseTest,
                                   hunt_test_lib.StandardHuntTestMixin):

  def setUp(self):
    super(AbstractMemoryDumpPluginTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.plugin = None
    self.plugin_state = None

  def _ProcessValuesWithPlugin(self, values, fake_time=42):
    if self.plugin is None:
      source_urn = rdfvalue.RDFURN("aff4:/foo/bar")
      plugin_cls = MemoryDumpOutputPlugin

      self.plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
          source_urn=source_urn, token=self.token)
      self.plugin.OutputMemoryDump = mock.MagicMock()

      if self.plugin_state is None:
        self.plugin_state = plugin_state

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(fake_time)):
      self.plugin.ProcessResponses(self.plugin_state, values)
      self.plugin.Flush(self.plugin_state)
      self.plugin.UpdateState(self.plugin_state)

    return self.plugin, self.plugin_state

  def testDoesNotFailForYaraProcessScanResponse(self):
    yara_dump = rdf_memory.YaraProcessScanResponse()
    message = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump)

    self._ProcessValuesWithPlugin([message])
    self.plugin.OutputMemoryDump.assert_not_called()

  def testDoesNotFailForEmptyProcessDump(self):
    yara_dump = rdf_memory.YaraProcessDumpResponse()
    message = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump)

    self._ProcessValuesWithPlugin([message])
    self.plugin.OutputMemoryDump.assert_not_called()

  def testCallsOutputMemoryDumpWithSingleBlob(self):
    yara_dump = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    m0 = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump)
    m1 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry)
    self._ProcessValuesWithPlugin([m0, m1])

    self.plugin.OutputMemoryDump.assert_called_once_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ]), self.client_id)

  def testProcessesMultipleYaraProcessDumpInformationCorrectly(self):
    yara_dump = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ]),
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry_1 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    stat_entry_2 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_fa_104.tmp", pathtype=TMPFILE))
    stat_entry_3 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="foobar_456_f0_fa.tmp", pathtype=TMPFILE))

    m0 = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump)
    m1 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_1)
    m2 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_2)
    m3 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_3)
    self._ProcessValuesWithPlugin([m0, m1, m2, m3])

    self.assertEqual(self.plugin.OutputMemoryDump.call_count, 2)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ]), self.client_id)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ]), self.client_id)

  def testProcessesMultipleYaraProcessDumpResponsesCorrectly(self):
    yara_dump_0 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ])
    ])
    yara_dump_1 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry_00 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    stat_entry_01 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_fa_104.tmp", pathtype=TMPFILE))
    stat_entry_10 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="foobar_456_f0_fa.tmp", pathtype=TMPFILE))

    m0 = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_0)
    m1 = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_1)
    m2 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_00)
    m3 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_01)
    m4 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_10)
    self._ProcessValuesWithPlugin([m0, m1, m2, m3, m4])

    self.assertEqual(self.plugin.OutputMemoryDump.call_count, 2)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ]), self.client_id)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ]), self.client_id)

  def testAwaitsStatEntriesCorrectly(self):
    yara_dump_0 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ])
    ])
    yara_dump_1 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry_00 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    stat_entry_01 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_fa_104.tmp", pathtype=TMPFILE))
    stat_entry_10 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="foobar_456_f0_fa.tmp", pathtype=TMPFILE))

    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_0)])
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_1)])
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_00)])
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_01)])
    self.assertEqual(self.plugin.OutputMemoryDump.call_count, 1)
    self.plugin.OutputMemoryDump.assert_called_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ]), self.client_id)
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_10)])
    self.assertEqual(self.plugin.OutputMemoryDump.call_count, 2)
    self.plugin.OutputMemoryDump.assert_called_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ]), self.client_id)

  def testOutputPluginPersistsStateCorrectly(self):
    yara_dump_0 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ])
    ])
    yara_dump_1 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry_00 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    stat_entry_01 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_fa_104.tmp", pathtype=TMPFILE))
    stat_entry_10 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="foobar_456_f0_fa.tmp", pathtype=TMPFILE))

    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_0)])
    self.plugin = None

    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump_1)])
    self.plugin = None

    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_00)])
    self.plugin = None
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_01)])
    self.plugin.OutputMemoryDump.assert_called_once_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
            rdf_paths.PathSpec(path="my_proc_123_fa_104.tmp", pathtype=TMPFILE)
        ]), self.client_id)
    self.plugin = None
    self._ProcessValuesWithPlugin(
        [rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry_10)])
    self.plugin.OutputMemoryDump.assert_called_once_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="foobar_456_f0_fa.tmp", pathtype=TMPFILE),
        ]), self.client_id)

  # TODO: Fix PathSpec inconsistencies on Windows and remove test.
  def testIsResilientToTemporaryPathSpecRegression(self):
    yara_dump = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(
                path="C:\\Foo\\my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/C:/Foo/my_proc_123_f0_fa.tmp",
            pathtype=TMPFILE,
            path_options=rdf_paths.PathSpec.Options.CASE_LITERAL))
    m0 = rdf_flows.GrrMessage(source=self.client_id, payload=yara_dump)
    m1 = rdf_flows.GrrMessage(source=self.client_id, payload=stat_entry)
    self._ProcessValuesWithPlugin([m0, m1])

    self.plugin.OutputMemoryDump.assert_called_once_with(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(
                path="/C:/Foo/my_proc_123_f0_fa.tmp",
                pathtype=TMPFILE,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
        ]), self.client_id)

  def testMultipleClientsWithIdenticalPathsYieldDifferentPMIs(self):
    client1 = self.SetupClient(1)
    client2 = self.SetupClient(2)

    yara_dump1 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    yara_dump2 = rdf_memory.YaraProcessDumpResponse(dumped_processes=[
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ])
    ])
    stat_entry1 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    stat_entry2 = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE))
    m0 = rdf_flows.GrrMessage(source=client1, payload=yara_dump1)
    m1 = rdf_flows.GrrMessage(source=client2, payload=yara_dump2)
    m2 = rdf_flows.GrrMessage(source=client1, payload=stat_entry1)
    m3 = rdf_flows.GrrMessage(source=client2, payload=stat_entry2)
    self._ProcessValuesWithPlugin([m0, m1, m2, m3])

    self.assertEqual(self.plugin.OutputMemoryDump.call_count, 2)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ]), client1)
    self.plugin.OutputMemoryDump.assert_any_call(
        rdf_memory.YaraProcessDumpInformation(dump_files=[
            rdf_paths.PathSpec(path="my_proc_123_f0_fa.tmp", pathtype=TMPFILE),
        ]), client2)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
