#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for grr.lib.type_info."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


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

  def testTypeInfoNumberObjects(self):
    """Test the type info objects behave as expected."""
    a = type_info.Integer()
    self.assertRaises(type_info.TypeValueError, a.Validate, "1")
    self.assertRaises(type_info.TypeValueError, a.Validate, "hello")
    a.Validate(1231232)
    a.Validate(-2)

  def testTypeInfoListObjects(self):
    """Test List objects."""
    a = type_info.List(type_info.Integer())
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    self.assertRaises(type_info.TypeValueError, a.Validate, "test")
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    self.assertRaises(type_info.TypeValueError, a.Validate, ["test"])
    self.assertRaises(type_info.TypeValueError, a.Validate,
                      [rdf_paths.PathSpec()])
    a.Validate([1, 2, 3])

  def testTypeInfoListConvertsObjectsOnValidation(self):
    """Test List objects return validated objects."""

    class TypeInfoFoo(type_info.Integer):

      def Validate(self, value):
        return value * 2

    a = type_info.List(TypeInfoFoo())
    self.assertEqual(a.Validate([1, 2, 3]), [2, 4, 6])

  def testTypeInfoMultiChoiceObjects(self):
    """Test MultiChoice objects."""
    a = type_info.MultiChoice(choices=["a", "b"])
    self.assertRaises(type_info.TypeValueError, a.Validate, "a")
    self.assertRaises(type_info.TypeValueError, a.Validate, ["test"])
    self.assertRaises(type_info.TypeValueError, a.Validate, ["a", "test"])
    self.assertRaises(type_info.TypeValueError, a.Validate, ["a", "a"])
    self.assertRaises(type_info.TypeValueError, a.Validate, None)
    self.assertRaises(type_info.TypeValueError, a.Validate, [1])
    self.assertRaises(type_info.TypeValueError, a.Validate, 1)
    a.Validate(["a"])
    a.Validate(["a", "b"])

    with self.assertRaises(type_info.TypeValueError):
      type_info.MultiChoice(choices=[1, 2])

    a = type_info.MultiChoice(choices=[1, 2], validator=type_info.Integer())
    self.assertRaises(type_info.TypeValueError, a.Validate, "a")
    self.assertRaises(type_info.TypeValueError, a.Validate, ["test"])
    a.Validate([2])
    a.Validate([1, 2])

  def testStructDictType(self):
    """Test RDFStructDictType type."""
    a = type_info.RDFStructDictType(rdfclass=rdf_paths.PathSpec)
    self.assertRaises(type_info.TypeValueError, a.Validate, 2)
    self.assertRaises(type_info.TypeValueError, a.Validate, "ab")
    self.assertRaises(type_info.TypeValueError, a.Validate, [1, 2])

    # None values are left as is.
    self.assertEqual(None, a.Validate(None))

    # Check that validation raises when unknown attributes are passed.
    self.assertRaises(type_info.TypeValueError, a.Validate, dict(foo="bar"))

    v = a.Validate(dict(path="blah", pathtype="TSK"))
    self.assertIsInstance(v, rdf_paths.PathSpec)
    self.assertEqual(v.path, "blah")
    self.assertEqual(v.pathtype, "TSK")

  def testTypeDescriptorSet(self):

    type_infos = [
        type_info.String(name="output", default="analysis/{p}/{u}-{t}"),
        type_info.String(
            description="Profile to use.", name="profile", default=""),
        type_info.String(
            description="A comma separated list of plugins.",
            name="plugins",
            default=""),
    ]

    info = type_info.TypeDescriptorSet(
        type_infos[0],
        type_infos[1],
        type_infos[2],
    )

    new_info = type_info.TypeDescriptorSet(type_infos[0],)

    updated_info = new_info + type_info.TypeDescriptorSet(type_infos[1],)

    updated_info += type_info.TypeDescriptorSet(type_infos[2],)

    self.assertEqual(info.descriptor_map, updated_info.descriptor_map)
    self.assertEqual(sorted(info.descriptors), sorted(updated_info.descriptors))

    self.assertIn(type_infos[1], updated_info.descriptors)
    self.assertIn("plugins", updated_info)

    removed_info = updated_info.Remove("plugins")

    self.assertIn(type_infos[1], updated_info.descriptors)
    self.assertIn("plugins", updated_info)

    self.assertNotIn(type_infos[2], removed_info.descriptors)
    self.assertNotIn("plugins", removed_info)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
