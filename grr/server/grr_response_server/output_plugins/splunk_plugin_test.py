#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for Splunk output plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

import requests

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util.compat import json
from grr_response_server import data_store
from grr_response_server.output_plugins import splunk_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

KWARGS = 1


class SplunkOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests Splunk hunt output plugin."""

  def setUp(self):
    super(SplunkOutputPluginTest, self).setUp()

    self.client_id = self.SetupClient(0)
    self.flow_id = '12345678'
    data_store.REL_DB.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=self.flow_id,
            client_id=self.client_id,
            flow_class_name='ClientFileFinder',
            create_time=rdfvalue.RDFDatetime.Now(),
        ))

  def _CallPlugin(self, plugin_args=None, responses=None, patcher=None):
    source_id = rdf_client.ClientURN(
        self.client_id).Add('Results').RelativeName('aff4:/')

    messages = []
    for response in responses:
      messages.append(
          rdf_flows.GrrMessage(
              source=self.client_id,
              session_id='{}/{}'.format(self.client_id, self.flow_id),
              payload=response))

    plugin_cls = splunk_plugin.SplunkOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=source_id, args=plugin_args, token=self.token)

    if patcher is None:
      patcher = mock.patch.object(requests, 'post')

    with patcher as patched:
      plugin.ProcessResponses(plugin_state, messages)
      plugin.Flush(plugin_state)
      plugin.UpdateState(plugin_state)

    return patched

  def _ParseEvents(self, patched):
    request = patched.call_args[KWARGS]['data']
    return [json.Parse(part) for part in request.split('\n\n')]

  def testPopulatesEventCorrectly(self):
    with test_lib.ConfigOverrider({
        'Splunk.url': 'http://a',
        'Splunk.token': 'b',
    }):
      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        mock_post = self._CallPlugin(
            plugin_args=splunk_plugin.SplunkOutputPluginArgs(
                index='idx', annotations=['a', 'b', 'c']),
            responses=[
                rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS'))
            ])
    events = self._ParseEvents(mock_post)

    self.assertLen(events, 1)
    self.assertEqual(events[0]['host'], 'Host-0.example.com')
    self.assertEqual(events[0]['sourcetype'], 'grr_flow_result')
    self.assertEqual(events[0]['source'], 'grr')
    self.assertEqual(events[0]['time'], 15)
    self.assertEqual(events[0]['event']['client']['clientUrn'],
                     'aff4:/C.1000000000000000')
    self.assertEqual(events[0]['event']['annotations'], ['a', 'b', 'c'])
    self.assertEqual(events[0]['event']['flow']['flowId'], '12345678')
    self.assertEqual(events[0]['event']['resultType'], 'StatEntry')
    self.assertEqual(events[0]['event']['result'], {
        'pathspec': {
            'pathtype': 'OS',
            'path': '/中国',
        },
    })

  def testPopulatesBatchCorrectly(self):
    with test_lib.ConfigOverrider({
        'Splunk.url': 'http://a',
        'Splunk.token': 'b',
    }):
      mock_post = self._CallPlugin(
          plugin_args=splunk_plugin.SplunkOutputPluginArgs(),
          responses=[
              rdf_client_fs.StatEntry(
                  pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS')),
              rdf_client.Process(pid=42),
          ])
    events = self._ParseEvents(mock_post)

    self.assertLen(events, 2)
    for event in events:
      self.assertEqual(event['sourcetype'], 'grr_flow_result')
      self.assertEqual(event['source'], 'grr')
      self.assertEqual(event['host'], 'Host-0.example.com')
      self.assertEqual(event['event']['client']['clientUrn'],
                       'aff4:/C.1000000000000000')

    self.assertEqual(events[0]['event']['resultType'], 'StatEntry')
    self.assertEqual(events[0]['event']['result'], {
        'pathspec': {
            'pathtype': 'OS',
            'path': '/中国',
        },
    })

    self.assertEqual(events[1]['event']['resultType'], 'Process')
    self.assertEqual(events[1]['event']['result'], {
        'pid': 42,
    })

  def testReadsConfigurationValuesCorrectly(self):
    with test_lib.ConfigOverrider({
        'Splunk.url': 'http://a',
        'Splunk.token': 'b',
        'Splunk.verify_https': False,
        'Splunk.source': 'c',
        'Splunk.sourcetype': 'd',
        'Splunk.index': 'e'
    }):
      mock_post = self._CallPlugin(
          plugin_args=splunk_plugin.SplunkOutputPluginArgs(),
          responses=[rdf_client.Process(pid=42)])

    self.assertEqual(mock_post.call_args[KWARGS]['url'],
                     'http://a/services/collector/event')
    self.assertFalse(mock_post.call_args[KWARGS]['verify'])
    self.assertEqual(mock_post.call_args[KWARGS]['headers']['Authorization'],
                     'Splunk b')

    events = self._ParseEvents(mock_post)
    self.assertEqual(events[0]['source'], 'c')
    self.assertEqual(events[0]['sourcetype'], 'd')
    self.assertEqual(events[0]['index'], 'e')

  def testFailsWhenUrlIsNotConfigured(self):
    with test_lib.ConfigOverrider({'Splunk.token': 'b'}):
      with self.assertRaisesRegex(splunk_plugin.SplunkConfigurationError,
                                  'Splunk.url'):
        self._CallPlugin(
            plugin_args=splunk_plugin.SplunkOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)])

  def testFailsWhenTokenIsNotConfigured(self):
    with test_lib.ConfigOverrider({'Splunk.url': 'a'}):
      with self.assertRaisesRegex(splunk_plugin.SplunkConfigurationError,
                                  'Splunk.token'):
        self._CallPlugin(
            plugin_args=splunk_plugin.SplunkOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)])

  def testArgsOverrideConfiguration(self):
    with test_lib.ConfigOverrider({
        'Splunk.url': 'http://a',
        'Splunk.token': 'b',
        'Splunk.index': 'e'
    }):
      mock_post = self._CallPlugin(
          plugin_args=splunk_plugin.SplunkOutputPluginArgs(index='f'),
          responses=[rdf_client.Process(pid=42)])

    events = self._ParseEvents(mock_post)
    self.assertEqual(events[0]['index'], 'f')

  def testRaisesForHttpError(self):
    post = mock.MagicMock()
    post.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError())

    with test_lib.ConfigOverrider({
        'Splunk.url': 'http://a',
        'Splunk.token': 'b',
    }):
      with self.assertRaises(requests.exceptions.HTTPError):
        self._CallPlugin(
            plugin_args=splunk_plugin.SplunkOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)],
            patcher=mock.patch.object(requests, 'post', post))


def main(argv):
  test_lib.main(argv)


if __name__ == '__main__':
  app.run(main)
