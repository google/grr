#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for grr.lib.objectfilter."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from absl.testing import absltest
from future.utils import iteritems

from grr_response_core.lib import objectfilter

attr1 = "Backup"
attr2 = "Archive"
hash1 = "123abc"
hash2 = "456def"
filename = "boot.ini"


class DummyObject(object):

  def __init__(self, key, value):
    setattr(self, key, value)


class HashObject(object):

  def __init__(self, hash_value=None):
    self.value = hash_value

  @property
  def md5(self):
    return self.value

  def __eq__(self, y):
    return self.value == y

  def __lt__(self, y):
    return self.value < y


class Dll(object):

  def __init__(self, name, imported_functions=None, exported_functions=None):
    self.name = name
    self._imported_functions = imported_functions or []
    self.num_imported_functions = len(self._imported_functions)
    self.exported_functions = exported_functions or []
    self.num_exported_functions = len(self.exported_functions)

  @property
  def imported_functions(self):
    for fn in self._imported_functions:
      yield fn


class DummyFile(object):
  non_callable_leaf = "yoda"

  def __init__(self):
    self.non_callable = HashObject(hash1)
    self.non_callable_repeated = [
        DummyObject("desmond", ["brotha", "brotha"]),
        DummyObject("desmond", ["brotha", "sista"])
    ]
    self.imported_dll1 = Dll("a.dll", ["FindWindow", "CreateFileA"])
    self.imported_dll2 = Dll("b.dll", ["RegQueryValueEx"])

  @property
  def name(self):
    return filename

  @property
  def attributes(self):
    return [attr1, attr2]

  @property
  def hash(self):
    return [HashObject(hash1), HashObject(hash2)]

  @property
  def mapping(self):
    return {
        "hashes": [HashObject(hash1), HashObject(hash2)],
        "nested": {
            "attrs": [attr1, attr2]
        },
        "string": "mate",
        "float": 42.0
    }

  @property
  def size(self):
    return 10

  @property
  def deferred_values(self):
    for v in ["a", "b"]:
      yield v

  @property
  def novalues(self):
    return []

  @property
  def imported_dlls(self):
    return [self.imported_dll1, self.imported_dll2]

  def Callable(self):
    raise RuntimeError("This can not be called.")

  @property
  def float(self):
    return 123.9823


