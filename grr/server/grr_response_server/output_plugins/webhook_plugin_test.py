#!/usr/bin/env python
"""Tests for Webhook output plugin."""

import json
from unittest import mock

from absl import app
import requests

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server.output_plugins import webhook_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

KWARGS = 1


class WebhookOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests Webhook hunt output plugin."""

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)
    self.flow_id = '12345678'
    data_store.REL_DB.WriteFlowObject(
        mig_flow_objects.ToProtoFlow(
            rdf_flow_objects.Flow(
                flow_id=self.flow_id,
                client_id=self.client_id,
                flow_class_name='ClientFileFinder',
            )
        )
    )

  def _CallPlugin(self, plugin_args=None, responses=None, patcher=None):
    source_id = (
        rdf_client.ClientURN(self.client_id)
        .Add('Results')
        .RelativeName('aff4:/')
    )

    messages = []
    for response in responses:
      messages.append(
          rdf_flow_objects.FlowResult(
              client_id=self.client_id, flow_id=self.flow_id, payload=response
          )
      )

    plugin_cls = webhook_plugin.WebhookOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=source_id, args=plugin_args
    )

    if patcher is None:
      patcher = mock.patch.object(requests, 'post')

    with patcher as patched:
      plugin.ProcessResponses(plugin_state, messages)
      plugin.Flush(plugin_state)
      plugin.UpdateState(plugin_state)

    return patched

  def _ParseEvents(self, patched):
    request = patched.call_args[KWARGS]['data']
    return [json.loads(part) for part in request.split('\n\n')]

  def testPopulatesEventCorrectly(self):
    with test_lib.ConfigOverrider({
        'Webhook.url': 'http://a',
    }):
      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        mock_post = self._CallPlugin(
            plugin_args=webhook_plugin.WebhookOutputPluginArgs(
                annotations=['a', 'b', 'c']
            ),
            responses=[
                rdf_client_fs.StatEntry(
                    pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS')
                )
            ],
        )
    events = self._ParseEvents(mock_post)

    self.assertLen(events, 1)
    self.assertEqual(events[0]['host'], 'Host-0.example.com')
    self.assertEqual(events[0]['time'], 15)
    self.assertEqual(
        events[0]['event']['client']['clientUrn'], 'aff4:/C.1000000000000000'
    )
    self.assertEqual(events[0]['event']['annotations'], ['a', 'b', 'c'])
    self.assertEqual(events[0]['event']['flow']['flowId'], '12345678')
    self.assertEqual(events[0]['event']['resultType'], 'StatEntry')
    self.assertEqual(
        events[0]['event']['result'],
        {
            'pathspec': {
                'pathtype': 'OS',
                'path': '/中国',
            },
        },
    )

  def testPopulatesBatchCorrectly(self):
    with test_lib.ConfigOverrider({
        'Webhook.url': 'http://a',
    }):
      mock_post = self._CallPlugin(
          plugin_args=webhook_plugin.WebhookOutputPluginArgs(),
          responses=[
              rdf_client_fs.StatEntry(
                  pathspec=rdf_paths.PathSpec(path='/中国', pathtype='OS')
              ),
              rdf_client.Process(pid=42),
          ],
      )
    events = self._ParseEvents(mock_post)

    self.assertLen(events, 2)
    for event in events:
      self.assertEqual(event['host'], 'Host-0.example.com')
      self.assertEqual(
          event['event']['client']['clientUrn'], 'aff4:/C.1000000000000000'
      )

    self.assertEqual(events[0]['event']['resultType'], 'StatEntry')
    self.assertEqual(
        events[0]['event']['result'],
        {
            'pathspec': {
                'pathtype': 'OS',
                'path': '/中国',
            },
        },
    )

    self.assertEqual(events[1]['event']['resultType'], 'Process')
    self.assertEqual(
        events[1]['event']['result'],
        {
            'pid': 42,
        },
    )

  def testReadsConfigurationValuesCorrectly(self):
    with test_lib.ConfigOverrider({
        'Webhook.url': 'http://a',
        'Webhook.verify_https': False,
    }):
      mock_post = self._CallPlugin(
          plugin_args=webhook_plugin.WebhookOutputPluginArgs(),
          responses=[rdf_client.Process(pid=42)],
      )

    self.assertEqual(
        mock_post.call_args[KWARGS]['url'], 'http://a'
    )
    self.assertFalse(mock_post.call_args[KWARGS]['verify'])

  def testFailsWhenUrlIsNotConfigured(self):
    with test_lib.ConfigOverrider({'Webook.verify_false': False}):
      with self.assertRaisesRegex(
          webhook_plugin.WebhookConfigurationError, 'Webhook.url'
      ):
        self._CallPlugin(
            plugin_args=webhook_plugin.WebhookOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)],
        )

  def testArgsOverrideConfiguration(self):
    with test_lib.ConfigOverrider(
        {'Webhook.url': 'http://a'}
    ):
      mock_post = self._CallPlugin(
              plugin_args=webhook_plugin.WebhookOutputPluginArgs(url='http://b'),
          responses=[rdf_client.Process(pid=42)],
      )

    self.assertEqual(
        mock_post.call_args[KWARGS]['url'], 'http://b'
    )

  def testRaisesForHttpError(self):
    post = mock.MagicMock()
    post.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError()
    )

    with test_lib.ConfigOverrider({
        'Webhook.url': 'http://a',
    }):
      with self.assertRaises(requests.exceptions.HTTPError):
        self._CallPlugin(
            plugin_args=webhook_plugin.WebhookOutputPluginArgs(),
            responses=[rdf_client.Process(pid=42)],
            patcher=mock.patch.object(requests, 'post', post),
        )


def main(argv):
  test_lib.main(argv)


if __name__ == '__main__':
  app.run(main)
