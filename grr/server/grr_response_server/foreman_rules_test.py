#!/usr/bin/env python
"""Test for the foreman client rule classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


class ForemanClientRuleSetTest(rdf_test_base.RDFValueTestMixin,
                               test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanClientRuleSet

  def GenerateSample(self, number=0):
    ret = foreman_rules.ForemanClientRuleSet()

    # Use the number's least significant bit to assign a match mode
    if number % 1:
      ret.match_mode = foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL
    else:
      ret.match_mode = foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY

    # Generate a sequence of rules using all other bits
    ret.rules = [
        ForemanClientRuleTest.GenerateSample(n) for n in range(number // 2)
    ]

    return ret

  def testEvaluatesPositiveInMatchAnyModeIfOneRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True))
        ])

    client_id_dar = self.SetupClient(0, system="Darwin")
    # One of the set's rules has os_darwin=True, so the whole set matches
    # with the match any match mode
    self.assertTrue(
        rs.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))

  def testEvaluatesNegativeInMatchAnyModeIfNoRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True))
        ])

    client_id_win = self.SetupClient(0, system="Windows")
    # None of the set's rules has os_windows=True, so the whole set doesn't
    # match
    self.assertFalse(
        rs.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))

  def testEvaluatesNegativeInMatchAllModeIfOnlyOneRuleMatches(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True))
        ])

    client_id_dar = self.SetupClient(0, system="Darwin")
    # One of the set's rules has os_darwin=False, so the whole set doesn't
    # match with the match all match mode
    self.assertFalse(
        rs.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))

  def testEvaluatesPositiveInMatchAllModeIfAllRuleMatch(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True))
        ])

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=False, so the whole set matches
    self.assertTrue(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testEvaluatesNegativeInMatchAnyModeWithNoRules(self):
    # Instantiate an empty rule set that matches if any of its rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[])

    client_id_lin = self.SetupClient(0, system="Linux")
    # None of the set's rules has os_linux=True, so the set doesn't match
    self.assertFalse(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testEvaluatesPositiveInMatchAllModeWithNoRules(self):
    # Instantiate an empty rule set that matches if all of its rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[])

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=True, so the set matches
    self.assertTrue(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))


class ForemanClientRuleTest(rdf_test_base.RDFValueTestMixin,
                            test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanClientRule

  @staticmethod
  def GenerateSample(number=0):
    # Wrap the operating system rule sample generator
    return foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=ForemanOsClientRuleTest.GenerateSample(number))

  def testEvaluatesPositiveIfNestedRuleEvaluatesPositive(self):
    r = foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=foreman_rules.ForemanOsClientRule(
            os_windows=True, os_linux=True, os_darwin=False))

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client matches rule r
    self.assertTrue(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))

  def testEvaluatesNegativeIfNestedRuleEvaluatesNegative(self):
    r = foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=foreman_rules.ForemanOsClientRule(
            os_windows=False, os_linux=True, os_darwin=False))

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client doesn't match rule r
    self.assertFalse(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))


class ForemanOsClientRuleTest(rdf_test_base.RDFValueTestMixin,
                              test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanOsClientRule

  @staticmethod
  def GenerateSample(number=0):
    # Assert that the argument uses at most the three least significant bits
    num_combinations = 2**3
    if number < 0 or number >= num_combinations:
      raise ValueError(
          "Only %d distinct instances of %s exist, "
          "numbered from 0 to %d." %
          (num_combinations, foreman_rules.ForemanOsClientRule.__name__,
           num_combinations - 1))

    # Assign the bits to new rule's boolean fields accordingly
    return foreman_rules.ForemanOsClientRule(
        os_windows=number & 1, os_linux=number & 2, os_darwin=number & 4)

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    r = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    client_id_win = self.SetupClient(0, system="Windows")
    self.assertFalse(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    client_id_lin = self.SetupClient(0, system="Linux")
    self.assertFalse(
        r0.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))
    self.assertTrue(
        r1.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True)

    client_id_dar = self.SetupClient(0, system="Darwin")
    self.assertFalse(
        r0.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))
    self.assertTrue(
        r1.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))


class ForemanOsClientRuleTestRelational(db_test_lib.RelationalDBEnabledMixin,
                                        test_lib.GRRBaseTest):

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    r = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    client = self.SetupTestClientObject(0, system="Windows")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)
    self.assertFalse(r.Evaluate(info))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True)

    client = self.SetupTestClientObject(0, system="Darwin")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))


class ForemanLabelClientRuleTest(rdf_test_base.RDFValueTestMixin,
                                 test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanLabelClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients labeled str(number)
    return foreman_rules.ForemanLabelClientRule(label_names=[str(number)])

  def _Evaluate(self, rule):
    client_id = self.SetupClient(0)

    client_obj = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    client_obj.SetLabels(["hello", "world"], owner=u"GRR")

    return rule.Evaluate(client_obj)

  def testEvaluatesToFalseForClientWithoutTheLabel(self):
    r = foreman_rules.ForemanLabelClientRule(label_names=["arbitrary text"])

    # The client isn't labeled "arbitrary text"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueForClientWithTheLabel(self):
    r = foreman_rules.ForemanLabelClientRule(label_names=["world"])

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAnyModeIfClientHasOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "world"])

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAnyModeIfClientHasNoneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAllModeIfClientHasAllOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "hello"])

    # The client is labeled both "world" and "hello"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAllModeIfClientDoesntHaveOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "random"])

    # The client isn't labeled "random"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAnyModeIfClientHasOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "world"])

    # The client is labeled "world"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAnyModeIfClientHasNoneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAllModeIfClientHasAllOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "hello"])

    # The client is labeled both "world" and "hello"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "random"])

    # The client isn't labeled "random"
    self.assertTrue(self._Evaluate(r))


class ForemanLabelClientRuleTestRelational(db_test_lib.RelationalDBEnabledMixin,
                                           ForemanLabelClientRuleTest):

  def _Evaluate(self, rule):
    client = self.SetupTestClientObject(0)

    data_store.REL_DB.AddClientLabels(client.client_id, u"GRR",
                                      [u"hello", u"world"])

    client_info = data_store.REL_DB.ReadClientFullInfo(client.client_id)
    return rule.Evaluate(client_info)


class ForemanRegexClientRuleTest(rdf_test_base.RDFValueTestMixin,
                                 test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanRegexClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients that have str(number) in their MAC
    return foreman_rules.ForemanRegexClientRule(
        field="MAC_ADDRESSES", attribute_regex=str(number))

  def testEvaluatesTheWholeAttributeToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="^Linux$")

    client_id = self.SetupClient(0, system="Linux")
    self.assertTrue(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testEvaluatesAttributesSubstringToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="inu")

    client_id = self.SetupClient(0, system="Linux")

    # The system contains the substring inu
    self.assertTrue(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testEvaluatesNonSubstringToFalse(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="foo")

    client_id = self.SetupClient(0, system="Linux")

    # The system doesn't contain foo
    self.assertFalse(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testUnsetFieldRaises(self):
    client_id = self.SetupClient(0, system="Linux")
    client = aff4.FACTORY.Open(client_id, token=self.token)

    r = foreman_rules.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      r.Evaluate(client)

  def testLabels(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="ell")

    client_id = self.SetupClient(0, system="Linux")
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    self.assertFalse(r.Evaluate(client))

    client.SetLabels(["hello", "world"], owner=u"GRR")
    self.assertTrue(r.Evaluate(client))


class ForemanRegexClientRuleTestRelational(db_test_lib.RelationalDBEnabledMixin,
                                           test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    for f in foreman_rules.ForemanRegexClientRule.ForemanStringField.enum_dict:
      if f == "UNSET":
        continue

      r = foreman_rules.ForemanRegexClientRule(field=f, attribute_regex=".")
      r.Evaluate(info)

  def testEvaluatesTheWholeAttributeToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="^Linux$")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesAttributesSubstringToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="inu")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    # The system contains the substring inu
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesNonSubstringToFalse(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="foo")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    # The system doesn't contain foo
    self.assertFalse(r.Evaluate(info))

  def testUnsetFieldRaises(self):
    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    r = foreman_rules.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      r.Evaluate(info)

  def testLabels(self):
    client = self.SetupTestClientObject(0, system="Linux")

    data_store.REL_DB.AddClientLabels(client.client_id, u"GRR",
                                      [u"hello", u"world"])

    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    # Match a system label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="label1")
    self.assertTrue(r.Evaluate(info))

    # Match a user label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="ell")
    self.assertTrue(r.Evaluate(info))

    # This rule doesn't match any label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="NonExistentLabel")
    self.assertFalse(r.Evaluate(info))


class ForemanIntegerClientRuleTest(rdf_test_base.RDFValueTestMixin,
                                   test_lib.GRRBaseTest):
  rdfvalue_class = foreman_rules.ForemanIntegerClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients with the attribute size equal to number
    return foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.EQUAL,
        value=number)

  def testEvaluatesSizeLessThanEqualValueToFalse(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsSecondsSinceEpoch())

    # The values are the same, less than should not trigger.
    self.assertFalse(r.Evaluate(client))

  def testEvaluatesSizeGreaterThanSmallerValueToTrue(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)

    before_boot = now - 1

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot.AsSecondsSinceEpoch())

    self.assertTrue(r.Evaluate(client))

  def testEvaluatesRaisesWithUnsetField(self):
    r = foreman_rules.ForemanIntegerClientRule(
        operator=foreman_rules.ForemanIntegerClientRule.Operator.EQUAL,
        value=123)

    client_id = self.SetupClient(0)

    with self.assertRaises(ValueError):
      r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token))


class ForemanIntegerClientRuleTestRelational(
    db_test_lib.RelationalDBEnabledMixin, test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    int_f = foreman_rules.ForemanIntegerClientRule.ForemanIntegerField
    for f in int_f.enum_dict:
      if f == "UNSET":
        continue

      r = foreman_rules.ForemanIntegerClientRule(
          field=f,
          operator=foreman_rules.ForemanIntegerClientRule.Operator.LESS_THAN,
          value=now.AsSecondsSinceEpoch())
      r.Evaluate(info)

  def testEvaluatesSizeLessThanEqualValueToFalse(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsSecondsSinceEpoch())

    # The values are the same, less than should not trigger.
    self.assertFalse(r.Evaluate(info))

  def testEvaluatesSizeGreaterThanSmallerValueToTrue(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    before_boot = now - 1

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot.AsSecondsSinceEpoch())

    self.assertTrue(r.Evaluate(info))

  def testEvaluatesRaisesWithUnsetField(self):
    r = foreman_rules.ForemanIntegerClientRule(
        operator=foreman_rules.ForemanIntegerClientRule.Operator.EQUAL,
        value=123)

    client = self.SetupTestClientObject(0)
    info = data_store.REL_DB.ReadClientFullInfo(client.client_id)

    with self.assertRaises(ValueError):
      r.Evaluate(info)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
