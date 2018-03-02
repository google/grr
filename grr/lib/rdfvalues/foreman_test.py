#!/usr/bin/env python
"""Test for the foreman client rule classes."""

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base
from grr.server import aff4
from grr.server import data_store
from grr.server import foreman as rdf_foreman
from grr.test_lib import test_lib


class ForemanClientRuleSetTest(test_base.RDFValueTestMixin,
                               test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanClientRuleSet

  def GenerateSample(self, number=0):
    ret = rdf_foreman.ForemanClientRuleSet()

    # Use the number's least significant bit to assign a match mode
    if number % 1:
      ret.match_mode = rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL
    else:
      ret.match_mode = rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY

    # Generate a sequence of rules using all other bits
    ret.rules = [
        ForemanClientRuleTest.GenerateSample(n) for n in xrange(number / 2)
    ]

    return ret

  def testEvaluatesPositiveInMatchAnyModeIfOneRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
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
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
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
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
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
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True))
        ])

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=False, so the whole set matches
    self.assertTrue(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testEvaluatesNegativeInMatchAnyModeWithNoRules(self):
    # Instantiate an empty rule set that matches if any of its rules matches
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[])

    client_id_lin = self.SetupClient(0, system="Linux")
    # None of the set's rules has os_linux=True, so the set doesn't match
    self.assertFalse(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testEvaluatesPositiveInMatchAllModeWithNoRules(self):
    # Instantiate an empty rule set that matches if all of its rules match
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[])

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=True, so the set matches
    self.assertTrue(
        rs.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))


class ForemanClientRuleTest(test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanClientRule

  @staticmethod
  def GenerateSample(number=0):
    # Wrap the operating system rule sample generator
    return rdf_foreman.ForemanClientRule(
        rule_type=rdf_foreman.ForemanClientRule.Type.OS,
        os=ForemanOsClientRuleTest.GenerateSample(number))

  def testEvaluatesPositiveIfNestedRuleEvaluatesPositive(self):
    # Instantiate a wrapped operating system rule
    r = rdf_foreman.ForemanClientRule(
        rule_type=rdf_foreman.ForemanClientRule.Type.OS,
        os=rdf_foreman.ForemanOsClientRule(
            os_windows=True, os_linux=True, os_darwin=False))

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client matches rule r
    self.assertTrue(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))

  def testEvaluatesNegativeIfNestedRuleEvaluatesNegative(self):
    # Instantiate a wrapped operating system rule
    r = rdf_foreman.ForemanClientRule(
        rule_type=rdf_foreman.ForemanClientRule.Type.OS,
        os=rdf_foreman.ForemanOsClientRule(
            os_windows=False, os_linux=True, os_darwin=False))

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client doesn't match rule r
    self.assertFalse(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))


class ForemanOsClientRuleTest(test_base.RDFValueTestMixin,
                              test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanOsClientRule

  @staticmethod
  def GenerateSample(number=0):
    # Assert that the argument uses at most the three least significant bits
    num_combinations = 2**3
    if number < 0 or number >= num_combinations:
      raise ValueError("Only %d distinct instances of %s exist, "
                       "numbered from 0 to %d." %
                       (num_combinations,
                        rdf_foreman.ForemanOsClientRule.__name__,
                        num_combinations - 1))

    # Assign the bits to new rule's boolean fields accordingly
    return rdf_foreman.ForemanOsClientRule(
        os_windows=number & 1, os_linux=number & 2, os_darwin=number & 4)

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    # Instantiate an operating system rule
    r = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    client_id_win = self.SetupClient(0, system="Windows")
    self.assertFalse(
        r.Evaluate(aff4.FACTORY.Open(client_id_win, token=self.token)))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    client_id_lin = self.SetupClient(0, system="Linux")
    self.assertFalse(
        r0.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))
    self.assertTrue(
        r1.Evaluate(aff4.FACTORY.Open(client_id_lin, token=self.token)))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True)

    client_id_dar = self.SetupClient(0, system="Darwin")
    self.assertFalse(
        r0.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))
    self.assertTrue(
        r1.Evaluate(aff4.FACTORY.Open(client_id_dar, token=self.token)))


class ForemanOsClientRuleTestRelational(test_lib.RelationalDBTestMixin,
                                        test_lib.GRRBaseTest):

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    # Instantiate an operating system rule
    r = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    client = self.SetupTestClientObject(0, system="Windows")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)
    self.assertFalse(r.Evaluate(info))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True)

    client = self.SetupTestClientObject(0, system="Darwin")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))


class ForemanLabelClientRuleTest(test_base.RDFValueTestMixin,
                                 test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanLabelClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients labeled str(number)
    return rdf_foreman.ForemanLabelClientRule(label_names=[str(number)])

  def _Evaluate(self, rule):
    client_id = self.SetupClient(0)

    client_obj = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    client_obj.SetLabels(["hello", "world"], owner="GRR")

    return rule.Evaluate(client_obj)

  def testEvaluatesToFalseForClientWithoutTheLabel(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(label_names=["arbitrary text"])

    # The client isn't labeled "arbitrary text"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueForClientWithTheLabel(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(label_names=["world"])

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAnyModeIfClientHasOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "world"])

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAnyModeIfClientHasNoneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAllModeIfClientHasAllOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "hello"])

    # The client is labeled both "world" and "hello"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAllModeIfClientDoesntHaveOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "random"])

    # The client isn't labeled "random"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAnyModeIfClientHasOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "world"])

    # The client is labeled "world"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAnyModeIfClientHasNoneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAllModeIfClientHasAllOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "hello"])

    # The client is labeled both "world" and "hello"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "random"])

    # The client isn't labeled "random"
    self.assertTrue(self._Evaluate(r))


