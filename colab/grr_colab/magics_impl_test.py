#!/usr/bin/env python
import collections
import io
import ipaddress
import time
from unittest import mock

from absl.testing import absltest
import pandas as pd

import grr_colab
from grr_colab import _timeout
from grr_colab import magics_impl
from grr_response_proto import artifact_pb2
from grr_response_proto.api import client_pb2


class GrrSetNoFlowTimeoutImplTest(absltest.TestCase):

  def testNone(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 30):
      magics_impl.grr_set_no_flow_timeout_impl()
      self.assertIsNone(_timeout._FLOW_TIMEOUT)


class GrrSetDefaultFlowTimeoutImplTest(absltest.TestCase):

  def testDefault(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 10):
      magics_impl.grr_set_default_flow_timeout_impl()
      self.assertEqual(_timeout._FLOW_TIMEOUT, 30)


class GrrSetFlowTimeoutImplTest(absltest.TestCase):

  def testNoneValueError(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 30):
      with self.assertRaises(ValueError):
        magics_impl.grr_set_flow_timeout_impl(None)

  def testZero(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 30):
      magics_impl.grr_set_flow_timeout_impl(0)
      self.assertEqual(_timeout._FLOW_TIMEOUT, 0)

  def testNonZero(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 30):
      magics_impl.grr_set_flow_timeout_impl(10)
      self.assertEqual(_timeout._FLOW_TIMEOUT, 10)

  def testNegativeValueError(self):
    with mock.patch.object(_timeout, '_FLOW_TIMEOUT', 30):
      with self.assertRaises(ValueError):
        magics_impl.grr_set_flow_timeout_impl(-10)


class GrrListArtifactsImplTest(absltest.TestCase):

  def testEmptyResults(self):
    with mock.patch.object(
        grr_colab, 'list_artifacts', return_value=[]) as mock_fn:
      magics_impl.grr_list_artifacts_impl()

      mock_fn.assert_called_once_with()

  def testPriorityColumns(self):
    artifact = artifact_pb2.ArtifactDescriptor()
    artifact.artifact.name = 'foo'
    artifact.artifact.doc = 'bar'
    artifact.is_custom = True

    with mock.patch.object(
        grr_colab, 'list_artifacts', return_value=[artifact]):
      df = magics_impl.grr_list_artifacts_impl()

    self.assertEqual((1, 3), df.shape)
    self.assertEqual(
        list(df.columns), ['artifact.name', 'artifact.doc', 'is_custom'])
    self.assertEqual(df['artifact.name'][0], 'foo')
    self.assertEqual(df['artifact.doc'][0], 'bar')
    self.assertTrue(df['is_custom'][0])


