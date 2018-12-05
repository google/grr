#!/usr/bin/env python
"""Tests for mysql_pool.py."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from builtins import range  # pylint: disable=redefined-builtin
import mock
import MySQLdb

from grr_response_core.lib import flags
from grr_response_server.databases import mysql_pool
from grr.test_lib import test_lib


class TestPool(absltest.TestCase):

  def testMaxSize(self):
    mocks = []

    def gen_mock():
      c = mock.MagicMock()
      mocks.append(c)
      return c

    proxies = []
    pool = mysql_pool.Pool(gen_mock, max_size=5)
    for _ in range(5):
      c = pool.get(blocking=False)
      self.assertIsNotNone(c)
      proxies.append(c)

    self.assertIsNone(pool.get(blocking=False))
    for p in proxies:
      p.close()

    for m in mocks:
      # Should be returned to the pool.
      m.close.assert_not_called()

    for _ in range(5):
      c = pool.get(blocking=False)
      self.assertIsNotNone(c)
      proxies.append(c)
    for p in proxies:
      p.close()
    self.assertLen(mocks, 5, 'Should have created only 5 mocks.')

  def testConnectFailure(self):

    class TestException(Exception):
      pass

    def gen_failure():
      raise TestException()

    pool = mysql_pool.Pool(gen_failure, max_size=5)
    # Repeated tries should fail, but not use up pool capacity. Try 10>5 times.
    for _ in range(10):
      with self.assertRaises(TestException):
        pool.get()

  def testBadConnection(self):

    def operational_error(*args, **kwargs):
      del args, kwargs  # Unused
      raise MySQLdb.OperationalError('Bad Cursor')

    bad_cursor_mock = mock.MagicMock()
    for m in [
        'callproc', 'execute', 'executemany', 'fetchone', 'fetchmany',
        'fetchall'
    ]:
      getattr(bad_cursor_mock, m).side_effect = operational_error

    bad_connection_mock = mock.MagicMock()
    bad_connection_mock.cursor.return_value = bad_cursor_mock

    def gen_bad():
      return bad_connection_mock

    pool = mysql_pool.Pool(gen_bad, max_size=5)

    for op in [
        lambda c: c.callproc('my_proc'), lambda c: c.
        execute('SELECT foo FROM bar'), lambda c: c.executemany(
            'INSERT INTO foo(bar) VALUES %s', ['A', 'B']), lambda c: c.fetchone(
            ), lambda c: c.fetchmany(size=5), lambda c: c.fetchall()
    ]:
      # If we can fail 10 times, then failed connections aren't consuming
      # pool capacity.
      for _ in range(10):
        con = pool.get()
        cur = con.cursor()
        with self.assertRaises(MySQLdb.OperationalError):
          op(cur)
        cur.close()
        con.close()
        # whitebox: make sure the connection didn't end up on the idle list
        self.assertFalse(pool.idle_conns)

  def testGoodConnection(self):

    good_cursor_mock = mock.MagicMock()
    for m in [
        'callproc', 'execute', 'executemany', 'fetchone', 'fetchmany',
        'fetchall'
    ]:
      getattr(good_cursor_mock, m).return_value = m

    good_connection_mock = mock.MagicMock()
    good_connection_mock.cursor.return_value = good_cursor_mock

    def gen_good():
      return good_connection_mock

    pool = mysql_pool.Pool(gen_good, max_size=5)

    for m, op in [
        ('callproc', lambda c: c.callproc('my_proc')),
        ('execute', lambda c: c.execute('SELECT foo FROM bar')),
        ('executemany',
         lambda c: c.executemany('INSERT INTO foo(bar) VALUES %s', ['A', 'B'])),
        ('fetchone', lambda c: c.fetchone()),
        ('fetchmany', lambda c: c.fetchmany(size=5)),
        ('fetchall', lambda c: c.fetchall())
    ]:
      # If we can fail 10 times, then idling a connection doesn't consume pool
      # capacity.
      for _ in range(10):
        con = pool.get()
        cur = con.cursor()
        self.assertEqual(m, op(cur))
        cur.close()
        con.close()
        # whitebox: make sure the connection did end up on the idle list
        self.assertLen(pool.idle_conns, 1)


if __name__ == '__main__':
  flags.StartMain(test_lib.main)