class ObjectFilterTest(absltest.TestCase):

  def setUp(self):
    self.file = DummyFile()
    self.filter_imp = objectfilter.LowercaseAttributeFilterImplementation
    self.value_expander = self.filter_imp.FILTERS["ValueExpander"]

  operator_tests = {
      objectfilter.Less: [
          (True, ["size", 1000]),
          (True, ["size", 11]),
          (False, ["size", 10]),
          (False, ["size", 0]),
          (False, ["float", 1.0]),
          (True, ["float", 123.9824]),
      ],
      objectfilter.LessEqual: [
          (True, ["size", 1000]),
          (True, ["size", 11]),
          (True, ["size", 10]),
          (False, ["size", 9]),
          (False, ["float", 1.0]),
          (True, ["float", 123.9823]),
      ],
      objectfilter.Greater: [
          (True, ["size", 1]),
          (True, ["size", 9.23]),
          (False, ["size", 10]),
          (False, ["size", 1000]),
          (True, ["float", 122]),
          (True, ["float", 1.0]),
      ],
      objectfilter.GreaterEqual: [
          (False, ["size", 1000]),
          (False, ["size", 11]),
          (True, ["size", 10]),
          (True, ["size", 0]),
          # Floats work fine too
          (True, ["float", 122]),
          (True, ["float", 123.9823]),
          # Comparisons works with strings, although it might be a bit silly
          (True, ["name", "aoot.ini"]),
      ],
      objectfilter.Contains: [
          # Contains works with strings
          (True, ["name", "boot.ini"]),
          (True, ["name", "boot"]),
          (False, ["name", "meh"]),
          # Works with generators
          (True, ["imported_dlls.imported_functions", "FindWindow"]),
          # But not with numbers
          (False, ["size", 12]),
      ],
      objectfilter.NotContains: [
          (False, ["name", "boot.ini"]),
          (False, ["name", "boot"]),
          (True, ["name", "meh"]),
      ],
      objectfilter.Equals: [
          (True, ["name", "boot.ini"]),
          (False, ["name", "foobar"]),
          (True, ["float", 123.9823]),
      ],
      objectfilter.NotEquals: [
          (False, ["name", "boot.ini"]),
          (True, ["name", "foobar"]),
          (True, ["float", 25]),
      ],
      objectfilter.InSet: [
          (True, ["name", ["boot.ini", "autoexec.bat"]]),
          (True, ["name", "boot.ini"]),
          (False, ["name", "NOPE"]),
          # All values of attributes are within these
          (True, ["attributes", ["Archive", "Backup", "Nonexisting"]]),
          # Not all values of attributes are within these
          (False, ["attributes", ["Executable", "Sparse"]]),
      ],
      objectfilter.NotInSet: [
          (False, ["name", ["boot.ini", "autoexec.bat"]]),
          (False, ["name", "boot.ini"]),
          (True, ["name", "NOPE"]),
      ],
      objectfilter.Regexp: [
          (True, ["name", "^boot.ini$"]),
          (True, ["name", "boot.ini"]),
          (False, ["name", "^$"]),
          (True, ["attributes", "Archive"]),
          # One can regexp numbers if they're inclined
          (True, ["size", 0]),
          # But regexp doesn't work with lists or generators for the moment
          (False, ["imported_dlls.imported_functions", "FindWindow"])
      ],
  }

  def testBinaryOperators(self):
    for operator, test_data in iteritems(self.operator_tests):
      for test_unit in test_data:
        print("Testing %s with %s and %s" % (operator, test_unit[0],
                                             test_unit[1]))
        kwargs = {
            "arguments": test_unit[1],
            "value_expander": self.value_expander
        }
        self.assertEqual(test_unit[0], operator(**kwargs).Matches(self.file))

  def testExpand(self):
    # Case insensitivity
    values_lowercase = self.value_expander().Expand(self.file, "size")
    values_uppercase = self.value_expander().Expand(self.file, "Size")
    self.assertListEqual(list(values_lowercase), list(values_uppercase))

    # Existing, non-repeated, leaf is a value
    values = self.value_expander().Expand(self.file, "size")
    self.assertListEqual(list(values), [10])

    # Existing, non-repeated, leaf is a string in mapping
    values = self.value_expander().Expand(self.file, "mapping.string")
    self.assertListEqual(list(values), ["mate"])

    # Existing, non-repeated, leaf is a scalar in mapping
    values = self.value_expander().Expand(self.file, "mapping.float")
    self.assertListEqual(list(values), [42.0])

    # Existing, non-repeated, leaf is iterable
    values = self.value_expander().Expand(self.file, "attributes")
    self.assertListEqual(list(values), [[attr1, attr2]])

    # Existing, repeated, leaf is value
    values = self.value_expander().Expand(self.file, "hash.md5")
    self.assertListEqual(list(values), [hash1, hash2])

    # Existing, repeated, leaf is iterable
    values = self.value_expander().Expand(self.file,
                                          "non_callable_repeated.desmond")
    self.assertListEqual(
        list(values), [["brotha", "brotha"], ["brotha", "sista"]])

    # Existing, repeated, leaf is mapping.
    values = self.value_expander().Expand(self.file, "mapping.hashes")
    self.assertListEqual(list(values), [hash1, hash2])
    values = self.value_expander().Expand(self.file, "mapping.nested.attrs")
    self.assertListEqual(list(values), [[attr1, attr2]])

    # Now with an iterator
    values = self.value_expander().Expand(self.file, "deferred_values")
    self.assertListEqual([list(value) for value in values], [["a", "b"]])

    # Iterator > generator
    values = self.value_expander().Expand(self.file,
                                          "imported_dlls.imported_functions")
    expected = [["FindWindow", "CreateFileA"], ["RegQueryValueEx"]]
    self.assertListEqual([list(value) for value in values], expected)

    # Non-existing first path
    values = self.value_expander().Expand(self.file, "nonexistant")
    self.assertListEqual(list(values), [])

    # Non-existing in the middle
    values = self.value_expander().Expand(self.file, "hash.mink.boo")
    self.assertListEqual(list(values), [])

    # Non-existing as a leaf
    values = self.value_expander().Expand(self.file, "hash.mink")
    self.assertListEqual(list(values), [])

    # Non-callable leaf
    values = self.value_expander().Expand(self.file, "non_callable_leaf")
    self.assertListEqual(list(values), [DummyFile.non_callable_leaf])

    # callable
    values = self.value_expander().Expand(self.file, "Callable")
    self.assertListEqual(list(values), [])

    # leaf under a callable. Will return nothing
    values = self.value_expander().Expand(self.file, "Callable.a")
    self.assertListEqual(list(values), [])

  def testGenericBinaryOperator(self):

    class TestBinaryOperator(objectfilter.GenericBinaryOperator):
      values = list()

      def Operation(self, x, _):
        return self.values.append(x)

    # Test a common binary operator
    tbo = TestBinaryOperator(
        arguments=["whatever", 0], value_expander=self.value_expander)
    self.assertEqual(tbo.right_operand, 0)
    self.assertEqual(tbo.args[0], "whatever")
    tbo.Matches(DummyObject("whatever", "id"))
    tbo.Matches(DummyObject("whatever", "id2"))
    tbo.Matches(DummyObject("whatever", "bg"))
    tbo.Matches(DummyObject("whatever", "bg2"))
    self.assertListEqual(tbo.values, ["id", "id2", "bg", "bg2"])

  def testContext(self):
    self.assertRaises(
        objectfilter.InvalidNumberOfOperands,
        objectfilter.Context,
        arguments=["context"],
        value_expander=self.value_expander)
    self.assertRaises(
        objectfilter.InvalidNumberOfOperands,
        objectfilter.Context,
        arguments=[
            "context",
            objectfilter.Equals(
                arguments=["path", "value"],
                value_expander=self.value_expander),
            objectfilter.Equals(
                arguments=["another_path", "value"],
                value_expander=self.value_expander)
        ],
        value_expander=self.value_expander)
    # "One imported_dll imports 2 functions AND one imported_dll imports
    # function RegQueryValueEx"
    arguments = [
        objectfilter.Equals(
            ["imported_dlls.num_imported_functions", 1],
            value_expander=self.value_expander),
        objectfilter.Contains(
            ["imported_dlls.imported_functions", "RegQueryValueEx"],
            value_expander=self.value_expander)
    ]
    condition = objectfilter.AndFilter(arguments=arguments)
    # Without context, it matches because both filters match separately
    self.assertEqual(True, condition.Matches(self.file))

    arguments = [
        objectfilter.Equals(
            ["num_imported_functions", 2], value_expander=self.value_expander),
        objectfilter.Contains(
            ["imported_functions", "RegQueryValueEx"],
            value_expander=self.value_expander)
    ]
    condition = objectfilter.AndFilter(arguments=arguments)
    # "The same DLL imports 2 functions AND one of these is RegQueryValueEx"
    context = objectfilter.Context(
        arguments=["imported_dlls", condition],
        value_expander=self.value_expander)
    # With context, it doesn't match because both don't match in the same dll
    self.assertEqual(False, context.Matches(self.file))

    # "One imported_dll imports only 1 function AND one imported_dll imports
    # function RegQueryValueEx"
    condition = objectfilter.AndFilter(arguments=[
        objectfilter.Equals(
            arguments=["num_imported_functions", 1],
            value_expander=self.value_expander),
        objectfilter.Contains(
            ["imported_functions", "RegQueryValueEx"],
            value_expander=self.value_expander)
    ])
    # "The same DLL imports 1 function AND it"s RegQueryValueEx"
    context = objectfilter.Context(
        ["imported_dlls", condition], value_expander=self.value_expander)
    self.assertEqual(True, context.Matches(self.file))

    # Now test the context with a straight query
    query = """
@imported_dlls
(
  imported_functions contains "RegQueryValueEx"
  AND num_imported_functions == 1
)
"""
    filter_ = objectfilter.Parser(query).Parse()
    filter_ = filter_.Compile(self.filter_imp)
    self.assertEqual(True, filter_.Matches(self.file))

  def testRegexpRaises(self):
    self.assertRaises(
        ValueError,
        objectfilter.Regexp,
        arguments=["name", "I [dont compile"],
        value_expander=self.value_expander)

  def testEscaping(self):
    parser = objectfilter.Parser(r"a is '\n'").Parse()
    self.assertEqual(parser.args[0], "\n")
    # Invalid escape sequence
    parser = objectfilter.Parser(r"a is '\z'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Can escape the backslash
    parser = objectfilter.Parser(r"a is '\\'").Parse()
    self.assertEqual(parser.args[0], "\\")

    # HEX ESCAPING
    # This fails as it's not really a hex escaped string
    parser = objectfilter.Parser(r"a is '\xJZ'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Instead, this is what one should write
    parser = objectfilter.Parser(r"a is '\\xJZ'").Parse()
    self.assertEqual(parser.args[0], r"\xJZ")
    # Standard hex-escape
    parser = objectfilter.Parser(r"a is '\x41\x41\x41'").Parse()
    self.assertEqual(parser.args[0], "AAA")
    # Hex-escape + a character
    parser = objectfilter.Parser(r"a is '\x414'").Parse()
    self.assertEqual(parser.args[0], r"A4")
    # How to include r'\x41'
    parser = objectfilter.Parser(r"a is '\\x41'").Parse()
    self.assertEqual(parser.args[0], r"\x41")

  def testParse(self):
    # Arguments are either int, float or quoted string
    objectfilter.Parser("attribute == 1").Parse()
    objectfilter.Parser("attribute == 0x10").Parse()
    objectfilter.Parser("attribute == 0xa").Parse()
    objectfilter.Parser("attribute == 0xFF").Parse()
    parser = objectfilter.Parser("attribute == 1a")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    objectfilter.Parser("attribute == 1.2").Parse()
    objectfilter.Parser("attribute == 'bla'").Parse()
    objectfilter.Parser("attribute == \"bla\"").Parse()
    parser = objectfilter.Parser("something == red")
    self.assertRaises(objectfilter.ParseError, parser.Parse)

    # Can't start with AND
    parser = objectfilter.Parser("and something is 'Blue'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)

    # Need to close braces
    objectfilter.Parser("(a is 3)").Parse()
    parser = objectfilter.Parser("(a is 3")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Need to open braces to close them
    parser = objectfilter.Parser("a is 3)")
    self.assertRaises(objectfilter.ParseError, parser.Parse)

    # Can parse lists
    objectfilter.Parser("attribute inset [1, 2, '3', 4.01, 0xa]").Parse()
    # Need to close square braces for lists.
    parser = objectfilter.Parser("attribute inset [1, 2, '3', 4.01, 0xA")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Need to opensquare braces to close lists.
    parser = objectfilter.Parser("attribute inset 1, 2, '3', 4.01]")
    self.assertRaises(objectfilter.ParseError, parser.Parse)

    # Context Operator alone is not accepted
    parser = objectfilter.Parser("@attributes")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Accepted only with braces
    objectfilter.Parser("@attributes( name is 'adrien')").Parse()
    # Not without them
    parser = objectfilter.Parser("@attributes name is 'adrien'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Can nest context operators
    query = "@imported_dlls( @imported_function( name is 'OpenFileA'))"
    objectfilter.Parser(query).Parse()
    # Can nest context operators and mix braces without it messing up
    query = "@imported_dlls( @imported_function( name is 'OpenFileA'))"
    parser = objectfilter.Parser(query).Parse()
    query = """
@imported_dlls
(
  @imported_function
  (
    name is 'OpenFileA' and ordinal == 12
  )
)
"""
    parser = objectfilter.Parser(query).Parse()
    # Mix context and binary operators
    query = """
@imported_dlls
(
  @imported_function
  (
    name is 'OpenFileA'
  ) AND num_functions == 2
)
"""
    parser = objectfilter.Parser(query).Parse()
    # Also on the right
    query = """
@imported_dlls
(
  num_functions == 2 AND
  @imported_function
  (
    name is 'OpenFileA'
  )
)
"""

  # Altogether
  # There's an imported dll that imports OpenFileA AND
  # an imported DLL matching advapi32.dll that imports RegQueryValueExA AND
  # and it exports a symbol called 'inject'
  query = """
@imported_dlls( @imported_function ( name is 'OpenFileA' ) )
AND
@imported_dlls (
  name regexp '(?i)advapi32.dll'
  AND @imported_function ( name is 'RegQueryValueEx' )
)
AND @exported_symbols(name is 'inject')
"""

  def testInset(self):
    obj = DummyObject("clone", 2)
    parser = objectfilter.Parser("clone inset [1, 2, 3]").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), True)
    obj = DummyObject("troubleshooter", "red")
    parser = objectfilter.Parser("troubleshooter inset ['red', 'blue']").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), True)
    obj = DummyObject("troubleshooter", "infrared")
    parser = objectfilter.Parser("troubleshooter inset ['red', 'blue']").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)

  def testCompile(self):
    obj = DummyObject("something", "Blue")
    parser = objectfilter.Parser("something == 'Blue'").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), True)
    parser = objectfilter.Parser("something == 'Red'").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)
    parser = objectfilter.Parser("something == \"Red\"").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)
    obj = DummyObject("size", 4)
    parser = objectfilter.Parser("size < 3").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)
    parser = objectfilter.Parser("size == 4").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), True)
    query = "something is 'Blue' and size notcontains 3"
    parser = objectfilter.Parser(query).Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)


if __name__ == "__main__":
  absltest.main()
