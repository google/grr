#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_core.lib import interpolation

vid = interpolation.VarId
sid = interpolation.ScopeId


class SubstitutionTest(absltest.TestCase):

  def testNoPlaceholdersUnicodeString(self):
    subst = interpolation.Substitution(var_config={}, scope_config={})
    self.assertEqual(subst.Substitute("foo bar baz"), "foo bar baz")

  def testNoPlaceholdersByteString(self):
    subst = interpolation.Substitution(var_config={}, scope_config={})
    self.assertEqual(subst.Substitute(b"FOOBARBAZ"), b"FOOBARBAZ")

  def testSimpleVarUnicodeString(self):
    var_config = {vid("foo"): 108}
    subst = interpolation.Substitution(var_config=var_config, scope_config={})

    self.assertEqual(subst.Substitute("%%foo%%"), "108")

  def testSimpleVarByteString(self):
    var_config = {vid("foo"): 42}
    subst = interpolation.Substitution(var_config=var_config, scope_config={})

    self.assertEqual(subst.Substitute(b"%%foo%%"), b"42")

  def testMultipleVarUnicodeString(self):
    var_config = {vid("foo"): "FOO", vid("bar"): "BAR", vid("baz"): "BAZ"}
    subst = interpolation.Substitution(var_config=var_config, scope_config={})

    self.assertEqual(subst.Substitute("%%foo%% %%bar%% %%baz%%"), "FOO BAR BAZ")

  def testMultipleVarByteString(self):
    var_config = {vid("foo"): 42, vid("bar"): "BAR", vid("baz"): 1337}
    subst = interpolation.Substitution(var_config=var_config, scope_config={})

    self.assertEqual(
        subst.Substitute(b"%%foo%% %%bar%% %%baz%%"), b"42 BAR 1337")

  def testSimpleScopeUnicodeString(self):
    scope_config = {sid("foo"): {vid("bar"): "BAR", vid("baz"): "BAZ"}}
    subst = interpolation.Substitution(var_config={}, scope_config=scope_config)

    self.assertEqual(subst.Substitute("%%foo.bar%% %%foo.baz%%"), "BAR BAZ")

  def testSimpleScopeByteString(self):
    scope_config = {sid("foo"): {vid("bar"): "BAR", vid("baz"): "BAZ"}}
    subst = interpolation.Substitution(var_config={}, scope_config=scope_config)

    self.assertEqual(subst.Substitute(b"%%foo.bar%% %%foo.baz%%"), b"BAR BAZ")

  def testMultipleScopeUnicodeString(self):
    scope_config = {
        sid("foo"): {
            vid("bar"): "BAR",
            vid("baz"): "BAZ"
        },
        sid("quux"): {
            vid("norf"): "NORF",
            vid("thud"): "THUD"
        },
    }
    subst = interpolation.Substitution(var_config={}, scope_config=scope_config)

    pattern = "%%foo.bar%% %%foo.baz%% %%quux.norf%% %%quux.thud%%"
    self.assertEqual(subst.Substitute(pattern), "BAR BAZ NORF THUD")

  def testMultipleScopeByteString(self):
    scope_config = {
        sid("foo"): {
            vid("bar"): 2,
            vid("baz"): 3
        },
        sid("quux"): {
            vid("norf"): 5,
            vid("thud"): 7
        },
    }
    subst = interpolation.Substitution(var_config={}, scope_config=scope_config)

    pattern = b"%%foo.bar%% %%foo.baz%% %%quux.norf%% %%quux.thud%%"
    self.assertEqual(subst.Substitute(pattern), b"2 3 5 7")

  def testVarAndScope(self):
    var_config = {vid("foo"): "FOO"}
    scope_config = {sid("quux"): {vid("bar"): "BAR", vid("baz"): "BAZ"}}
    subst = interpolation.Substitution(
        var_config=var_config, scope_config=scope_config)

    pattern = "%%foo%% %%quux.bar%% %%quux.baz%%"
    self.assertEqual(subst.Substitute(pattern), "FOO BAR BAZ")

  def testMultipleVariableOccurences(self):
    var_config = {vid("foo"): 42}
    subst = interpolation.Substitution(var_config=var_config, scope_config={})
    self.assertEqual(subst.Substitute("%%foo%% %%foo%% %%foo%%"), "42 42 42")

  def testInterpolationHappensSimultaneously(self):
    var_config = {vid("foo"): "%%bar%%", vid("bar"): "%%quux.norf%%"}
    scope_config = {
        sid("quux"): {
            vid("norf"): "%%foo%%",
            vid("thud"): "%%quux.norf%%"
        }
    }
    subst = interpolation.Substitution(
        var_config=var_config, scope_config=scope_config)

    pattern = "%%foo%% %%bar%% %%quux.norf%% %%quux.thud%%"
    output = "%%bar%% %%quux.norf%% %%foo%% %%quux.norf%%"
    self.assertEqual(subst.Substitute(pattern), output)


