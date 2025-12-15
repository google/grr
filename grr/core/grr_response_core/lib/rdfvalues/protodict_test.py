#!/usr/bin/env python
"""Test protodict implementation.

An Dict is a generic dictionary implementation which has keys of type
string, and values of varying types. The Dict can be used to serialize
and transport arbitrary python dictionaries containing a limited set of value.

Dict objects behave generally like a dict (with __getitem__, items() and
an __iter__) method, but are serializable as an RDFProto.
"""

from collections import abc

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import test_lib


class DictTest(rdf_test_base.RDFProtoTestMixin, test_lib.GRRBaseTest):
  """Test the Dict implementation."""

  rdfvalue_class = rdf_protodict.Dict

  def GenerateSample(self, number=0):
    return rdf_protodict.Dict(foo=number, bar="hello")

  def CheckRDFValue(self, value, sample):
    super().CheckRDFValue(value, sample)

    self.assertEqual(value.ToDict(), sample.ToDict())

  def CheckTestDict(self, test_dict, sample):
    for k, v in test_dict.items():
      # Test access through getitem.
      self.assertEqual(sample[k], v)

  def testEmbeddedDict(self):
    state = rdf_flow_runner.RequestState(data=rdf_protodict.Dict({"a": 1}))
    serialized = state.SerializeToBytes()
    deserialized = rdf_flow_runner.RequestState.FromSerializedBytes(serialized)
    self.assertEqual(deserialized.data, state.data)

  def testIsMapping(self):
    test_dict = rdf_protodict.Dict(a=1)
    self.assertIsInstance(test_dict, abc.Mapping)

  def testDictBehaviour(self):
    tested = rdf_protodict.Dict(a=1)

    now = rdfvalue.RDFDatetime.Now()
    tested["b"] = now

    self.assertEqual(tested["b"], now)
    self.assertEqual(tested["a"], 1)

    tested["b"] = rdfvalue.RDFURN("aff4:/users/")
    self.assertLen(tested, 2)
    self.assertEqual(tested["b"].SerializeToBytes(), b"aff4:/users")

  def testSerialization(self):
    test_dict = dict(
        key1=1,  # Integer.
        key2="foo",  # String.
        key3="\u4f60\u597d",  # Unicode.
        key5=rdfvalue.RDFDatetime.FromHumanReadable("2012/12/11"),  # RDFValue.
        key6=None,  # Support None Encoding.
        key7=rdf_structs.EnumNamedValue(5, name="Test"),  # Enums.
    )

    # Initialize through keywords.
    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through dict.
    sample = rdf_protodict.Dict(test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through a serialized form.
    serialized = sample.SerializeToBytes()
    self.assertIsInstance(serialized, bytes)

    sample = rdf_protodict.Dict.FromSerializedBytes(serialized)
    self.CheckTestDict(test_dict, sample)

    # Convert to a dict.
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDicts(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({"A": 1}),
    )

    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDictsMultipleTypes(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({"A": 1}),
        key3=[1, 2, 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]],
        key5=set([1, 2, 3]),
    )

    sample = rdf_protodict.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    to_dict = sample.ToDict()
    self.CheckTestDict(test_dict, to_dict)
    self.assertIsInstance(to_dict["key1"], dict)

  def testNestedDictsOpaqueTypes(self):

    class UnSerializable:
      pass

    test_dict = dict(
        key1={"A": 1},
        key2=rdf_protodict.Dict({"A": 1}),
        key3=[1, UnSerializable(), 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]],
        key5=UnSerializable(),
        key6=["a", UnSerializable(), "b"],
    )

    self.assertRaises(TypeError, rdf_protodict.Dict, **test_dict)

    sample = rdf_protodict.Dict()
    for key, value in test_dict.items():
      sample.SetItem(key, value, raise_on_error=False)

    # Need to do some manual checking here since this is a lossy conversion.
    self.assertEqual(test_dict["key1"], sample["key1"])
    self.assertEqual(test_dict["key2"], sample["key2"])

    self.assertEqual(1, sample["key3"][0])
    self.assertIn("Unsupported type", sample["key3"][1])
    self.assertCountEqual(test_dict["key3"][2:], sample["key3"][2:])

    self.assertEqual(test_dict["key4"], sample["key4"])
    self.assertIn("Unsupported type", sample["key5"])
    self.assertEqual("a", sample["key6"][0])
    self.assertIn("Unsupported type", sample["key6"][1])
    self.assertEqual("b", sample["key6"][2])

  def testBool(self):
    sample = rdf_protodict.Dict(a=False)
    self.assertIs(sample["a"], False)

    sample = rdf_protodict.Dict(a=True)
    self.assertIs(sample["a"], True)

    sample = rdf_protodict.Dict(sample)
    self.assertIs(sample["a"], True)

    sample = rdf_protodict.Dict(a="true")
    self.assertEqual(sample["a"], "true")

  def testLegacyRDFBoolCanBeDeserialized(self):
    kv = rdf_protodict.KeyValue()
    kv.k.data = b"t"
    kv.v.rdf_value.name = b"RDFBool"
    kv.v.rdf_value.data = b"1"

    sample = rdf_protodict.Dict()
    sample._values[b"t"] = kv

    sample = rdf_protodict.Dict.FromSerializedBytes(sample.SerializeToBytes())
    self.assertIs(sample[b"t"], True)

  def testOverwriting(self):
    req = rdf_client_action.Iterator(client_state=rdf_protodict.Dict({"A": 1}))
    # There should be one element now.
    self.assertLen(list(req.client_state.items()), 1)

    req.client_state = rdf_protodict.Dict({"B": 2})
    # Still one element.
    self.assertLen(list(req.client_state.items()), 1)

    req.client_state = rdf_protodict.Dict({})

    # And now it's gone.
    self.assertEmpty(list(req.client_state.items()))


