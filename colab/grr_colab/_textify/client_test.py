#!/usr/bin/env python
import time
from unittest import mock

from absl.testing import absltest

from grr_colab._textify import client


class LastSeenTest(absltest.TestCase):

  def testSeconds(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 1) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.last_seen(last_seen_at), '1 seconds ago')

  def testMinutes(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 2 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.last_seen(last_seen_at), '2 minutes ago')

  def testHours(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 3 * 60 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.last_seen(last_seen_at), '3 hours ago')

  def testDays(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 4 * 60 * 60 * 24) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.last_seen(last_seen_at), '4 days ago')

  def testFuture(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs + 1) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.last_seen(last_seen_at), 'in 1 seconds')


class OnlineIconTest(absltest.TestCase):

  def testOnline(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 2 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_icon(last_seen_at), '🌕')

  def testSeen1d(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 3 * 60 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_icon(last_seen_at), '🌓')

  def testOffline(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 4 * 60 * 60 * 24) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_icon(last_seen_at), '🌑')


class OnlineStatusTest(absltest.TestCase):

  def testOnline(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 2 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_status(last_seen_at), 'online')

  def testSeen1d(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 3 * 60 * 60) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_status(last_seen_at), 'seen-1d')

  def testOffline(self):
    current_time_secs = 1560000000
    last_seen_at = (current_time_secs - 4 * 60 * 60 * 24) * (10**6)

    with mock.patch.object(time, 'time', return_value=current_time_secs):
      self.assertEqual(client.online_status(last_seen_at), 'offline')


class MacTest(absltest.TestCase):

  def testValid(self):
    mac = b'\xaa\x12\x42\xff\xa5\xd0'
    self.assertEqual(client.mac(mac), 'aa:12:42:ff:a5:d0')

  def testEmpty(self):
    self.assertEqual(client.mac(b''), '')


if __name__ == '__main__':
  absltest.main()
