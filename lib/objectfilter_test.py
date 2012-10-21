#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for grr.lib.objectfilter."""



import unittest
from grr.lib import objectfilter


attr1 = 'Backup'
attr2 = 'Archive'
hash1 = '123abc'
hash2 = '456def'
filename = 'boot.ini'


class DummyObject(object):
  def __init__(self, key, value):
    setattr(self, key, value)


class HashObject(object):
  def __init__(self, hash_value=None):
    self.value = hash_value

  @property
  def md5(self):
    return self.value


class Dll(object):
  def __init__(self, name, imported_functions=None, exported_functions=None):
    self.name = name
    self.imported_functions = imported_functions or []
    self.num_imported_functions = len(self.imported_functions)
    self.exported_functions = exported_functions or []
    self.num_exported_functions = len(self.exported_functions)


class DummyFile(object):
  non_callable_leaf = 'yoda'

  def __init__(self):
    self.non_callable = HashObject(hash1)
    self.non_callable_repeated = [DummyObject('desmond', ['brotha',
                                                          'brotha']),
                                  DummyObject('desmond', ['brotha',
                                                          'sista'])]
    self.imported_dll1 = Dll('a.dll', ['FindWindow', 'CreateFileA'])
    self.imported_dll2 = Dll('b.dll', ['RegQueryValueEx'])

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
  def size(self):
    return 10

  @property
  def deferred_values(self):
    for v in ['a', 'b']:
      yield v

  @property
  def novalues(self):
    return []

  @property
  def imported_dlls(self):
    return [self.imported_dll1, self.imported_dll2]

  def Callable(self):
    raise RuntimeError('This can not be called.')