class DictSimpleTest(absltest.TestCase):

  def testToDictSimple(self):
    dct = {
        "foo": b"bar",
        b"baz": "quux",
    }
    self.assertEqual(rdf_protodict.Dict(dct).ToDict(), dct)

  def testToDictNestedDicts(self):
    dct = {
        "foo": {
            "bar": 42,
            "baz": 1337,
        },
        "quux": {
            "norf": 3.14,
            "thud": [4, 8, 15, 16, 23, 42],
        },
    }
    self.assertEqual(rdf_protodict.Dict(dct).ToDict(), dct)

  def testToDictNestedLists(self):
    dct = {
        "foo": [
            [42],
            [1, 3, 3, 7],
        ],
        "bar": [
            {
                "quux": [4, 8, 15],
                "thud": [16, 23],
            },
            {
                "norf": [42],
            },
        ],
    }
    self.assertEqual(rdf_protodict.Dict(dct).ToDict(), dct)


class AttributedDictTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test AttributedDictFile operations."""

  rdfvalue_class = rdf_protodict.AttributedDict

  def GenerateSample(self, number=0):
    return rdf_protodict.AttributedDict({"number": number})

  def testInitialize(self):
    arnie = {"target": "Sarah Connor", "mission": "Protect"}
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = rdf_protodict.AttributedDict(arnie)
    self.assertEqual(terminator.GetItem("target"), "Sarah Connor")
    self.assertEqual(terminator.GetItem("mission"), "Protect")
    terminator = rdf_protodict.AttributedDict(t800)
    self.assertEqual(terminator.target, "Sarah Connor")
    self.assertEqual(terminator.mission, "Terminate")
    # We don't want a conflicted Terminator
    self.assertFalse(terminator.GetItem("happy_face"))

  def testAttributedDictSettingsAreAttr(self):
    t800 = {"target": "Sarah Connor", "mission": "Terminate"}
    terminator = rdf_protodict.AttributedDict(t800)
    self.assertEqual(terminator.target, "Sarah Connor")
    self.assertEqual(terminator.mission, "Terminate")


class AttributedDictSimpleTest(absltest.TestCase):

  def testInitFromStringKeyedDict(self):
    adict = rdf_protodict.AttributedDict({
        "foo": 42,
        "bar": b"quux",
        "baz": [4, 8, 15, 16, 23, 42],
    })

    self.assertEqual(adict.foo, 42)
    self.assertEqual(adict.bar, b"quux")
    self.assertEqual(adict.baz, [4, 8, 15, 16, 23, 42])

  # TODO: This behaviour should be removed once migration is done.
  def testInitFromBytestringKeyedDict(self):
    adict = rdf_protodict.AttributedDict({
        b"foo": 42,
        b"bar": b"quux",
        b"baz": [4, 8, 15, 16, 23, 42],
    })

    self.assertEqual(adict.foo, 42)
    self.assertEqual(adict.bar, b"quux")
    self.assertEqual(adict.baz, [4, 8, 15, 16, 23, 42])

  def testInitFromNonStringKeyedDictRaises(self):
    with self.assertRaises(TypeError):
      rdf_protodict.AttributedDict({
          1: "foo",
          2: "bar",
          3: "baz",
      })

  def testSetStringItem(self):
    adict = rdf_protodict.AttributedDict()
    adict["foo"] = 42
    adict["bar"] = b"quux"
    adict["baz"] = [4, 8, 15, 16, 23, 42]

    self.assertEqual(adict.foo, 42)
    self.assertEqual(adict.bar, b"quux")
    self.assertEqual(adict.baz, [4, 8, 15, 16, 23, 42])

  # TODO: This behaviour should be removed once migration is done.
  def testSetBytestringItem(self):
    adict = rdf_protodict.AttributedDict()
    adict[b"foo"] = 42
    adict[b"bar"] = b"quux"
    adict[b"baz"] = [4, 8, 15, 16, 23, 42]

    self.assertEqual(adict.foo, 42)
    self.assertEqual(adict.bar, b"quux")
    self.assertEqual(adict.baz, [4, 8, 15, 16, 23, 42])

  def testSetNonStringItemRaises(self):
    adict = rdf_protodict.AttributedDict()
    with self.assertRaises(TypeError):
      adict[42] = "foo"

  def testGetStringItem(self):
    adict = rdf_protodict.AttributedDict()
    adict.foo = 42
    adict.bar = b"quux"
    adict.baz = [4, 8, 15, 16, 23, 42]

    self.assertEqual(adict["foo"], 42)
    self.assertEqual(adict["bar"], b"quux")
    self.assertEqual(adict["baz"], [4, 8, 15, 16, 23, 42])

  # TODO: This behaviour should be removed once migration is done.
  def testGetBytestringItem(self):
    adict = rdf_protodict.AttributedDict()
    adict.foo = 42
    adict.bar = b"quux"
    adict.baz = [4, 8, 15, 16, 23, 42]

    self.assertEqual(adict[b"foo"], 42)
    self.assertEqual(adict[b"bar"], b"quux")
    self.assertEqual(adict[b"baz"], [4, 8, 15, 16, 23, 42])

  # TODO: This behaviour should be removed once migration is done.
  def testFromSerializedProtoDict(self):
    # In this test we use a non-attributed dict to force a serialization with
    # byte keys and then we deserialize it as attributed dict that should have
    # these attributes properly to unicode string keys.
    pdict = rdf_protodict.Dict()
    pdict[b"foo"] = 42
    pdict[b"bar"] = b"quux"
    pdict[b"baz"] = [4, 8, 15, 16, 23, 42]
    serialized = pdict.SerializeToBytes()

    adict = rdf_protodict.AttributedDict.FromSerializedBytes(serialized)
    self.assertEqual(adict.foo, 42)
    self.assertEqual(adict.bar, b"quux")
    self.assertEqual(adict.baz, [4, 8, 15, 16, 23, 42])

  # TODO: This behaviour should be removed once migration is done.
  def testToPrimitiveDict(self):
    # See rationale for using serialized non-attributed dict above.
    pdict = rdf_protodict.Dict()
    pdict[b"foo"] = 42
    pdict[b"bar"] = b"quux"
    pdict[b"baz"] = [4, 8, 15, 16, 23, 42]
    serialized = pdict.SerializeToBytes()

    adict = rdf_protodict.AttributedDict.FromSerializedBytes(serialized)

    dct = adict.ToDict()
    self.assertEqual(dct["foo"], 42)
    self.assertEqual(dct["bar"], b"quux")
    self.assertEqual(dct["baz"], [4, 8, 15, 16, 23, 42])

  def testNestedAssignment(self):
    adict = rdf_protodict.AttributedDict()

    adict["foo"] = {}
    adict["foo"]["bar"] = 42
    adict["foo"][b"baz"] = "Lorem ipsum."

    adict[b"quux"] = {}
    adict[b"quux"]["norf"] = [4, 8, 15, 16, 23, 42]
    adict[b"quux"][b"thud"] = 3.14

    self.assertEqual(adict.foo["bar"], 42)
    self.assertEqual(adict.foo[b"baz"], "Lorem ipsum.")
    self.assertEqual(adict.quux["norf"], [4, 8, 15, 16, 23, 42])
    self.assertEqual(adict.quux[b"thud"], 3.14)


class EmbeddedRDFValueTest(
    rdf_test_base.RDFProtoTestMixin, test_lib.GRRBaseTest
):
  rdfvalue_class = rdf_protodict.EmbeddedRDFValue

  def GenerateSample(self, number=0):
    return rdf_protodict.EmbeddedRDFValue(
        rdf_protodict.DataBlob(integer=number)
    )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
