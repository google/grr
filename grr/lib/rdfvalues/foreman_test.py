#!/usr/bin/env python
"""Test for the foreman client rule classes."""



from grr.lib import aff4
from grr.lib.rdfvalues import test_base
from grr.server import foreman as rdf_foreman


def CollectAff4Objects(paths, client_id, token):
  """Mimics the logic in aff4_grr.py related to foreman rules."""
  object_urns = {}
  for path in paths:
    aff4_object = client_id.Add(path)
    object_urns[str(aff4_object)] = aff4_object

  objects = {
      fd.urn: fd
      for fd in aff4.FACTORY.MultiOpen(object_urns, token=token)
  }
  return objects


class ForemanClientRuleSetTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdf_foreman.ForemanClientRuleSet

  def GenerateSample(self, number=0):
    ret = rdf_foreman.ForemanClientRuleSet()

    # Use the number's least significant bit to assign a match mode
    if number % 1:
      ret.match_mode = rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL
    else:
      ret.match_mode = rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY

    # Generate a sequence of rules using all other bits
    ret.rules = [ForemanClientRuleTest.GenerateSample(n)
                 for n in xrange(number / 2)]

    return ret

  def testEvaluatesPositiveInMatchAnyModeIfOneRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=True))
        ])

    client_id_dar, = self.SetupClients(nr_clients=1, system="Darwin")
    # One of the set's rules has os_darwin=True, so the whole set matches
    # with the match any match mode
    self.assertTrue(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_dar, self.token),
        client_id_dar))

  def testEvaluatesNegativeInMatchAnyModeIfNoRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=True))
        ])

    client_id_win, = self.SetupClients(nr_clients=1, system="Windows")
    # None of the set's rules has os_windows=True, so the whole set doesn't
    # match
    self.assertFalse(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_win, self.token),
        client_id_win))

  def testEvaluatesNegativeInMatchAllModeIfOnlyOneRuleMatches(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=True))
        ])

    client_id_dar, = self.SetupClients(nr_clients=1, system="Darwin")
    # One of the set's rules has os_darwin=False, so the whole set doesn't
    # match with the match all match mode
    self.assertFalse(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_dar, self.token),
        client_id_dar))

  def testEvaluatesPositiveInMatchAllModeIfAllRuleMatch(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=False)),
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                                   os_linux=True,
                                                   os_darwin=True))
        ])

    client_id_lin, = self.SetupClients(nr_clients=1, system="Linux")
    # All of the set's rules have os_linux=False, so the whole set matches
    self.assertTrue(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_lin, self.token),
        client_id_lin))

  def testEvaluatesNegativeInMatchAnyModeWithNoRules(self):
    # Instantiate an empty rule set that matches if any of its rules matches
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[])

    client_id_lin, = self.SetupClients(nr_clients=1, system="Linux")
    # None of the set's rules has os_linux=True, so the set doesn't match
    self.assertFalse(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_lin, self.token),
        client_id_lin))

  def testEvaluatesPositiveInMatchAllModeWithNoRules(self):
    # Instantiate an empty rule set that matches if all of its rules match
    rs = rdf_foreman.ForemanClientRuleSet(
        match_mode=rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[])

    client_id_lin, = self.SetupClients(nr_clients=1, system="Linux")
    # All of the set's rules have os_linux=True, so the set matches
    self.assertTrue(rs.Evaluate(
        CollectAff4Objects(rs.GetPathsToCheck(), client_id_lin, self.token),
        client_id_lin))


class ForemanClientRuleTest(test_base.RDFValueTestCase):
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
        os=rdf_foreman.ForemanOsClientRule(os_windows=True,
                                           os_linux=True,
                                           os_darwin=False))

    client_id_win, = self.SetupClients(nr_clients=1, system="Windows")
    # The Windows client matches rule r
    self.assertTrue(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id_win, self.token),
        client_id_win))

  def testEvaluatesNegativeIfNestedRuleEvaluatesNegative(self):
    # Instantiate a wrapped operating system rule
    r = rdf_foreman.ForemanClientRule(
        rule_type=rdf_foreman.ForemanClientRule.Type.OS,
        os=rdf_foreman.ForemanOsClientRule(os_windows=False,
                                           os_linux=True,
                                           os_darwin=False))

    client_id_win, = self.SetupClients(nr_clients=1, system="Windows")
    # The Windows client doesn't match rule r
    self.assertFalse(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id_win, self.token),
        client_id_win))


