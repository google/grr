#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test protodict implementation.

An Dict is a generic dictionary implementation which has keys of type
string, and values of varying types. The Dict can be used to serialize
and transport arbitrary python dictionaries containing a limited set of value.

Dict objects behave generally like a dict (with __getitem__, items() and
an __iter__) method, but are serializable as an RDFProto.
"""


import collections

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs
from grr.lib.rdfvalues import test_base
from grr.test_lib import test_lib


class TestRDFValueArray(rdf_protodict.RDFValueArray):
  rdf_type = rdfvalue.RDFString


class DictTest(test_base.RDFProtoTestMixin, test_lib.GRRBaseTest):
  """Test the Dict implementation."""

  rdfvalue_class = rdf_protodict.Dict

  def GenerateSample(self, number=0):
    return rdf_protodict.Dict(foo=number, bar="hello")

  def CheckRDFValue(self, value, sample):
    super(DictTest, self).CheckRDFValue(value, sample)

    self.assertEqual(value.ToDict(), sample.ToDict())

  def CheckTestDict(self, test_dict, sample):
    for k, v in test_dict.items():
      # Test access through getitem.
      self.assertEqual(sample[k], v)

  def testEmbeddedDict(self):
    state = rdf_flows.RequestState(data=rdf_protodict.Dict({"a": 1}))
    serialized = state.SerializeToString()
    deserialized = rdf_flows.RequestState.FromSerializedString(serialized)
    self.assertEqual(deserialized.data, state.data)

  def testIsMapping(self):
    test_dict = rdf_protodict.Dict(a=1)
    self.assertTrue(isinstance(test_dict, collections.Mapping))

  def testDictBehaviour(self):
    tested = rdf_protodict.Dict(a=1)

    now = rdfvalue.RDFDatetime.Now()
    tested["b"] = now

    self.assertEqual(tested["b"], now)
    self.assertEqual(tested["a"], 1)

    tested["b"] = rdfvalue.RDFURN("aff4:/users/")
    self.assertEqual(len(tested), 2)
    self.assertEqual(tested["b"].SerializeToString(), "aff4:/users")

  def testSerialization(self):
    test_dict = dict(
        key1=1,  # Integer.
        key2="foo",  # String.
        key3=u"\u4f60\u597d",  # Unicode.
        key5=rdfvalue.RDFDatetime.FromHumanReadable("2012/12/11"),  # RDFValue.
        key6=None,  # Support None Encoding.
        key7=structs.EnumNamedValue(5, name="Test"),  # Enums.
    )

    # Initialize through keywords.
    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through dict.
    sample = rdf_protodict.Dict(test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through a serialized form.
    serialized = sample.SerializeToString()
    self.assertIsInstance(serialized, str)

    sample = rdf_protodict.Dict.FromSerializedString(serialized)
    self.CheckTestDict(test_dict, sample)

    # Convert to a dict.
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDicts(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({
            "A": 1
        }),
    )

    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDictsMultipleTypes(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({
            "A": 1
        }),
        key3=[1, 2, 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]],
        key5=set([1, 2, 3]))

    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    to_dict = sample.ToDict()
    self.CheckTestDict(test_dict, to_dict)
    self.assertIsInstance(to_dict["key1"], dict)

  def testNestedDictsOpaqueTypes(self):

    class UnSerializable(object):
      pass

    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({
            "A": 1
        }),
        key3=[1, UnSerializable(), 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]],
        key5=UnSerializable(),
        key6=["a", UnSerializable(), "b"])

    self.assertRaises(TypeError, rdf_protodict.Dict, **test_dict)

    sample = rdf_protodict.Dict()
    for key, value in test_dict.iteritems():
      sample.SetItem(key, value, raise_on_error=False)

    # Need to do some manual checking here since this is a lossy conversion.
    self.assertEqual(test_dict["key1"], sample["key1"])
    self.assertEqual(test_dict["key2"], sample["key2"])

    self.assertEqual(1, sample["key3"][0])
    self.assertTrue("Unsupported type" in sample["key3"][1])
    self.assertItemsEqual(test_dict["key3"][2:], sample["key3"][2:])

    self.assertEqual(test_dict["key4"], sample["key4"])
    self.assertTrue("Unsupported type" in sample["key5"])
    self.assertEqual("a", sample["key6"][0])
    self.assertTrue("Unsupported type" in sample["key6"][1])
    self.assertEqual("b", sample["key6"][2])

  def testBool(self):
    sample = rdf_protodict.Dict(a=True)
    self.assertTrue(isinstance(sample["a"], bool))
    sample = rdf_protodict.Dict(a="true")
    self.assertEqual(sample["a"], "true")

  def testOverwriting(self):
    req = rdf_client.Iterator(client_state=rdf_protodict.Dict({"A": 1}))
    # There should be one element now.
    self.assertEqual(len(list(req.client_state.items())), 1)

    req.client_state = rdf_protodict.Dict({"B": 2})
    # Still one element.
    self.assertEqual(len(list(req.client_state.items())), 1)

    req.client_state = rdf_protodict.Dict({})

    # And now it's gone.
    self.assertEqual(len(list(req.client_state.items())), 0)


class AttributedDictTest(test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test AttributedDictFile operations."""

  rdfvalue_class = rdf_protodict.AttributedDict

  def GenerateSample(self, number=0):
    return rdf_protodict.AttributedDict({"number": number})

  def testInitialize(self):
    arnie = {"target": "Sarah Connor", "mission": "Protect"}
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = rdf_protodict.AttributedDict(arnie)
    self.assertEquals(terminator.GetItem("target"), "Sarah Connor")
    self.assertEquals(terminator.GetItem("mission"), "Protect")
    terminator = rdf_protodict.AttributedDict(t800)
    self.assertEquals(terminator.target, "Sarah Connor")
    self.assertEquals(terminator.mission, "Terminate")
    # We don't want a conflicted Terminator
    self.assertFalse(terminator.GetItem("happy_face"))

  def testAttributedDictSettingsAreAttr(self):
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = rdf_protodict.AttributedDict(t800)
    self.assertEquals(terminator.target, "Sarah Connor")
    self.assertEquals(terminator.mission, "Terminate")


