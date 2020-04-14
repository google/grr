#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""A module with test cases for the YARA database method."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestYaraMixin(object):
  """A mixin class for testing YARA methods of database implementations."""

  def testWriteYaraSignatureReferenceIncorrectUsername(self):
    blob_id = rdf_objects.BlobID(os.urandom(32))

    with self.assertRaises(db.UnknownGRRUserError) as context:
      self.db.WriteYaraSignatureReference(blob_id=blob_id, username="quux")

    self.assertEqual(context.exception.username, "quux")

  def testWriteYaraSignatureReferenceDuplicated(self):
    self.db.WriteGRRUser("foo")

    blob_id = rdf_objects.BlobID(os.urandom(32))

    # Writing duplicated signatures is possible, it should not raise.
    self.db.WriteYaraSignatureReference(blob_id=blob_id, username="foo")
    self.db.WriteYaraSignatureReference(blob_id=blob_id, username="foo")

  def testVerifyYaraSignatureReferenceSimple(self):
    self.db.WriteGRRUser("foo")

    blob_id = rdf_objects.BlobID(os.urandom(32))
    self.db.WriteYaraSignatureReference(blob_id=blob_id, username="foo")

    self.assertTrue(self.db.VerifyYaraSignatureReference(blob_id))

  def testVerifyYaraSignatureReferenceIncorrect(self):
    blob_id = rdf_objects.BlobID(os.urandom(32))

    self.assertFalse(self.db.VerifyYaraSignatureReference(blob_id))