class ForemanOsClientRuleTest(test_base.RDFValueTestCase):
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
    return rdf_foreman.ForemanOsClientRule(os_windows=number & 1,
                                           os_linux=number & 2,
                                           os_darwin=number & 4)

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    # Instantiate an operating system rule
    r = rdf_foreman.ForemanOsClientRule(os_windows=False,
                                        os_linux=False,
                                        os_darwin=False)

    client_id_win, = self.SetupClients(nr_clients=1, system="Windows")
    self.assertFalse(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id_win, self.token),
        client_id_win))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(os_windows=False,
                                         os_linux=False,
                                         os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(os_windows=False,
                                         os_linux=True,
                                         os_darwin=False)

    client_id_lin, = self.SetupClients(nr_clients=1, system="Linux")
    self.assertFalse(r0.Evaluate(
        CollectAff4Objects(r0.GetPathsToCheck(), client_id_lin, self.token),
        client_id_lin))
    self.assertTrue(r1.Evaluate(
        CollectAff4Objects(r1.GetPathsToCheck(), client_id_lin, self.token),
        client_id_lin))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    # Instantiate two operating system rules
    r0 = rdf_foreman.ForemanOsClientRule(os_windows=False,
                                         os_linux=True,
                                         os_darwin=False)

    r1 = rdf_foreman.ForemanOsClientRule(os_windows=True,
                                         os_linux=False,
                                         os_darwin=True)

    client_id_dar, = self.SetupClients(nr_clients=1, system="Darwin")
    self.assertFalse(r0.Evaluate(
        CollectAff4Objects(r0.GetPathsToCheck(), client_id_dar, self.token),
        client_id_dar))
    self.assertTrue(r1.Evaluate(
        CollectAff4Objects(r1.GetPathsToCheck(), client_id_dar, self.token),
        client_id_dar))


class ForemanLabelClientRuleTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdf_foreman.ForemanLabelClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients labeled str(number)
    return rdf_foreman.ForemanLabelClientRule(label_names=[str(number)])

  def testEvaluatesToFalseForClientWithoutTheLabel(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(label_names=["arbitrary text"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client isn't labeled "arbitrary text"
    self.assertFalse(r.Evaluate(objects, client_id))

  def testEvaluatesToTrueForClientWithTheLabel(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(label_names=["world"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client is labeled "world"
    self.assertTrue(r.Evaluate(objects, client_id))

  def testEvaluatesToTrueInMatchAnyModeIfClientHasOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "world"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client is labeled "world"
    self.assertTrue(r.Evaluate(objects, client_id))

  def testEvaluatesToFalseInMatchAnyModeIfClientHasNoneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertFalse(r.Evaluate(objects, client_id))

  def testEvaluatesToTrueInMatchAllModeIfClientHasAllOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "hello"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client is labeled both "world" and "hello"
    self.assertTrue(r.Evaluate(objects, client_id))

  def testEvaluatesToFalseInMatchAllModeIfClientDoesntHaveOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "random"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client isn't labeled "random"
    self.assertFalse(r.Evaluate(objects, client_id))

  def testEvaluatesToFalseInDoesntMatchAnyModeIfClientHasOneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "world"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client is labeled "world"
    self.assertFalse(r.Evaluate(objects, client_id))

  def testEvaluatesToTrueInDoesntMatchAnyModeIfClientHasNoneOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "arbitrary"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertTrue(r.Evaluate(objects, client_id))

  def testEvaluatesToFalseInDoesntMatchAllModeIfClientHasAllOfTheLabels(self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "hello"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client is labeled both "world" and "hello"
    self.assertFalse(r.Evaluate(objects, client_id))

  def testEvaluatesToTrueInDoesntMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self):
    # Instantiate a label rule
    r = rdf_foreman.ForemanLabelClientRule(
        match_mode=rdf_foreman.ForemanLabelClientRule.MatchMode.
        DOES_NOT_MATCH_ALL,
        label_names=["world", "random"])

    client_id, = self.SetupClients(nr_clients=1)

    objects = CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token)
    # Label the client
    objects[client_id].SetLabels("hello", "world", owner="GRR")

    # The client isn't labeled "random"
    self.assertTrue(r.Evaluate(objects, client_id))


class ForemanRegexClientRuleTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdf_foreman.ForemanRegexClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients that have str(number) in their MAC
    return rdf_foreman.ForemanRegexClientRule(attribute_name="MAC",
                                              attribute_regex=str(number))

  def testEvaluatesTheWholeAttributeToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(attribute_name="type",
                                           attribute_regex="^VFSGRRClient$")

    client_id, = self.SetupClients(nr_clients=1)

    # Aff4 object type is VFSGRRClient
    self.assertTrue(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))

  def testEvaluatesAttributesSubstringToTrue(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(attribute_name="type",
                                           attribute_regex="GRR")

    client_id, = self.SetupClients(nr_clients=1)

    # The type contains the substring GRR
    self.assertTrue(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))

  def testEvaluatesNonSubstringToFalse(self):
    # Instantiate a regex rule
    r = rdf_foreman.ForemanRegexClientRule(attribute_name="type",
                                           attribute_regex="foo")

    client_id, = self.SetupClients(nr_clients=1)

    # The type doesn't contain foo
    self.assertFalse(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))


class ForemanIntegerClientRuleTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdf_foreman.ForemanIntegerClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients with the attribute size equal to number
    return rdf_foreman.ForemanIntegerClientRule(
        attribute_name="size",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.EQUAL,
        value=number)

  def testEvaluatesSizeLessThanZeroToFalse(self):
    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        attribute_name="size",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=0)

    client_id, = self.SetupClients(nr_clients=1)

    # The size is not less than 0
    self.assertFalse(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))

  def testEvaluatesSizeGreaterThanMinusOneToTrue(self):
    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        attribute_name="size",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=-1)

    client_id, = self.SetupClients(nr_clients=1)

    # size > -1
    self.assertTrue(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))

  def testEvaluatesToFalseWithNonIntAttribute(self):
    # Instantiate an integer rule
    r = rdf_foreman.ForemanIntegerClientRule(
        attribute_name="Host",
        operator=rdf_foreman.ForemanIntegerClientRule.Operator.EQUAL,
        value=123)

    client_id, = self.SetupClients(nr_clients=1)

    # Host is not a number
    self.assertFalse(r.Evaluate(
        CollectAff4Objects(r.GetPathsToCheck(), client_id, self.token),
        client_id))
