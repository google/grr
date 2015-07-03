#!/usr/bin/env python
"""Tests for the RekallResponse protobuf."""

from grr.lib.rdfvalues import rekall_types
from grr.lib.rdfvalues import test_base


class RekallResponseTest(test_base.RDFProtoTestCase):
  """Test the PathSpec implementation."""

  rdfvalue_class = rekall_types.RekallResponse

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class(plugin="foo%s" % number)
    return result

  def testCompressionOnSerialization(self):
    json_message = "hello world"
    sample = self.rdfvalue_class(plugin="test")
    sample.json_messages = json_message

    self.assertEqual(sample.json_messages, json_message)
    data = sample.SerializeToString()

    # After serialization, the json_messages field should be cleared, and the
    # compressed_json_messages should contain the data.
    self.assertFalse(sample.HasField("json_messages"))
    self.assertTrue(sample.HasField("compressed_json_messages"))
    self.assertEqual(sample.json_messages, json_message)

    # Test assignment. The new parameters should overwrite the old values.
    sample.json_messages = "goodbye world"
    self.assertEqual(sample.json_messages, "goodbye world")

    # On access we should be able to read the fields with transparent
    # decompression.
    sample2 = self.rdfvalue_class(data)
    self.assertEqual(sample2.json_messages, json_message)
