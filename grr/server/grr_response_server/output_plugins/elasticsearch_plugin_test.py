#!/usr/bin/env python
"""Tests for Elasticsearch output plugin."""

from unittest import mock

from absl import app
import requests

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util.compat import json
from grr_response_server import data_store
from grr_response_server.output_plugins import elasticsearch_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# For a mocked object's `call_args` property, the index of the kwargs dict
KWARGS = 1


class ElasticsearchOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests Elasticsearch hunt output plugin."""

  def setUp(self):
    super().setUp()

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

    plugin_cls = elasticsearch_plugin.ElasticsearchOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=source_id, args=plugin_args)

    if patcher is None:
      patcher = mock.patch.object(requests, 'post')

    with patcher as patched:
      plugin.ProcessResponses(plugin_state, messages)
      plugin.Flush(plugin_state)
      plugin.UpdateState(plugin_state)

    return patched

  def _ParseEvents(self, patched):
    request = patched.call_args[KWARGS]['data']
    # Elasticsearch bulk requests are line-deliminated pairs, where the first
    # line is the index command and the second is the actual document to index
    split_requests = []
    splitRequest = request.split('\n')
    for line in splitRequest:
        # Skip terminating newlines - which crashes json.Parse
        if not line:
            continue
        split_requests.append(json.Parse(line))
    update_pairs = []
    for i in range(0, len(split_requests), 2):
        update_pairs.append([split_requests[i], split_requests[i + 1]])

    return update_pairs

  def testPopulatesEventCorrectly(self):
    with test_lib.ConfigOverrider({
        'Elasticsearch.url': 'http://a',
        'Elasticsearch.token': 'b',
    }):
      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        mock_post = self._CallPlugin(
            plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(
                index='idx', tags=['a', 'b', 'c']),
            responses=[
                rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS'))
            ])
    bulk_pairs = self._ParseEvents(mock_post)

    self.assertLen(bulk_pairs, 1)
    event_pair = bulk_pairs[0]
    self.assertEqual(event_pair[0]['index']['_index'], 'idx')
    self.assertEqual(event_pair[1]['client']['clientUrn'],
                     'aff4:/C.1000000000000000')
    self.assertEqual(event_pair[1]['flow']['flowId'], '12345678')
    self.assertEqual(event_pair[1]['tags'], ['a', 'b', 'c'])
    self.assertEqual(event_pair[1]['resultType'], 'StatEntry')
    self.assertEqual(event_pair[1]['result'], {
        'pathspec': {
            'pathtype': 'OS',
            'path': '/中国',
        },
    })

  def testPopulatesBatchCorrectly(self):
    with test_lib.ConfigOverrider({
        'Elasticsearch.url': 'http://a',
        'Elasticsearch.token': 'b',
    }):
      mock_post = self._CallPlugin(
          plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(),
          responses=[
              rdf_client_fs.StatEntry(
                  pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS')),
              rdf_client.Process(pid=42),
          ])

    bulk_pairs = self._ParseEvents(mock_post)

    self.assertLen(bulk_pairs, 2)
    for event_pair in bulk_pairs:
      self.assertEqual(event_pair[1]['client']['clientUrn'],
                       'aff4:/C.1000000000000000')

    self.assertEqual(bulk_pairs[0][1]['resultType'], 'StatEntry')
    self.assertEqual(bulk_pairs[0][1]['result'], {
        'pathspec': {
            'pathtype': 'OS',
            'path': '/中国',
        },
    })

    self.assertEqual(bulk_pairs[1][1]['resultType'], 'Process')
    self.assertEqual(bulk_pairs[1][1]['result'], {
        'pid': 42,
    })

  def testReadsConfigurationValuesCorrectly(self):
    with test_lib.ConfigOverrider({
        'Elasticsearch.url': 'http://a',
        'Elasticsearch.token': 'b',
        'Elasticsearch.verify_https': False,
        'Elasticsearch.index': 'e'
    }):
      mock_post = self._CallPlugin(
          plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(),
          responses=[rdf_client.Process(pid=42)])

    self.assertEqual(mock_post.call_args[KWARGS]['url'], 'http://a/_bulk')
    self.assertFalse(mock_post.call_args[KWARGS]['verify'])
    self.assertEqual(mock_post.call_args[KWARGS]['headers']['Authorization'],
                     'Basic b')
    self.assertTrue(
        mock_post.call_args[KWARGS]['headers']['Content-Type'] == 'application/json' or
        mock_post.call_args[KWARGS]['headers']['Content-Type'] == 'application/x-ndjson'
    )

    bulk_pairs = self._ParseEvents(mock_post)
    self.assertEqual(bulk_pairs[0][0]['index']['_index'], 'e')

  def testFailsWhenUrlIsNotConfigured(self):
    with test_lib.ConfigOverrider({'Elasticsearch.token': 'b'}):
      with self.assertRaisesRegex(
          elasticsearch_plugin.ElasticsearchConfigurationError,
          'Elasticsearch.url'):
        self._CallPlugin(
            plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)])

  def testArgsOverrideConfiguration(self):
    with test_lib.ConfigOverrider({
        'Elasticsearch.url': 'http://a',
        'Elasticsearch.token': 'b',
        'Elasticsearch.index': 'e'
    }):
      mock_post = self._CallPlugin(
          plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(
              index='f'),
          responses=[rdf_client.Process(pid=42)])

    bulk_pairs = self._ParseEvents(mock_post)
    self.assertEqual(bulk_pairs[0][0]['index']['_index'], 'f')

  def testRaisesForHttpError(self):
    post = mock.MagicMock()
    post.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError())

    with test_lib.ConfigOverrider({
        'Elasticsearch.url': 'http://a',
        'Elasticsearch.token': 'b',
    }):
      with self.assertRaises(requests.exceptions.HTTPError):
        self._CallPlugin(
            plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)],
            patcher=mock.patch.object(requests, 'post', post))

  def testPostDataTerminatingNewline(self):
      with test_lib.ConfigOverrider({
          'Elasticsearch.url': 'http://a',
          'Elasticsearch.token': 'b',
      }):
          mock_post = self._CallPlugin(
              plugin_args=elasticsearch_plugin.ElasticsearchOutputPluginArgs(),
              responses=[rdf_client.Process(pid=42)])
      self.assertTrue(mock_post.call_args[KWARGS]['data'].endswith('\n'))

if __name__ == '__main__':
  app.run(test_lib.main)