class GrrSearchClientsImplTest(absltest.TestCase):

  def testNoArgs(self):
    with mock.patch.object(
        grr_colab.Client, 'search', return_value=[]) as mock_fn:
      magics_impl.grr_search_clients_impl()
      mock_fn.assert_called_once_with(
          version=None, host=None, labels=None, mac=None, ip=None, user=None)

  def testWithArgs(self):
    with mock.patch.object(
        grr_colab.Client, 'search', return_value=[]) as mock_fn:
      magics_impl.grr_search_clients_impl(
          version='test_v',
          host='test_host',
          labels=['test_label'],
          mac='test_mac',
          ip='test_ip',
          user='test_user')
      mock_fn.assert_called_once_with(
          version='test_v',
          host='test_host',
          labels=['test_label'],
          mac='test_mac',
          ip='test_ip',
          user='test_user')

  def testIsDataframe(self):
    mock_client = _MockClient()

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=[mock_client]):
      df = magics_impl.grr_search_clients_impl()
      self.assertIsInstance(df, pd.DataFrame)
      self.assertEqual(df.shape[0], 1)

  def testSortedByLastSeen(self):
    mock_clients = [
        _MockClient(client_id='foo', last_seen_at=1000),
        _MockClient(client_id='bar', last_seen_at=10),
        _MockClient(client_id='quux', last_seen_at=100),
    ]

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=mock_clients):
      df = magics_impl.grr_search_clients_impl()

    self.assertEqual(df.shape[0], 3)
    self.assertEqual(list(df['client_id']), ['foo', 'quux', 'bar'])

  def testOnlineColumns(self):
    current_time_secs = int(time.time())

    mock_clients = [
        _MockClient(last_seen_at=(current_time_secs - 2 * 60) * (10**6)),
        _MockClient(last_seen_at=(current_time_secs - 3 * 60 * 60) * (10**6)),
        _MockClient(
            last_seen_at=(current_time_secs - 4 * 60 * 60 * 24) * (10**6)),
    ]

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=mock_clients):
      df = magics_impl.grr_search_clients_impl()

    self.assertEqual(df.shape[0], 3)

    self.assertIn('online', df.columns)
    self.assertEqual(df['online'][0], 'online')
    self.assertEqual(df['online'][1], 'seen-1d')
    self.assertEqual(df['online'][2], 'offline')

    self.assertIn('online.pretty', df.columns)
    self.assertEqual(df['online.pretty'][0], '🌕')
    self.assertEqual(df['online.pretty'][1], '🌓')
    self.assertEqual(df['online.pretty'][2], '🌑')

  def testLastSeenAgoColumn(self):
    current_time_secs = 1560000000

    mock_clients = [
        _MockClient(last_seen_at=(current_time_secs + 1) * (10**6)),
        _MockClient(last_seen_at=(current_time_secs - 1) * (10**6)),
        _MockClient(last_seen_at=(current_time_secs - 2 * 60) * (10**6)),
        _MockClient(last_seen_at=(current_time_secs - 3 * 60 * 60) * (10**6)),
        _MockClient(
            last_seen_at=(current_time_secs - 4 * 60 * 60 * 24) * (10**6)),
    ]

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      with mock.patch.object(
          grr_colab.Client, 'search', return_value=mock_clients):
        df = magics_impl.grr_search_clients_impl()

    self.assertEqual(df.shape[0], 5)
    self.assertIn('last_seen_ago', df.columns)
    self.assertEqual(df['last_seen_ago'][0], 'in 1 seconds')
    self.assertEqual(df['last_seen_ago'][1], '1 seconds ago')
    self.assertEqual(df['last_seen_ago'][2], '2 minutes ago')
    self.assertEqual(df['last_seen_ago'][3], '3 hours ago')
    self.assertEqual(df['last_seen_ago'][4], '4 days ago')

  def testPriorityColumns(self):
    mock_client = _MockClient(client_id='foo')
    mock_client.set_hostname('test_hostname')
    mock_client.set_os_version('test_version')

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=[mock_client]):
      df = magics_impl.grr_search_clients_impl()

    self.assertGreaterEqual(df.shape[1], 7)
    self.assertEqual(
        list(df)[:7], [
            'online.pretty', 'online', 'client_id', 'last_seen_ago',
            'last_seen_at.pretty', 'knowledge_base.fqdn', 'os_info.version'
        ])


