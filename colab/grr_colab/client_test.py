#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import platform
import socket
import threading
import time
from unittest import mock

from absl.testing import absltest

import grr_colab
from grr_colab import errors
from grr_colab import testing
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import artifact_pb2
from grr_response_proto import objects_pb2
from grr_response_server import artifact_registry
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import osquery_test_lib
from grr.test_lib import parser_test_lib


class ClientTest(testing.ColabE2ETest):

  FAKE_CLIENT_ID = 'C.0123456789abcdef'
  NONEXISTENT_CLIENT_ID = 'C.5555555555555555'

  def testWithId_ClientExists(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertIsNotNone(client)
    self.assertEqual(ClientTest.FAKE_CLIENT_ID, client.id)

  def testWithId_NoSuchClient(self):
    with self.assertRaises(errors.UnknownClientError) as context:
      grr_colab.Client.with_id(ClientTest.NONEXISTENT_CLIENT_ID)

    self.assertEqual(context.exception.client_id,
                     ClientTest.NONEXISTENT_CLIENT_ID)

  def testWithHostname_SingleClient(self):
    hostname = 'user.loc.group.example.com'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.knowledge_base.fqdn = hostname
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = grr_colab.Client.with_hostname(hostname)
    self.assertEqual(client.id, ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.hostname, hostname)

  def testWithHostname_MultipleClients(self):
    hostname = 'multclients.loc.group.example.com'
    client_id1 = 'C.1111111111111111'
    client_id2 = 'C.1111111111111112'

    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id2, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=client_id1)
    client.knowledge_base.fqdn = hostname
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = rdf_objects.ClientSnapshot(client_id=client_id2)
    client.knowledge_base.fqdn = hostname
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    with self.assertRaises(errors.AmbiguousHostnameError) as context:
      grr_colab.Client.with_hostname(hostname)

    self.assertEqual(context.exception.hostname, hostname)
    self.assertItemsEqual([client_id1, client_id2], context.exception.clients)

  @parser_test_lib.WithAllParsers
  def testWithHostname_NoClients(self):
    hostname = 'noclients.loc.group.example.com'

    with self.assertRaises(errors.UnknownHostnameError) as context:
      grr_colab.Client.with_hostname(hostname)

    self.assertEqual(context.exception.hostname, hostname)

  def testSearch_SingleKeyword(self):
    client_id1 = 'C.1111111111111111'
    client_id2 = 'C.1111111111111112'

    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id2, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=client_id1)
    client.startup_info.client_info.labels.append('foo')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = rdf_objects.ClientSnapshot(client_id=client_id2)
    client.startup_info.client_info.labels.append('bar')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    clients = grr_colab.Client.search(labels=['foo'])
    self.assertLen(clients, 1)
    self.assertEqual(clients[0].id, client_id1)

  def testSearch_NoResults(self):
    client_id1 = 'C.1111111111111111'
    client_id2 = 'C.1111111111111112'

    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id2, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=client_id1)
    client.startup_info.client_info.labels.append('foo')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = rdf_objects.ClientSnapshot(client_id=client_id2)
    client.startup_info.client_info.labels.append('bar')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    clients = grr_colab.Client.search(labels=['quux'])
    self.assertEmpty(clients)

  def testSearch_MultipleResults(self):
    client_id1 = 'C.1111111111111111'
    client_id2 = 'C.1111111111111112'

    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id2, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=client_id1)
    client.startup_info.client_info.labels.append('foo')
    client.startup_info.client_info.labels.append('bar')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = rdf_objects.ClientSnapshot(client_id=client_id2)
    client.startup_info.client_info.labels.append('bar')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    clients = grr_colab.Client.search(labels=['bar'])
    self.assertLen(clients, 2)
    self.assertCountEqual([_.id for _ in clients], [client_id1, client_id2])

  def testSearch_MultipleKeywords(self):
    hostname = 'multkeywords.loc.group.example.com'
    client_id1 = 'C.1111111111111111'
    client_id2 = 'C.1111111111111112'

    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(
        client_id=client_id2, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=client_id1)
    client.knowledge_base.fqdn = hostname
    client.startup_info.client_info.labels.append('foo')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    client = rdf_objects.ClientSnapshot(client_id=client_id2)
    client.knowledge_base.fqdn = hostname
    client.startup_info.client_info.labels.append('bar')
    data_store.REL_DB.WriteClientSnapshot(client)
    client_index.ClientIndex().AddClient(client)

    clients = grr_colab.Client.search(labels=['foo'], host=hostname)
    self.assertLen(clients, 1)
    self.assertEqual(clients[0].id, client_id1)

  def testId(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(ClientTest.FAKE_CLIENT_ID, client.id)

  def testHostname(self):
    hostname = 'hostname.loc.group.example.com'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.knowledge_base.fqdn = hostname
    data_store.REL_DB.WriteClientSnapshot(client)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.hostname, hostname)

  @parser_test_lib.WithAllParsers
  def testHostname_AfterInterrogate(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    client.interrogate()
    self.assertEqual(client.hostname, socket.getfqdn())

  def testIfaces(self):
    ifname = 'test_ifname'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.interfaces = [rdf_client_network.Interface(ifname=ifname)]
    data_store.REL_DB.WriteClientSnapshot(client)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertLen(client.ifaces, 1)
    self.assertEqual(client.ifaces[0].ifname, ifname)

  @parser_test_lib.WithAllParsers
  def testIfaces_AfterInterrogate(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    client.interrogate()
    self.assertNotEmpty(client.ifaces)
    self.assertNotEmpty([_ for _ in client.ifaces if _.ifname == 'lo'])

  def testKnowledgebase(self):
    fqdn = 'test-fqdn'
    system = 'test-os'
    users = ['test-user1', 'test-user2']

    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.knowledge_base.fqdn = fqdn
    client.knowledge_base.os = system
    client.knowledge_base.users = [
        rdf_client.User(username=users[0]),
        rdf_client.User(username=users[1]),
    ]
    data_store.REL_DB.WriteClientSnapshot(client)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.knowledgebase.fqdn, fqdn)
    self.assertEqual(client.knowledgebase.os, system)
    self.assertLen(list(client.knowledgebase.users), 2)
    for expected_user, actual_user in zip(users, client.knowledgebase.users):
      self.assertEqual(expected_user, actual_user.username)

  def testArch(self):
    arch = 'x42'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.arch = arch
    data_store.REL_DB.WriteClientSnapshot(client)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.arch, arch)

  @parser_test_lib.WithAllParsers
  def testArch_AfterInterrogate(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    client.interrogate()
    self.assertEqual(client.arch, platform.machine())

  def testKernel(self):
    kernel = '0.0.0'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.kernel = kernel
    data_store.REL_DB.WriteClientSnapshot(client)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.kernel, kernel)

  @parser_test_lib.WithAllParsers
  def testKernel_AfterInterrogate(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    client.interrogate()
    self.assertEqual(client.kernel, platform.release())

  def testLabels(self):
    labels = ['label1', 'label2']
    owner = 'test-user'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    data_store.REL_DB.AddClientLabels(ClientTest.FAKE_CLIENT_ID, owner, labels)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertItemsEqual(labels, client.labels)

  def testFirstSeen(self):
    first_seen = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID,
        fleetspeak_enabled=False,
        first_seen=first_seen)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.first_seen, first_seen.AsDatetime())

  def testLastSeen(self):
    last_seen = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID,
        fleetspeak_enabled=False,
        last_ping=last_seen)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    self.assertEqual(client.last_seen, last_seen.AsDatetime())

  def testRequestApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    data_store.REL_DB.WriteGRRUser('foo')

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)
    client.request_approval(reason='test', approvers=['foo'])

    approvals = data_store.REL_DB.ReadApprovalRequests(
        self.token.username, objects_pb2.ApprovalRequest.APPROVAL_TYPE_CLIENT,
        ClientTest.FAKE_CLIENT_ID)

    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].requestor_username, self.token.username)
    self.assertEqual(approvals[0].notified_users, ['foo'])
    self.assertEqual(approvals[0].reason, 'test')

  def testRequestApprovalAndWait(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    data_store.REL_DB.WriteGRRUser('foo')

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    def ProcessApproval():
      while True:
        approvals = data_store.REL_DB.ReadApprovalRequests(
            self.token.username,
            objects_pb2.ApprovalRequest.APPROVAL_TYPE_CLIENT,
            ClientTest.FAKE_CLIENT_ID)
        if not approvals:
          time.sleep(1)
          continue

        approval_id = approvals[0].approval_id
        data_store.REL_DB.GrantApproval(self.token.username, approval_id, 'foo')
        break

    thread = threading.Thread(name='ProcessApprover', target=ProcessApproval)
    thread.start()

    try:
      client.request_approval_and_wait(reason='test', approvers=['foo'])
      approvals = data_store.REL_DB.ReadApprovalRequests(
          self.token.username, objects_pb2.ApprovalRequest.APPROVAL_TYPE_CLIENT,
          ClientTest.FAKE_CLIENT_ID)
      self.assertLen(approvals, 1)

      approval = client._client.Approval(self.token.username,
                                         approvals[0].approval_id).Get()
      self.assertTrue(approval.data.is_valid)
    finally:
      thread.join()

  @parser_test_lib.WithAllParsers
  def testInterrogate(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    summary = client.interrogate()
    self.assertEqual(summary.system_info.fqdn, socket.getfqdn())

  @testing.with_approval_checks
  def testInterrogate_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      client.interrogate()

    self.assertEqual(context.exception.client_id, ClientTest.FAKE_CLIENT_ID)

  def testPs(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)
    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    ps = client.ps()
    self.assertNotEmpty(ps)

  @testing.with_approval_checks
  def testPs_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      client.ps()

    self.assertEqual(context.exception.client_id, ClientTest.FAKE_CLIENT_ID)

  def testOsquery(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    stdout = """
    [
      { "foo": "test1", "bar": "test2" },
      { "foo": "test3", "bar": "test4" }
    ]
    """
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=''):
      table = client.osquery('SELECT foo, bar FROM table;')

    self.assertLen(table.header.columns, 2)
    self.assertEqual(table.header.columns[0].name, 'foo')
    self.assertEqual(table.header.columns[1].name, 'bar')
    self.assertEqual(list(list(table.rows)[0].values), ['test1', 'test2'])
    self.assertEqual(list(list(table.rows)[1].values), ['test3', 'test4'])

  @testing.with_approval_checks
  def testOsquery_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      client.osquery('SELECT foo, bar FROM table;')

    self.assertEqual(context.exception.client_id, ClientTest.FAKE_CLIENT_ID)

  @parser_test_lib.WithAllParsers
  def testCollect(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = rdf_objects.ClientSnapshot(client_id=ClientTest.FAKE_CLIENT_ID)
    client.knowledge_base.os = 'test-os'
    data_store.REL_DB.WriteClientSnapshot(client)

    with mock.patch.object(artifact_registry, 'REGISTRY',
                           artifact_registry.ArtifactRegistry()):
      source = rdf_artifacts.ArtifactSource(
          type=artifact_pb2.ArtifactSource.COMMAND,
          attributes={
              'cmd': '/bin/echo',
              'args': ['1']
          })
      artifact = rdf_artifacts.Artifact(
          name='FakeArtifact', sources=[source], doc='fake artifact doc')
      artifact_registry.REGISTRY.RegisterArtifact(artifact)

      client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

      results = client.collect('FakeArtifact')
      self.assertNotEmpty(results)
      self.assertEqual(results[0].stdout, b'1\n')

  @testing.with_approval_checks
  def testCollect_WithoutApproval(self):
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    with self.assertRaises(errors.ApprovalMissingError) as context:
      client.collect('FakeArtifact')

    self.assertEqual(context.exception.client_id, ClientTest.FAKE_CLIENT_ID)

  def testYara(self):
    search_str = 'foobarbaz-test-with-unique-string-in-memory'
    data_store.REL_DB.WriteClientMetadata(
        client_id=ClientTest.FAKE_CLIENT_ID, fleetspeak_enabled=False)

    client = grr_colab.Client.with_id(ClientTest.FAKE_CLIENT_ID)

    signature = """
    rule Test {{
      strings:
        $test = "{}"
      condition:
        $test
    }}""".format(search_str)
    current_pid = os.getpid()
    results = client.yara(signature, pids=[current_pid])

    self.assertLen(results, 1)
    self.assertEqual(results[0].process.pid, current_pid)

    self.assertNotEmpty(results[0].match)
    matches = results[0].match[0].string_matches
    self.assertNotEmpty(matches)
    self.assertEqual(matches[0].data.decode('utf-8'), search_str)

  def testListArtifacts(self):
    artifact = rdf_artifacts.Artifact(name='FakeArtifact')

    registry_stub = artifact_registry.ArtifactRegistry()
    registry_stub.RegisterArtifact(artifact)
    data_store.REL_DB.WriteArtifact(artifact)

    with mock.patch.object(artifact_registry, 'REGISTRY', registry_stub):
      results = grr_colab.list_artifacts()

    self.assertLen(results, 1)
    self.assertEqual(results[0].artifact.name, 'FakeArtifact')


if __name__ == '__main__':
  absltest.main()
