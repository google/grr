#!/usr/bin/env python
"""Tests for export flows."""



import hashlib
import os
import StringIO
import subprocess
import zipfile

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class TestExportHuntResultsFilesAsZipFlow(test_lib.FlowTestsBaseclass):
  """Tests ExportHuntResultFilesAsZip flows."""

  def setUp(self):
    super(TestExportHuntResultsFilesAsZipFlow, self).setUp()

    path1 = "aff4:/C.0000000000000000/fs/os/foo/bar/hello1.txt"
    fd = aff4.FACTORY.Create(path1, "AFF4MemoryStream", token=self.token)
    fd.Write("hello1")
    fd.Set(fd.Schema.HASH,
           rdfvalue.Hash(sha256=hashlib.sha256("hello1").digest()))
    fd.Close()

    path2 = "aff4:/C.0000000000000000/fs/os/foo/bar/hello2.txt"
    fd = aff4.FACTORY.Create(path2, "AFF4MemoryStream", token=self.token)
    fd.Write("hello2")
    fd.Set(fd.Schema.HASH,
           rdfvalue.Hash(sha256=hashlib.sha256("hello2").digest()))
    fd.Close()

    self.paths = [path1, path2]

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[],
        token=self.token) as hunt:

      self.hunt_urn = hunt.urn

      with hunt.GetRunner() as runner:
        runner.Start()

        with aff4.FACTORY.Create(
            runner.context.results_collection_urn,
            aff4_type="RDFValueCollection", mode="w",
            token=self.token) as collection:

          for path in self.paths:
            collection.Add(rdfvalue.StatEntry(
                aff4path=path,
                pathspec=rdfvalue.PathSpec(
                    path="fs/os/foo/bar/" + path.split("/")[-1],
                    pathtype=rdfvalue.PathSpec.PathType.OS)))

  def _CheckEmailMessage(self, email_messages):
    self.assertEqual(len(email_messages), 1)

    for msg in email_messages:
      self.assertEqual(msg["address"], "%s@%s" % (
          self.token.username, config_lib.CONFIG.Get("Logging.domain")))
      self.assertEqual(msg["sender"],
                       "grr-noreply@%s" % config_lib.CONFIG.Get(
                           "Logging.domain"))
      self.assertTrue("ready for download" in msg["title"])
      self.assertTrue("2 of 2 files" in msg["message"])

  def SendEmailMock(self, address, sender, title, message, **_):
    self.email_messages.append(dict(address=address, sender=sender,
                                    title=title, message=message))

  def testNotifiesUserWithDownloadFileNotification(self):

    with test_lib.Stubber(email_alerts, "SendEmail", self.SendEmailMock):
      self.email_messages = []
      for _ in test_lib.TestFlowHelper(
          "ExportHuntResultFilesAsZip", None,
          hunt_urn=self.hunt_urn, token=self.token):
        pass

      self._CheckEmailMessage(self.email_messages)

    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add("test"),
                                token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)
    self.assertEqual(len(notifications), 1)
    self.assertEqual(notifications[0].type, "DownloadFile")
    self.assertEqual(notifications[0].message,
                     "Hunt results ready for download (archived 2 out "
                     "of 2 results)")

  def testCreatesZipContainingHuntResultsFilesWithoutDeduplication(self):

    with test_lib.Stubber(email_alerts, "SendEmail", self.SendEmailMock):
      self.email_messages = []

      for _ in test_lib.TestFlowHelper(
          "ExportHuntResultFilesAsZip", None,
          hunt_urn=self.hunt_urn, deduplicate=False, token=self.token):
        pass

      self._CheckEmailMessage(self.email_messages)

    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add("test"),
                                token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)
    self.assertEqual(len(notifications), 1)

    zip_fd = aff4.FACTORY.Open(notifications[0].subject, aff4_type="AFF4Stream",
                               token=self.token)
    zip_fd_contents = zip_fd.Read(len(zip_fd))

    test_zip = zipfile.ZipFile(StringIO.StringIO(zip_fd_contents), "r")
    test_zip.testzip()

    friendly_hunt_name = self.hunt_urn.Basename().replace(":", "_")
    prefix = os.path.join(friendly_hunt_name,
                          "C.0000000000000000/fs/os/foo/bar")
    self.assertEqual(sorted(test_zip.namelist()),
                     [os.path.join(prefix, "hello1.txt"),
                      os.path.join(prefix, "hello2.txt")])
    self.assertEqual(test_zip.read(os.path.join(prefix, "hello1.txt")),
                     "hello1")
    self.assertEqual(test_zip.read(os.path.join(prefix, "hello2.txt")),
                     "hello2")

  def testCreatesZipContainingDeduplicatedHuntResultsFiles(self):

    with test_lib.Stubber(email_alerts, "SendEmail", self.SendEmailMock):
      self.email_messages = []

      for _ in test_lib.TestFlowHelper(
          "ExportHuntResultFilesAsZip", None,
          hunt_urn=self.hunt_urn, deduplicate=True, token=self.token):
        pass

      self._CheckEmailMessage(self.email_messages)

    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add("test"),
                                token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)
    self.assertEqual(len(notifications), 1)

    zip_fd = aff4.FACTORY.Open(notifications[0].subject, aff4_type="AFF4Stream",
                               token=self.token)
    zip_fd_contents = zip_fd.Read(len(zip_fd))

    with utils.TempDirectory() as temp_dir:
      archive_path = os.path.join(temp_dir, "archive.zip")
      with open(archive_path, "w") as out_fd:
        out_fd.write(zip_fd_contents)

      # Builtin python ZipFile implementation doesn't support symlinks,
      # so we have to extract the files with command line tool.
      subprocess.check_call(["unzip", "-x", archive_path, "-d", temp_dir])

      friendly_hunt_name = self.hunt_urn.Basename().replace(":", "_")
      prefix = os.path.join(temp_dir, friendly_hunt_name,
                            "C.0000000000000000/fs/os/foo/bar")

      self.assertTrue(os.path.islink(os.path.join(prefix, "hello1.txt")))
      self.assertTrue(os.path.islink(os.path.join(prefix, "hello2.txt")))

      with open(os.path.join(prefix, "hello1.txt"), "r") as fd:
        self.assertEqual(fd.read(), "hello1")

      with open(os.path.join(prefix, "hello2.txt"), "r") as fd:
        self.assertEqual(fd.read(), "hello2")