class GrrSearchOnlineClientsImplTest(absltest.TestCase):

  def testContainsOnlineOnly(self):
    current_time_secs = int(time.time())

    mock_clients = [
        _MockClient(
            client_id='foo',
            last_seen_at=(current_time_secs - 2 * 60) * (10**6)),
        _MockClient(
            client_id='bar',
            last_seen_at=(current_time_secs - 3 * 60 * 60) * (10**6)),
        _MockClient(
            client_id='quux',
            last_seen_at=(current_time_secs - 4 * 60 * 60 * 24) * (10**6)),
    ]

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=mock_clients):
      df = magics_impl.grr_search_online_clients_impl()

    self.assertEqual(df.shape[0], 1)
    self.assertEqual(df['client_id'][0], 'foo')
    self.assertEqual(df['online'][0], 'online')
    self.assertEqual(df['online.pretty'][0], '🌕')

  def testEmptyResults(self):
    current_time_secs = int(time.time())

    mock_clients = [
        _MockClient(last_seen_at=(current_time_secs - 3 * 60 * 60) * (10**6)),
        _MockClient(
            last_seen_at=(current_time_secs - 4 * 60 * 60 * 24) * (10**6)),
    ]

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=mock_clients):
      df = magics_impl.grr_search_online_clients_impl()

    self.assertEqual(df.shape[0], 0)

  def testSortedByLastSeen(self):
    current_time_secs = int(time.time())

    mock_clients = [
        _MockClient(
            client_id='foo', last_seen_at=(current_time_secs - 5) * (10**6)),
        _MockClient(
            client_id='bar', last_seen_at=(current_time_secs - 3) * (10**6)),
        _MockClient(
            client_id='quux', last_seen_at=(current_time_secs - 10) * (10**6)),
    ]

    with mock.patch.object(
        grr_colab.Client, 'search', return_value=mock_clients):
      df = magics_impl.grr_search_online_clients_impl()

    self.assertEqual(df.shape[0], 3)
    self.assertEqual(list(df['client_id']), ['bar', 'foo', 'quux'])


class GrrSetClientImplTest(absltest.TestCase):

  def testBothHostnameAndId(self):
    with mock.patch.object(grr_colab.Client, 'with_id') as with_id_fn:
      with mock.patch.object(grr_colab.Client,
                             'with_hostname') as with_hostname_fn:
        with mock.patch.object(magics_impl, '_state', magics_impl._State()):

          with self.assertRaises(ValueError):
            magics_impl.grr_set_client_impl('test_hostname', 'test_id')

          self.assertFalse(with_id_fn.called)
          self.assertFalse(with_hostname_fn.called)

  def testNeitherHostnameOrId(self):
    with mock.patch.object(grr_colab.Client, 'with_id') as with_id_fn:
      with mock.patch.object(grr_colab.Client,
                             'with_hostname') as with_hostname_fn:
        with mock.patch.object(magics_impl, '_state', magics_impl._State()):

          with self.assertRaises(ValueError):
            magics_impl.grr_set_client_impl()

          self.assertFalse(with_id_fn.called)
          self.assertFalse(with_hostname_fn.called)

  def testWithHostname(self):
    mock_client = _MockClient(client_id='bar')

    with mock.patch.object(grr_colab.Client, 'with_id') as with_id_fn:
      with mock.patch.object(
          grr_colab.Client, 'with_hostname',
          return_value=mock_client) as with_hostname_fn:
        with mock.patch.object(magics_impl, '_state', magics_impl._State()):

          magics_impl.grr_set_client_impl(hostname='foo')

          self.assertFalse(with_id_fn.called)
          with_hostname_fn.assert_called_once_with('foo')
          self.assertEqual(magics_impl._state.client.id, mock_client.id)

  def testWithId(self):
    mock_client = _MockClient(client_id='foo')

    with mock.patch.object(
        grr_colab.Client, 'with_id', return_value=mock_client) as with_id_fn:
      with mock.patch.object(grr_colab.Client,
                             'with_hostname') as with_hostname_fn:
        with mock.patch.object(magics_impl, '_state', magics_impl._State()):

          magics_impl.grr_set_client_impl(client='foo')

          self.assertFalse(with_hostname_fn.called)
          with_id_fn.assert_called_once_with('foo')
          self.assertEqual(magics_impl._state.client.id, mock_client.id)


class GrrRequestApprovalImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_request_approval_impl('foo', ['bar'])

  def testNoWait(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_request_approval_impl('foo', ['bar'])

      mock_client.request_approval.assert_called_once_with(
          reason='foo', approvers=['bar'])
      self.assertFalse(mock_client.request_approval_and_wait.called)

  def testWait(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_request_approval_impl('foo', ['bar'], wait=True)

      mock_client.request_approval_and_wait.assert_called_once_with(
          reason='foo', approvers=['bar'])
      self.assertFalse(mock_client.request_approval.called)


class GrrIdImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_id_impl()

  def testWithClientSet(self):
    mock_client = _MockClient(client_id='foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      client_id = magics_impl.grr_id_impl()

    self.assertEqual(client_id, 'foo')


class GrrCdImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_cd_impl('foo')

  def testRelativePath(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/foo'):
        magics_impl.grr_cd_impl('bar/quux')

        self.assertEqual(magics_impl._state.cur_dir, '/foo/bar/quux')

  def testGoBack(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/foo/bar/quux'):
        magics_impl.grr_cd_impl('../..')

        self.assertEqual(magics_impl._state.cur_dir, '/foo')

  def testAbsolutePath(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/foo'):
        magics_impl.grr_cd_impl('/bar/quux')

        self.assertEqual(magics_impl._state.cur_dir, '/bar/quux')


class GrrPwdImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_pwd_impl()

  def testRoot(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      cur_dir = magics_impl.grr_pwd_impl()

    self.assertEqual(cur_dir, '/')

  def testNonRootPath(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/foo/bar'):
        cur_dir = magics_impl.grr_pwd_impl()

    self.assertEqual(cur_dir, '/foo/bar')


class GrrLsImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_ls_impl('/foo')

  def testRelativePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('foo/bar')

        mock_client.os.ls.assert_called_once_with('/quux/foo/bar')
        self.assertFalse(mock_client.os.cached.ls.called)

  def testAbsolutePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('/foo/bar')

        mock_client.os.ls.assert_called_once_with('/foo/bar')
        self.assertFalse(mock_client.os.cached.ls.called)

  def testCurrentPath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl()

        mock_client.os.ls.assert_called_once_with('/quux')
        self.assertFalse(mock_client.os.cached.ls.called)

  def testCached(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('foo/bar', cached=True)

        mock_client.os.cached.ls.assert_called_once_with('/quux/foo/bar')
        self.assertFalse(mock_client.os.ls.called)

  def testTskPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('foo/bar', path_type=magics_impl.TSK)

        mock_client.tsk.ls.assert_called_once_with('/quux/foo/bar')

  def testNtfsPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('foo/bar', path_type=magics_impl.NTFS)

        mock_client.ntfs.ls.assert_called_once_with('/quux/foo/bar')

  def testRegistryPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_ls_impl('foo/bar', path_type=magics_impl.REGISTRY)

        mock_client.registry.ls.assert_called_once_with('/quux/foo/bar')


class GrrStatImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_stat_impl('foo')

  def testRelativePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_stat_impl('foo/bar')

        mock_client.os.glob.assert_called_once_with('/quux/foo/bar')

  def testAbsolutePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_stat_impl('/foo/bar')

        mock_client.os.glob.assert_called_once_with('/foo/bar')

  def testTskPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_stat_impl('/foo/bar', path_type=magics_impl.TSK)

      mock_client.tsk.glob.assert_called_once_with('/foo/bar')

  def testNtfsPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_stat_impl('/foo/bar', path_type=magics_impl.NTFS)

      mock_client.ntfs.glob.assert_called_once_with('/foo/bar')

  def testRegistryPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_stat_impl('/foo/bar', path_type=magics_impl.REGISTRY)

      mock_client.registry.glob.assert_called_once_with('/foo/bar')


class GrrHeadImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_head_impl('foo')

  def testRelativePath(self):
    mock_client = _MockClient()
    mock_client.os.add_file('/quux/foo/bar', b'foo bar')
    mock_client.os.cached.add_file('/quux/foo/bar', b'bar foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        data = magics_impl.grr_head_impl('foo/bar')

    self.assertEqual(data, b'foo bar')

  def testAbsolutePath(self):
    mock_client = _MockClient()
    mock_client.os.add_file('/foo/bar', b'foo bar')
    mock_client.os.cached.add_file('/foo/bar', b'bar foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        data = magics_impl.grr_head_impl('/foo/bar')

    self.assertEqual(data, b'foo bar')

  def testCached(self):
    mock_client = _MockClient()
    mock_client.os.add_file('/foo/bar', b'foo bar')
    mock_client.os.cached.add_file('/foo/bar', b'bar foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        data = magics_impl.grr_head_impl('/foo/bar', cached=True)

    self.assertEqual(data, b'bar foo')

  def testTskPathType(self):
    mock_client = _MockClient()
    mock_client.tsk.add_file('/foo/bar', b'foo bar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      data = magics_impl.grr_head_impl('/foo/bar', path_type=magics_impl.TSK)

    self.assertEqual(data, b'foo bar')

  def testNtfsPathType(self):
    mock_client = _MockClient()
    mock_client.ntfs.add_file('/foo/bar', b'foo bar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      data = magics_impl.grr_head_impl('/foo/bar', path_type=magics_impl.NTFS)

    self.assertEqual(data, b'foo bar')

  def testRegistryPathType(self):
    mock_client = _MockClient()
    mock_client.registry.add_file('/foo/bar', b'foo bar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      data = magics_impl.grr_head_impl(
          '/foo/bar', path_type=magics_impl.REGISTRY)

    self.assertEqual(data, b'foo bar')

  def testBytes(self):
    mock_client = _MockClient()
    mock_client.os.add_file('/foo/bar', b'foo bar')
    mock_client.os.cached.add_file('/foo/bar', b'bar foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        data = magics_impl.grr_head_impl('/foo/bar', bytes=3)

    self.assertEqual(data, b'foo')

  def testOffset(self):
    mock_client = _MockClient()
    mock_client.os.add_file('/foo/bar', b'foo bar')
    mock_client.os.cached.add_file('/foo/bar', b'bar foo')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/'):
        data = magics_impl.grr_head_impl('/foo/bar', bytes=3, offset=4)

    self.assertEqual(data, b'bar')


class GrrGrepImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_grep_impl('foo', 'bar')

  def testRelativePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_grep_impl('foo bar', 'foo/bar')

        mock_client.os.grep.assert_called_once_with('/quux/foo/bar', b'foo bar')

  def testAbsolutePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_grep_impl('foo bar', '/foo/bar')

        mock_client.os.grep.assert_called_once_with('/foo/bar', b'foo bar')

  def testFixedStrings(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_grep_impl('foo bar', '/foo/bar', fixed_strings=True)

        mock_client.os.fgrep.assert_called_once_with('/foo/bar', b'foo bar')
        self.assertFalse(mock_client.grep.called)

  def testTskPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_grep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.TSK)

      mock_client.tsk.grep.assert_called_once_with('/foo/bar', b'foo bar')

  def testNtfsPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_grep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.NTFS)

      mock_client.ntfs.grep.assert_called_once_with('/foo/bar', b'foo bar')

  def testRegistryPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_grep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.REGISTRY)

      mock_client.registry.grep.assert_called_once_with('/foo/bar', b'foo bar')

  def testHexString(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_grep_impl('ffac90', '/foo/bar', hex_string=True)

      mock_client.os.grep.assert_called_once_with('/foo/bar', b'\xff\xac\x90')


class GrrFgrepImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_fgrep_impl('foo', 'bar')

  def testRelativePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_fgrep_impl('foo bar', 'foo/bar')

        mock_client.os.fgrep.assert_called_once_with('/quux/foo/bar',
                                                     b'foo bar')

  def testAbsolutePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_fgrep_impl('foo bar', '/foo/bar')

        mock_client.os.fgrep.assert_called_once_with('/foo/bar', b'foo bar')

  def testTskPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_fgrep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.TSK)

      mock_client.tsk.fgrep.assert_called_once_with('/foo/bar', b'foo bar')

  def testNtfsPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_fgrep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.NTFS)

      mock_client.ntfs.fgrep.assert_called_once_with('/foo/bar', b'foo bar')

  def testRegistryPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_fgrep_impl(
          'foo bar', '/foo/bar', path_type=magics_impl.REGISTRY)

      mock_client.registry.fgrep.assert_called_once_with('/foo/bar', b'foo bar')

  def testHexString(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_fgrep_impl('ffac90', '/foo/bar', hex_string=True)

      mock_client.os.fgrep.assert_called_once_with('/foo/bar', b'\xff\xac\x90')


class GrrInterrogateImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_interrogate_impl()

  def testWithClientSet(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_interrogate_impl()

      mock_client.interrogate.assert_called_once_with()


class GrrHostnameImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_hostname_impl()

  def testWithClientSet(self):
    mock_client = _MockClient()
    mock_client.set_hostname('foobar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      hostname = magics_impl.grr_hostname_impl()

    self.assertEqual(hostname, 'foobar')


class GrrIfconfigImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_ifconfig_impl()

  def testWithClientSet(self):
    mock_client = _MockClient(ifaces=['foo', 'bar'])

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      df = magics_impl.grr_ifconfig_impl()

    self.assertEqual(df.shape, (2, 1))
    self.assertEqual(list(df['ifname']), ['foo', 'bar'])

  def testPrettyIpAddress(self):
    mock_client = _MockClient()

    ipv4 = ipaddress.IPv4Address('42.0.255.32')
    ipv6 = ipaddress.IPv6Address('2001:db8::1000')
    mock_client.add_iface('foo', [ipv4.packed, ipv6.packed])
    mock_client.add_iface('bar', [])

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      df = magics_impl.grr_ifconfig_impl()

    self.assertEqual(df.shape, (2, 2))
    self.assertEqual(list(df['ifname']), ['foo', 'bar'])
    self.assertTrue(pd.isna(df['addresses'][1]))

    addresses = df['addresses'][0]
    self.assertEqual(
        list(addresses['packed_bytes']), [ipv4.packed, ipv6.packed])
    self.assertEqual(
        list(addresses['packed_bytes.pretty']),
        [str(ipv4), str(ipv6)])

  def testPrettyMacAddress(self):
    mock_client = _MockClient()

    mock_client.add_iface('foo', mac=b'\xaa\x12\x42\xff\xa5\xd0')
    mock_client.add_iface('bar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      df = magics_impl.grr_ifconfig_impl()

    self.assertEqual(df.shape, (2, 3))
    self.assertEqual(list(df['ifname']), ['foo', 'bar'])
    self.assertTrue(pd.isna(df['mac_address'][1]))
    self.assertTrue(pd.isna(df['mac_address.pretty'][1]))
    self.assertEqual(df['mac_address'][0], b'\xaa\x12\x42\xff\xa5\xd0')
    self.assertEqual(df['mac_address.pretty'][0], 'aa:12:42:ff:a5:d0')


class GrrUnameImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_uname_impl()

  def testKernelRelease(self):
    mock_client = _MockClient(kernel='foobar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      kernel_release = magics_impl.grr_uname_impl(kernel_release=True)

    self.assertEqual(kernel_release, 'foobar')

  def testMachine(self):
    mock_client = _MockClient(arch='foobar')

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      machine = magics_impl.grr_uname_impl(machine=True)

    self.assertEqual(machine, 'foobar')

  def testNoOptionsProvided(self):
    mock_client = _MockClient()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with self.assertRaises(ValueError):
        magics_impl.grr_uname_impl()


class GrrPsImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_ps_impl()

  def testWithClientSet(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_ps_impl()

      mock_client.ps.assert_called_once_with()


class GrrOsqueryiImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_osqueryi_impl('foo bar')

  def testWithClientSet(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_osqueryi_impl('foo bar')

      mock_client.osquery.assert_called_once_with('foo bar')


class GrrCollectImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_collect_impl('FakeArtifact')

  def testWithClientSet(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_collect_impl('FakeArtifact')

      mock_client.collect.assert_called_once_with('FakeArtifact')


class GrrYaraImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_yara_impl('foo')

  def testWithClientSet(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_yara_impl('foo', [42], 'bar')

      mock_client.yara.assert_called_once_with('foo', [42], 'bar')


class GrrWgetImplTest(absltest.TestCase):

  def testNoClientSelected(self):
    with self.assertRaises(magics_impl.NoClientSelectedError):
      magics_impl.grr_wget_impl('foo')

  def testRelativePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_wget_impl('foo/bar')

        mock_client.os.wget.assert_called_once_with('/quux/foo/bar')

  def testAbsolutePath(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_wget_impl('/foo/bar')

        mock_client.os.wget.assert_called_once_with('/foo/bar')

  def testCached(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      with mock.patch.object(magics_impl._state, 'cur_dir', '/quux'):
        magics_impl.grr_wget_impl('/foo/bar', cached=True)

        mock_client.os.cached.wget.assert_called_once_with('/foo/bar')

  def testTskPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_wget_impl('/foo/bar', path_type=magics_impl.TSK)

      mock_client.tsk.wget.assert_called_once_with('/foo/bar')

  def testNtfsPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_wget_impl('/foo/bar', path_type=magics_impl.NTFS)

      mock_client.ntfs.wget.assert_called_once_with('/foo/bar')

  def testRegistryPathType(self):
    mock_client = mock.MagicMock()

    with mock.patch.object(magics_impl._state, 'client', mock_client):
      magics_impl.grr_wget_impl('/foo/bar', path_type=magics_impl.REGISTRY)

      mock_client.registry.wget.assert_called_once_with('/foo/bar')


class _MockClient(grr_colab.Client):

  class MockInnerClient(object):

    def __init__(self):
      self.data = client_pb2.ApiClient()

  class MockVFS(object):

    def __init__(self):
      self.files = collections.defaultdict(bytes)

    def open(self, path):
      data = self.files[path]
      return io.BytesIO(data)

    def add_file(self, path, data):
      self.files[path] = data

  class MockFileSystem(object):

    def __init__(self):
      self._cached = _MockClient.MockVFS()
      self.files = collections.defaultdict(bytes)

    @property
    def cached(self):
      return self._cached

    def open(self, path):
      data = self.files[path]
      return io.BytesIO(data)

    def add_file(self, path, data):
      self.files[path] = data

  def __init__(self,
               client_id='',
               last_seen_at=0,
               ifaces=None,
               kernel='',
               arch=''):
    if ifaces is None:
      ifaces = []

    self._client = _MockClient.MockInnerClient()
    self._snapshot = None
    self._os = _MockClient.MockFileSystem()
    self._tsk = _MockClient.MockFileSystem()
    self._ntfs = _MockClient.MockFileSystem()
    self._registry = _MockClient.MockFileSystem()
    self.set_id(client_id)
    self.set_last_seen_at(last_seen_at)
    self.set_ifaces(ifaces)
    self.set_kernel(kernel)
    self.set_arch(arch)

  @property
  def os(self):
    return self._os

  @property
  def tsk(self):
    return self._tsk

  @property
  def ntfs(self):
    return self._ntfs

  @property
  def registry(self):
    return self._registry

  def set_id(self, client_id):
    self._client.data.client_id = client_id
    self._client.client_id = client_id

  def set_last_seen_at(self, ms):
    self._client.data.last_seen_at = ms

  def set_hostname(self, hostname):
    self._client.data.knowledge_base.fqdn = hostname

  def set_os_version(self, os_version):
    self._client.data.os_info.version = os_version

  def set_kernel(self, kernel):
    self._client.data.os_info.kernel = kernel

  def set_arch(self, arch):
    self._client.data.os_info.machine = arch

  def set_ifaces(self, ifnames):
    for ifname in ifnames:
      self.add_iface(ifname, [])

  def add_iface(self, ifname, addresses_bytes=None, mac=None):
    if addresses_bytes is None:
      addresses_bytes = []

    iface = self._client.data.interfaces.add()
    iface.ifname = ifname

    if mac is not None:
      iface.mac_address = mac

    for packed_bytes in addresses_bytes:
      addr = iface.addresses.add()
      addr.packed_bytes = packed_bytes


if __name__ == '__main__':
  absltest.main()
