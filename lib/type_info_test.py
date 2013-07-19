#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for grr.lib.type_info."""



from grr.artifacts import win_artifacts
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info


class TypeInfoTest(test_lib.GRRBaseTest):

  def testTypeInfoBoolObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Bool()
    self.assertRaises(type_info.TypeValueError, a.Validate, 2)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(True)
    # 1 is a valid substitute for True.
    a.Validate(1)

  def testTypeInfoStringObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.String()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate("test")
    a.Validate(u"test")
    a.Validate(u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ")

  def testTypeInfoEnumObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.SemanticEnum(rdfvalue.PathSpec.PathType)
    self.assertRaises(type_info.TypeValueError, a.Validate, 9999)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(rdfvalue.PathSpec.PathType.OS)

  def testTypeInfoNumberObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Integer()
    self.assertRaises(type_info.TypeValueError, a.Validate, "1")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(1231232)
    a.Validate(-2)

  def testTypeInfoListObjects(self):
    """Test List objects."""
    a = type_info.List(type_info.Integer())
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    self.assertRaises(type_info.TypeValueError, a.Validate, ["test"])
    self.assertRaises(type_info.TypeValueError, a.Validate, [
        rdfvalue.PathSpec()])
    a.Validate([1, 2, 3])

  def testTypeInfoArtifactObjects(self):
    """Test list List objects."""
    a = type_info.ArtifactList()
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    a.Validate(["ApplicationEventLog"])
    self.assertRaises(type_info.TypeValueError, a.Validate, ["Invalid"])
    self.assertRaises(type_info.TypeValueError, a.Validate,
                      [win_artifacts.ApplicationEventLog])

  def testTypeDescriptorSet(self):

    type_infos = [
        type_info.VolatilityRequestType(
            description="A request for the client's volatility subsystem."),

        type_info.String(
            name="output",
            default="analysis/{p}/{u}-{t}"),

        type_info.String(
            description="Profile to use.",
            name="profile",
            default=""),

        type_info.String(
            description="A comma separated list of plugins.",
            name="plugins",
            default=""),

        type_info.GenericProtoDictType(
            description="Volatility Arguments",
            name="args"),
    ]

    info = type_info.TypeDescriptorSet(
        type_infos[0],
        type_infos[1],
        type_infos[2],
        type_infos[3],
        type_infos[4],
        )

    new_info = type_info.TypeDescriptorSet(
        type_infos[0],
        type_infos[1],
        )

    updated_info = new_info + type_info.TypeDescriptorSet(
        type_infos[2],
        type_infos[3],
        )

    updated_info += type_info.TypeDescriptorSet(
        type_infos[4],
        )

    self.assertEqual(info.descriptor_map, updated_info.descriptor_map)
    self.assertEqual(sorted(info.descriptors), sorted(updated_info.descriptors))

    self.assertTrue(type_infos[3] in updated_info.descriptors)
    self.assertTrue("plugins" in updated_info)

    removed_info = updated_info.Remove("plugins")

    self.assertTrue(type_infos[3] in updated_info.descriptors)
    self.assertTrue("plugins" in updated_info)

    self.assertFalse(type_infos[3] in removed_info.descriptors)
    self.assertFalse("plugins" in removed_info)

  def testTypeFilterString(self):
    valid_query = "name is 'Bond'"
    invalid_query = "$!?%"
    a = type_info.FilterString()
    self.assertEqual(valid_query, a.Validate(valid_query))
    self.assertRaises(type_info.TypeValueError, a.Validate, invalid_query)

  def testTypeRDFURN(self):
    validator = type_info.RDFURNType()
    urn_none = rdfvalue.RDFURN(None)
    plain_str = "aff4:/something"
    urn_valid = rdfvalue.RDFURN("aff4:/users")
    no_urn = rdfvalue.RDFURN("aff4:/users")
    delattr(no_urn, "_urn")

    self.assertRaises(type_info.TypeValueError,
                      validator.Validate, urn_none)
    self.assertRaises(type_info.TypeValueError,
                      validator.Validate, plain_str)
    self.assertRaises(type_info.TypeValueError,
                      validator.Validate, no_urn)
    validator.Validate(urn_valid)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