class RDFValueArrayTest(test_base.RDFProtoTestMixin, test_lib.GRRBaseTest):
  """Test the Dict implementation."""

  rdfvalue_class = rdf_protodict.RDFValueArray

  def GenerateSample(self, number=0):
    return rdf_protodict.RDFValueArray([number])

  def testArray(self):
    sample = rdf_protodict.RDFValueArray()

    # Add a string.
    sample.Append("hello")
    self.assertEqual(len(sample), 1)
    self.assertEqual(sample[0], "hello")

    # Add another RDFValue
    sample.Append(rdfvalue.RDFString("hello"))
    self.assertIsInstance(sample[1], rdfvalue.RDFString)

    # Test iterator.
    sample_list = list(sample)
    self.assertIsInstance(sample_list, list)
    self.assertIsInstance(sample_list[0], str)
    self.assertIsInstance(sample_list[1], rdfvalue.RDFString)

    # Test initialization from a list of variable types.
    test_list = [
        1,
        2,  # Integers.
        None,  # None.
        rdfvalue.RDFDatetime.Now(),  # An RDFValue instance.
        [1, 2],  # A nested list.
        u"升级程序",  # Unicode.
    ]
    sample = rdf_protodict.RDFValueArray(test_list)

    for x, y in zip(sample, test_list):
      self.assertEqual(x.__class__, y.__class__)
      self.assertEqual(x, y)

  def testEnforcedArray(self):
    """Check that arrays with a forced type are enforced."""
    sample = TestRDFValueArray()

    # Simple type should be coerced to an RDFString.
    sample.Append("hello")
    self.assertIsInstance(sample[0], rdfvalue.RDFString)

    # Reject appending invalid types.
    self.assertRaises(ValueError, sample.Append, rdfvalue.RDFDatetime.Now())

  def testPop(self):
    sample = TestRDFValueArray()

    # Simple type should be coerced to an RDFString.
    sample.Append("hello")
    sample.Append("world")
    sample.Append("!")

    self.assertEqual(sample.Pop(), "hello")
    self.assertEqual(sample.Pop(1), "!")
    self.assertEqual(sample.Pop(), "world")


class EmbeddedRDFValueTest(test_base.RDFProtoTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_protodict.EmbeddedRDFValue

  def GenerateSample(self, number=0):
    return rdf_protodict.EmbeddedRDFValue(rdf_protodict.RDFValueArray([number]))

  def testAgePreserved(self):
    data = rdf_protodict.RDFValueArray([1, 2, 3])
    data.age = rdfvalue.RDFDatetime.Now()
    original_age = data.age

    now = rdfvalue.RDFDatetime.Now()

    self.assertLess((now - data.age), rdfvalue.Duration("5s"))

    embedded = rdf_protodict.EmbeddedRDFValue(payload=data)
    self.assertEqual(embedded.payload.age, original_age)

    new_log = rdf_protodict.EmbeddedRDFValue(embedded).payload
    self.assertEqual(
        new_log.age, original_age, "Age not preserved: %s != %s" %
        (new_log.age.AsMicrosecondsSinceEpoch(),
         original_age.AsMicrosecondsSinceEpoch()))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