class ObjectFilterTest(unittest.TestCase):
  def setUp(self):
    self.file = DummyFile()

  operator_tests = {
      objectfilter.Less: [
          (True, ['size', 1000]),
          (True, ['size', 11]),
          (False, ['size', 10]),
          (False, ['size', 0]),
          (False, ['size', '0']),
          (False, ['hash.md5', '0']),
          ],
      objectfilter.LessEqual: [
          (True, ['size', 1000]),
          (True, ['size', 11]),
          (True, ['size', 10]),
          (False, ['size', 9]),
          (True, ['size', '10']),
          (False, ['hash.md5', '0']),
          ],
      objectfilter.Greater: [
          (True, ['size', 1]),
          (True, ['size', 9.23]),
          (False, ['size', 10]),
          (False, ['size', 1000]),
          (True, ['size', '9']),
          (False, ['hash.md5', '0']),
          ],
      objectfilter.GreaterEqual: [
          (False, ['size', 1000]),
          (False, ['size', 11]),
          (True, ['size', 10]),
          (True, ['size', 0]),
          (True, ['size', '10']),
          (False, ['hash.md5', '0']),
          ],
      objectfilter.Contains: [
          (True, ['name', 'boot.ini']),
          (True, ['name', 'boot']),
          (False, ['name', 'meh']),
          ],
      objectfilter.NotContains: [
          (False, ['name', 'boot.ini']),
          (False, ['name', 'boot']),
          (True, ['name', 'meh']),
          ],
      objectfilter.InSet: [
          (True, ['name', 'boot.ini,autoexec.bat']),
          (True, ['name', 'boot.ini']),
          (False, ['name', 'NOPE']),
          (True, ['attributes', 'Nothing,Backup']),
          (False, ['attributes', 'Executable,Sparse']),
          ],
      objectfilter.NotInSet: [
          (False, ['name', 'boot.ini,autoexec.bat']),
          (False, ['name', 'boot.ini']),
          (True, ['name', 'NOPE']),
          ],
      objectfilter.Regexp: [
          (True, ['name', '^boot.ini$']),
          (True, ['name', 'boot.ini']),
          (False, ['name', '^$']),
          ],
      }

  def testBinaryOperators(self):
    for operator, test_data in self.operator_tests.items():
      for test_unit in test_data:
        print ('Testing %s with %s and %s' % (
            operator, test_unit[0], test_unit[1]))
        self.assertEqual(test_unit[0],
                         operator(test_unit[1]).Matches(self.file))

  def testExpandValues(self):
   # Case insensitivity
    values_lowercase = objectfilter.ExpandValues(self.file, 'size')
    values_uppercase = objectfilter.ExpandValues(self.file, 'Size')
    self.assertListEqual(list(values_lowercase), list(values_uppercase))

    # Existing, non-repeated, leaf is a value
    values = objectfilter.ExpandValues(self.file, 'size')
    self.assertListEqual(list(values), [10])

    # Existing, non-repeated, leaf is iterable
    values = objectfilter.ExpandValues(self.file, 'attributes')
    self.assertListEqual(list(values), [attr1, attr2])

    # Existing, repeated, leaf is value
    values = objectfilter.ExpandValues(self.file, 'hash.md5')
    self.assertListEqual(list(values), [hash1, hash2])

    # Existing, repeated, leaf is iterable
    values = objectfilter.ExpandValues(self.file,
                                       'non_callable_repeated.desmond')
    self.assertListEqual(list(values), ['brotha', 'brotha',
                                        'brotha', 'sista'])

    # Now with an iterator
    values = objectfilter.ExpandValues(self.file, 'deferred_values')
    self.assertListEqual(list(values), ['a', 'b'])

    # Non-existing first path
    values = objectfilter.ExpandValues(self.file, 'nonexistant')
    self.assertListEqual(list(values), [])

    # Non-existing in the middle
    values = objectfilter.ExpandValues(self.file, 'hash.mink.boo')
    self.assertListEqual(list(values), [])

    # Non-existing as a leaf
    values = objectfilter.ExpandValues(self.file, 'hash.mink')
    self.assertListEqual(list(values), [])

    # Non-callable leaf
    values = objectfilter.ExpandValues(self.file, 'non_callable_leaf')
    self.assertListEqual(list(values), [DummyFile.non_callable_leaf])

    # callable
    values = objectfilter.ExpandValues(self.file, 'Callable')
    self.assertListEqual(list(values), [])

    # leaf under a callable. Will return nothing
    values = objectfilter.ExpandValues(self.file, 'Callable.a')
    self.assertListEqual(list(values), [])

  def testGenericBinaryOperator(self):
    class TestBinaryOperator(objectfilter.GenericBinaryOperator):
      operation = lambda self, x, y: self.values.append(x)
      values = list()

    tbo = TestBinaryOperator(['whatever', 0])
    self.assertEqual(tbo.comp_value, 0)
    self.assertEqual(tbo.children[0], 'whatever')
    tbo.Matches(DummyObject('whatever', 'id'))
    tbo.Matches(DummyObject('whatever', 'id2'))
    tbo.Matches(DummyObject('whatever', 'bg'))
    tbo.Matches(DummyObject('whatever', 'bg2'))
    self.assertListEqual(tbo.values, ['id', 'id2', 'bg', 'bg2'])

  def testContext(self):
    self.assertRaises(objectfilter.InvalidNumberOfOperands,
                      objectfilter.Context, ['context'])
    self.assertRaises(objectfilter.InvalidNumberOfOperands,
                      objectfilter.Context,
                      ['context',
                       objectfilter.Is(['path', 'value']),
                       objectfilter.Is(['another_path', 'value'])
                      ])
    # "One imported_dll imports 2 functions AND one imported_dll imports
    # "One imported_dll imports 2 functions AND one imported_dll imports
    # function RegQueryValueEx"
    condition = objectfilter.AndFilter([
        objectfilter.Is(['imported_dlls.num_imported_functions', 2]),
        objectfilter.Is(['imported_dlls.imported_functions',
                         'RegQueryValueEx'])
        ])
    # Without context, it matches because both filters match separately
    self.assertEqual(True, condition.Matches(self.file))

    # "The same DLL imports 2 functions AND one of these is RegQueryValueEx"
    context = objectfilter.Context(['imported_dlls', condition])
    # With context, it doesn't match because both don't match in the same dll
    self.assertEqual(False, context.Matches(self.file))

    # "One imported_dll imports only 1 function AND one imported_dll imports
    # function RegQueryValueEx"
    condition = objectfilter.AndFilter([
        objectfilter.Is(['num_imported_functions', 1]),
        objectfilter.Is(['imported_functions', 'RegQueryValueEx'])
        ])
    # "The same DLL imports 1 function AND it's RegQueryValueEx"
    context = objectfilter.Context(['imported_dlls', condition])
    self.assertEqual(True, context.Matches(self.file))

  def testRegexpRaises(self):
    self.assertRaises(ValueError, objectfilter.Regexp,
                      ['name', 'I [dont compile'])

  def testParseFilterQuery(self):
    self.assertRaises(objectfilter.MalformedQueryError,
                      objectfilter.ParseFilterQuery,
                      "i'm not a valid expression")

  def testCompile(self):
    obj = DummyObject('something', 'Blue')
    filter_pb = objectfilter.ParseFilterQuery('something is "Blue"')
    filter_ = objectfilter.ObjectFilter(filter_proto=filter_pb).Compile()
    self.assertEqual(filter_.Matches(obj), True)
    filter_pb = objectfilter.ParseFilterQuery('something is "Red"')
    filter_ = objectfilter.ObjectFilter(filter_proto=filter_pb).Compile()
    self.assertEqual(filter_.Matches(obj), False)
    filter_pb = objectfilter.ParseFilterQuery('nothing < "3"')
    filter_ = objectfilter.ObjectFilter(filter_proto=filter_pb).Compile()
    self.assertEqual(filter_.Matches(obj), False)
    query = 'something is "Blue" AND nothing notcontains "all"'
    filter_pb = objectfilter.ParseFilterQuery(query)
    filter_ = objectfilter.ObjectFilter(filter_proto=filter_pb).Compile()
    self.assertEqual(filter_.Matches(obj), True)


if __name__ == '__main__':
  unittest.main()