class InterpolatorTest(absltest.TestCase):

  def testListVarsUnicodeString(self):
    interpolator = interpolation.Interpolator("%%foo%% %%bar%% %%baz%% %%foo%%")
    self.assertEqual(interpolator.Vars(), {vid("foo"), vid("bar"), vid("baz")})

  def testListVarsByteString(self):
    interpolator = interpolation.Interpolator(b"%%foo%%%%bar%%%%bar%%%%baz%%")
    self.assertEqual(interpolator.Vars(), {vid("foo"), vid("bar"), vid("baz")})

  def testListScopesUnicodeString(self):
    interpolator = interpolation.Interpolator("%%foo.bar%% %%quux.norf%%")
    self.assertEqual(interpolator.Scopes(), {sid("foo"), sid("quux")})

  def testListScopeByteString(self):
    interpolator = interpolation.Interpolator(b"%%foo.bar%% %%quux.norf%%")
    self.assertEqual(interpolator.Scopes(), {sid("foo"), sid("quux")})

  def testListScopeVarsUnicodeString(self):
    interpolator = interpolation.Interpolator("%%foo.A%% %%foo.B%% %%bar.C%%")
    self.assertEqual(interpolator.ScopeVars(sid("foo")), {vid("A"), vid("B")})
    self.assertEqual(interpolator.ScopeVars(sid("bar")), {vid("C")})

  def testListScopeVarsByteString(self):
    interpolator = interpolation.Interpolator(b"%%foo.A%% %%foo.B%% %%foo.C%%")
    self.assertEqual(
        interpolator.ScopeVars(sid("foo")), {
            vid("A"),
            vid("B"),
            vid("C"),
        })

  def testBindVarSimpleUnicodeString(self):
    interpolator = interpolation.Interpolator("foo %%bar%% baz")
    interpolator.BindVar(vid("bar"), "quux")

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, ["foo quux baz"])

  def testBindVarSimpleByteString(self):
    interpolator = interpolation.Interpolator(b"foo %%bar%% baz")
    interpolator.BindVar(vid("bar"), "quux")

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, [b"foo quux baz"])

  def testBindVarWeirdUnicodeString(self):
    interpolator = interpolation.Interpolator("❄ %%foo%% 🌊")
    interpolator.BindVar(vid("foo"), "🎄")

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, ["❄ 🎄 🌊"])

  def testBindVarWeirdByteString(self):
    interpolator = interpolation.Interpolator(b"\xff %%foo%% \xff")
    interpolator.BindVar(vid("foo"), 42)

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, [b"\xff 42 \xff"])

  def testBindVarTwoIntegersToUnicodeString(self):
    interpolator = interpolation.Interpolator("%%foo%%%%bar%%")
    interpolator.BindVar(vid("foo"), 1)
    interpolator.BindVar(vid("foo"), 2)
    interpolator.BindVar(vid("bar"), 3)
    interpolator.BindVar(vid("bar"), 4)

    strings = list(interpolator.Interpolate())
    self.assertCountEqual(strings, ["13", "14", "23", "24"])

  def testBindVarTwoIntegersToByteString(self):
    interpolator = interpolation.Interpolator(b"%%foo%%%%bar%%")
    interpolator.BindVar(vid("foo"), 1)
    interpolator.BindVar(vid("foo"), 2)
    interpolator.BindVar(vid("bar"), 3)
    interpolator.BindVar(vid("bar"), 4)

    strings = list(interpolator.Interpolate())
    self.assertCountEqual(strings, [b"13", b"14", b"23", b"24"])

  def testBindVarKeyError(self):
    interpolator = interpolation.Interpolator("%%foo%%")

    with self.assertRaises(KeyError):
      interpolator.BindVar(vid("bar"), 42)

  def testDuplicatedVars(self):
    interpolator = interpolation.Interpolator("%%foo%%%%bar%%%%foo%%%%bar%%")
    interpolator.BindVar(vid("foo"), 1)
    interpolator.BindVar(vid("foo"), 2)
    interpolator.BindVar(vid("bar"), 3)
    interpolator.BindVar(vid("bar"), 4)

    strings = list(interpolator.Interpolate())
    self.assertCountEqual(strings, ["1313", "1414", "2323", "2424"])

  def testBindScopeSingleUnicodeString(self):
    interpolator = interpolation.Interpolator("%%foo.bar%% %%foo.baz%%")
    interpolator.BindScope(sid("foo"), {vid("bar"): "quux", vid("baz"): "norf"})

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, ["quux norf"])

  def testBindScopeSingleByteString(self):
    interpolator = interpolation.Interpolator(b"%%foo.A%% %%foo.B%% %%foo.C%%")
    interpolator.BindScope(sid("foo"), {vid("A"): 1, vid("B"): 2, vid("C"): 3})

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, [b"1 2 3"])

  def testBindScopeMultipleUnicodeString(self):
    pattern = "%%foo.bar%%$%%quux.norf%%$%%foo.baz%%$%%quux.thud%%"

    interpolator = interpolation.Interpolator(pattern)
    interpolator.BindScope(sid("foo"), {vid("bar"): 1, vid("baz"): 2})
    interpolator.BindScope(sid("foo"), {vid("bar"): 3, vid("baz"): 4})
    interpolator.BindScope(sid("quux"), {vid("norf"): 5, vid("thud"): 6})
    interpolator.BindScope(sid("quux"), {vid("norf"): 7, vid("thud"): 8})

    strings = list(interpolator.Interpolate())
    self.assertCountEqual(strings, ["1$5$2$6", "1$7$2$8", "3$5$4$6", "3$7$4$8"])

  def testBindScopeAndVarUnicodeString(self):
    pattern = "%%foo.bar%%|%%quux%%|%%foo.baz%%|%%norf.thud%%|%%norf.blargh%%"

    interpolator = interpolation.Interpolator(pattern)
    interpolator.BindVar(vid("quux"), 1)
    interpolator.BindVar(vid("quux"), 2)
    interpolator.BindScope(sid("foo"), {vid("bar"): 3, vid("baz"): 4})
    interpolator.BindScope(sid("foo"), {vid("bar"): 5, vid("baz"): 6})
    interpolator.BindScope(sid("norf"), {vid("thud"): 7, vid("blargh"): 8})
    interpolator.BindScope(sid("norf"), {vid("thud"): 9, vid("blargh"): 0})

    strings = list(interpolator.Interpolate())
    self.assertCountEqual(strings, [
        "3|1|4|7|8",
        "3|1|4|9|0",
        "3|2|4|7|8",
        "3|2|4|9|0",
        "5|1|6|7|8",
        "5|1|6|9|0",
        "5|2|6|7|8",
        "5|2|6|9|0",
    ])

  def testBindScopeKeyErrorScope(self):
    interpolator = interpolation.Interpolator("%%foo.bar%%")

    with self.assertRaises(KeyError):
      interpolator.BindScope(sid("quux"), {vid("bar"): 42})

  def testBindScopeKeyErrorVar(self):
    interpolator = interpolation.Interpolator("%%foo.bar%%")

    with self.assertRaises(KeyError):
      interpolator.BindScope(sid("foo"), {vid("baz"): 42})

  def testInterpolationHappensSimultaneously(self):
    interpolator = interpolation.Interpolator("%%foo%% %%bar.baz%% %%quux%%")
    interpolator.BindVar(vid("foo"), "%%bar.baz%%")
    interpolator.BindVar(vid("quux"), "%%foo%%")
    interpolator.BindScope(sid("bar"), {"baz": "%%foo%% %%quux%%"})

    strings = list(interpolator.Interpolate())
    self.assertEqual(strings, ["%%bar.baz%% %%foo%% %%quux%% %%foo%%"])


if __name__ == "__main__":
  absltest.main()