class ForemanLabelClientRuleTestRelational(test_lib.RelationalDBTestMixin,
                                           ForemanLabelClientRuleTest):

  def _Evaluate(self, rule):
    client = self.SetupTestClientObject(0)

    data_store.REL_DB.AddClientLabels(client.client_id, "GRR",
                                      ["hello", "world"])

    client_info = data_store.REL_DB.ReadFullInfoClient(client.client_id)
    return rule.Evaluate(client_info)


class ForemanRegexClientRuleTest(test_base.RDFValueTestMixin,
                                 test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanRegexClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients that have str(number) in their MAC
    return rdf_foreman.ForemanRegexClientRule(
        field="MAC_ADDRESSES", attribute_regex=str(number))

  def testEvaluatesTheWholeAttributeToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="^Linux$")

    client_id = self.SetupClient(0, system="Linux")
    self.assertTrue(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testEvaluatesAttributesSubstringToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="inu")

    client_id = self.SetupClient(0, system="Linux")

    # The system contains the substring inu
    self.assertTrue(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testEvaluatesNonSubstringToFalse(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="foo")

    client_id = self.SetupClient(0, system="Linux")

    # The system doesn't contain foo
    self.assertFalse(r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token)))

  def testUnsetFieldRaises(self):
    client_id = self.SetupClient(0, system="Linux")
    client = aff4.FACTORY.Open(client_id, token=self.token)

    r = rdf_foreman.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      r.Evaluate(client)


class ForemanRegexClientRuleTestRelational(test_lib.RelationalDBTestMixin,
                                           test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    for f in rdf_foreman.ForemanRegexClientRule.ForemanStringField.enum_dict:
      if f == "UNSET":
        continue

      r = rdf_foreman.ForemanRegexClientRule(field=f, attribute_regex=".")
      r.Evaluate(info)

  def testEvaluatesTheWholeAttributeToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="^Linux$")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesAttributesSubstringToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="inu")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    # The system contains the substring inu
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesNonSubstringToFalse(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="foo")

    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    # The system doesn't contain foo
    self.assertFalse(r.Evaluate(info))

  def testUnsetFieldRaises(self):
    client = self.SetupTestClientObject(0, system="Linux")
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    r = rdf_foreman.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      r.Evaluate(info)


class ForemanIntegerClientRuleTest(test_base.RDFValueTestMixin,
                                   test_lib.GRRBaseTest):
  rdfvalue_class = rdf_foreman.ForemanIntegerClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients with the attribute size equal to number
    return rdf_foreman.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.EQUAL,
        value=number)

  def testEvaluatesSizeLessThanEqualValueToFalse(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)

    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsSecondsFromEpoch())

    # The values are the same, less than should not trigger.
    self.assertFalse(r.Evaluate(client))

  def testEvaluatesSizeGreaterThanSmallerValueToTrue(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)

    before_boot = now - 1

    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot.AsSecondsFromEpoch())

    self.assertTrue(r.Evaluate(client))

  def testEvaluatesRaisesWithUnsetField(self):
    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.EQUAL, value=123)

    client_id = self.SetupClient(0)

    with self.assertRaises(ValueError):
      r.Evaluate(aff4.FACTORY.Open(client_id, token=self.token))


class ForemanIntegerClientRuleTestRelational(test_lib.RelationalDBTestMixin,
                                             test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    for f in rdf_foreman.ForemanIntegerClientRule.ForemanIntegerField.enum_dict:
      if f == "UNSET":
        continue

      r = rdf_foreman.ForemanIntegerClientRule(
          field=f,
          operator=rdf_foreman.ForemanIntegerClientRule.Operator.LESS_THAN,
          value=now.AsSecondsFromEpoch())
      r.Evaluate(info)

  def testEvaluatesSizeLessThanEqualValueToFalse(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsSecondsFromEpoch())

    # The values are the same, less than should not trigger.
    self.assertFalse(r.Evaluate(info))

  def testEvaluatesSizeGreaterThanSmallerValueToTrue(self):
    now = rdfvalue.RDFDatetime().Now()
    client = self.SetupTestClientObject(0, last_boot_time=now)
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    before_boot = now - 1

    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot.AsSecondsFromEpoch())

    self.assertTrue(r.Evaluate(info))

  def testEvaluatesRaisesWithUnsetField(self):
    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.EQUAL, value=123)

    client = self.SetupTestClientObject(0)
    info = data_store.REL_DB.ReadFullInfoClient(client.client_id)

    with self.assertRaises(ValueError):
      r.Evaluate(info)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
