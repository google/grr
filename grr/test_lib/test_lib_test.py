#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time

from absl.testing import absltest
from grr_response_core.lib import rdfvalue
from grr.test_lib import test_lib


class FakeTimelineTest(absltest.TestCase):

  def testRunSingleSleep(self):
    log = []

    def foo():
      while True:
        log.append("foo")
        time.sleep(10)

    thread = threading.Thread(name="foo-thread", target=foo)
    with test_lib.FakeTimeline(thread) as foo_timeline:
      log.append("start")
      foo_timeline.Run(duration=rdfvalue.DurationSeconds("5s"))
      log.append("5 seconds have passed")
      foo_timeline.Run(duration=rdfvalue.DurationSeconds("3s"))
      log.append("3 seconds have passed")
      foo_timeline.Run(duration=rdfvalue.DurationSeconds("4s"))
      log.append("4 seconds have passed")
      foo_timeline.Run(duration=rdfvalue.DurationSeconds("22s"))
      log.append("22 seconds have passed")

    self.assertEqual(log, [
        "start",
        "foo",
        "5 seconds have passed",
        "3 seconds have passed",
        "foo",
        "4 seconds have passed",
        "foo",
        "foo",
        "22 seconds have passed",
    ])

  def testRunMultiSleep(self):
    log = []

    def barz():
      while True:
        time.sleep(10)
        log.append("bar")
        time.sleep(5)
        log.append("baz")

    thread = threading.Thread(name="barz=thread", target=barz)
    with test_lib.FakeTimeline(thread) as barz_timeline:
      log.append("start")
      barz_timeline.Run(duration=rdfvalue.DurationSeconds("5s"))
      log.append("5 seconds have passed")
      barz_timeline.Run(duration=rdfvalue.DurationSeconds("7s"))
      log.append("7 seconds have passed")
      barz_timeline.Run(duration=rdfvalue.DurationSeconds("1s"))
      log.append("1 second has passed")
      barz_timeline.Run(duration=rdfvalue.DurationSeconds("3s"))
      log.append("3 seconds have passed")
      barz_timeline.Run(duration=rdfvalue.DurationSeconds("20s"))
      log.append("20 seconds have passed")

    self.assertEqual(log, [
        "start",
        "5 seconds have passed",
        "bar",
        "7 seconds have passed",
        "1 second has passed",
        "baz",
        "3 seconds have passed",
        "bar",
        "baz",
        "20 seconds have passed",
    ])

  def testRunSleepZero(self):
    log = []

    def norf():
      time.sleep(0)
      log.append("norf")
      time.sleep(0)
      log.append("norf")
      time.sleep(0)
      log.append("norf")

    thread = threading.Thread(name="norf-thread", target=norf)
    with test_lib.FakeTimeline(thread) as norf_timeline:
      log.append("start")
      norf_timeline.Run(duration=rdfvalue.DurationSeconds("0s"))
      log.append("rest")
      norf_timeline.Run(duration=rdfvalue.DurationSeconds("0s"))
      log.append("stop")

    self.assertEqual(log, [
        "start",
        "norf",
        "norf",
        "norf",
        "rest",
        "stop",
    ])

  def testRunException(self):
    log = []

    def quux():
      time.sleep(10)
      log.append("foo")
      time.sleep(10)
      raise Exception("bar")

    thread = threading.Thread(name="quux-thread", target=quux)
    with test_lib.FakeTimeline(thread) as quux_timeline:
      log.append("start")
      quux_timeline.Run(duration=rdfvalue.DurationSeconds("6s"))
      log.append("6 seconds have passed")
      quux_timeline.Run(duration=rdfvalue.DurationSeconds("5s"))
      log.append("5 seconds have passed")
      quux_timeline.Run(duration=rdfvalue.DurationSeconds("7s"))
      log.append("7 seconds have passed")

      self.assertEqual(log, [
          "start",
          "6 seconds have passed",
          "foo",
          "5 seconds have passed",
          "7 seconds have passed",
      ])

      with self.assertRaisesRegexp(Exception, "bar"):
        quux_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))

  def testNoRuns(self):
    log = []

    def thud():
      log.append("thud")

    with test_lib.FakeTimeline(
        threading.Thread(name="thud-thread", target=thud)):
      pass

    self.assertEqual(log, [])

  def testRunAfterFinish(self):
    log = []

    def moof():
      log.append("moof")

    with test_lib.FakeTimeline(
        threading.Thread(name="moof-thread", target=moof)) as moof_timeline:
      moof_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))
      moof_timeline.Run(duration=rdfvalue.DurationSeconds("20s"))
      moof_timeline.Run(duration=rdfvalue.DurationSeconds("30s"))

    self.assertEqual(log, ["moof"])

  def testRunWithoutContext(self):
    weez_timeline = test_lib.FakeTimeline(
        threading.Thread(name="weez-thread", target=lambda: None))

    with self.assertRaisesRegexp(AssertionError, "called without context"):
      weez_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))

  def testReuse(self):
    log = []

    def blargh():
      log.append("blargh")

    blargh_timeline = test_lib.FakeTimeline(
        threading.Thread(name="blargh-thread", target=blargh))
    with blargh_timeline:
      blargh_timeline.Run(duration=rdfvalue.DurationSeconds("5s"))

    self.assertEqual(log, ["blargh"])

    with self.assertRaisesRegexp(AssertionError, "cannot be reused"):
      with blargh_timeline:
        blargh_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))

  def testTimePassage(self):
    log = []

    def fhesh():
      log.append(rdfvalue.RDFDatetime.Now().Format("%Y-%m-%d"))
      time.sleep(rdfvalue.DurationSeconds("2d").seconds)
      log.append(rdfvalue.RDFDatetime.Now().Format("%Y-%m-%d"))
      time.sleep(rdfvalue.DurationSeconds("15s").seconds)
      log.append(rdfvalue.RDFDatetime.Now().Format("%Y-%m-%d %H:%M:%S"))
      time.sleep(rdfvalue.DurationSeconds("20m").seconds)
      log.append(rdfvalue.RDFDatetime.Now().Format("%Y-%m-%d %H:%M:%S"))

    fhesh_timeline = test_lib.FakeTimeline(
        thread=threading.Thread(name="fhesh-thread", target=fhesh),
        now=rdfvalue.RDFDatetime.FromHumanReadable("2077-01-01"))
    with fhesh_timeline:
      log.append("beep (0)")
      fhesh_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))
      log.append("beep (1)")
      fhesh_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))
      log.append("beep (2)")
      fhesh_timeline.Run(duration=rdfvalue.DurationSeconds("2d"))
      log.append("beep (3)")
      fhesh_timeline.Run(duration=rdfvalue.DurationSeconds("10s"))
      log.append("beep (4)")
      fhesh_timeline.Run(duration=rdfvalue.DurationSeconds("30m"))
      log.append("beep (5)")

    self.assertEqual(log, [
        "beep (0)",
        "2077-01-01",
        "beep (1)",
        "beep (2)",
        "2077-01-03",
        "2077-01-03 00:00:15",
        "beep (3)",
        "beep (4)",
        "2077-01-03 00:20:15",
        "beep (5)",
    ])


if __name__ == "__main__":
  absltest.main()
