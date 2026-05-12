#!/usr/bin/env python
import ipaddress

from absl.testing import absltest

from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import foreman_rules
from grr_response_server.databases import db as abstract_db
from grr.test_lib import db_test_lib


class EvaluateForemanRuleSetTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testEvaluatesPositiveInMatchAnyModeIfOneRuleMatches(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_dar = "C.1%015x" % 1
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_dar,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Darwin"),
    )
    db.WriteClientMetadata(client_id_dar)
    db.WriteClientSnapshot(snapshot)
    # One of the set's rules has os_darwin=True, so the whole set matches
    # with the match any match mode
    self.assertTrue(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_dar),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesNegativeInMatchAnyModeIfNoRuleMatches(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_win = "C.1%015x" % 2
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_win,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Windows"),
    )
    db.WriteClientMetadata(client_id_win)
    db.WriteClientSnapshot(snapshot)
    # None of the set's rules has os_windows=True, so the whole set doesn't
    # match
    self.assertFalse(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_win),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesNegativeInMatchAllModeIfOnlyOneRuleMatches(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_dar = "C.1%015x" % 3
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_dar,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Darwin"),
    )
    db.WriteClientMetadata(client_id_dar)
    db.WriteClientSnapshot(snapshot)
    # One of the set's rules has os_darwin=False, so the whole set doesn't
    # match with the match all match mode
    self.assertFalse(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_dar),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesPositiveInMatchAllModeIfAllRuleMatch(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_lin = "C.1%015x" % 4
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_lin,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id_lin)
    db.WriteClientSnapshot(snapshot)
    # All of the set's rules have os_linux=True, so the whole set matches
    self.assertTrue(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_lin),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesNegativeInMatchAnyModeWithNoRules(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate an empty rule set that matches if any of its rules matches
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[],
    )

    client_id_lin = "C.1%015x" % 5
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_lin,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id_lin)
    db.WriteClientSnapshot(snapshot)
    # The set has no rules with MATCH_ANY mode, so the set doesn't match
    self.assertFalse(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_lin),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesPositiveInMatchAllModeWithNoRules(
      self, db: abstract_db.Database
  ) -> None:
    # Instantiate an empty rule set that matches if all of its rules match
    rs = jobs_pb2.ForemanClientRuleSet(
        match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[],
    )

    client_id_lin = "C.1%015x" % 6
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_lin,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id_lin)
    db.WriteClientSnapshot(snapshot)
    # The set has no rules with MATCH_ALL mode, so the set matches
    self.assertTrue(
        foreman_rules.EvaluateForemanRuleSet(
            rs,
            db.ReadClientFullInfo(client_id_lin),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesPositiveIfNestedRuleEvaluatesPositive(
      self, db: abstract_db.Database
  ) -> None:
    r = jobs_pb2.ForemanClientRule(
        rule_type=jobs_pb2.ForemanClientRule.Type.OS,
        os=jobs_pb2.ForemanOsClientRule(
            os_windows=True, os_linux=True, os_darwin=False
        ),
    )

    client_id_win = "C.1%015x" % 7
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_win,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Windows"),
    )
    db.WriteClientMetadata(client_id_win)
    db.WriteClientSnapshot(snapshot)

    # The Windows client matches rule r
    self.assertTrue(
        foreman_rules.EvaluateForemanRuleSet(
            jobs_pb2.ForemanClientRuleSet(rules=[r]),
            db.ReadClientFullInfo(client_id_win),
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesNegativeIfNestedRuleEvaluatesNegative(
      self, db: abstract_db.Database
  ) -> None:
    r = jobs_pb2.ForemanClientRule(
        rule_type=jobs_pb2.ForemanClientRule.Type.OS,
        os=jobs_pb2.ForemanOsClientRule(
            os_windows=False, os_linux=True, os_darwin=False
        ),
    )

    client_id_win = "C.1%015x" % 8
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id_win,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Windows"),
    )
    db.WriteClientMetadata(client_id_win)
    db.WriteClientSnapshot(snapshot)

    # The Windows client doesn't match rule r
    self.assertFalse(
        foreman_rules.EvaluateForemanRuleSet(
            jobs_pb2.ForemanClientRuleSet(rules=[r]),
            db.ReadClientFullInfo(client_id_win),
        )
    )


class EvaluateForemanOsClientRuleTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(
      self, db: abstract_db.Database
  ) -> None:
    r = jobs_pb2.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False
    )

    client_id = "C.1%015x" % 9
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Windows"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    self.assertFalse(
        foreman_rules.EvaluateForemanOsClientRule(
            r, db.ReadClientFullInfo(client_id)
        )
    )

  @db_test_lib.WithDatabase
  def testLinuxClientMatchesIffOsLinuxIsSelected(
      self, db: abstract_db.Database
  ) -> None:
    r0 = jobs_pb2.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False
    )

    r1 = jobs_pb2.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False
    )

    client_id = "C.1%015x" % 10
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    info = db.ReadClientFullInfo(client_id)
    self.assertFalse(foreman_rules.EvaluateForemanOsClientRule(r0, info))
    self.assertTrue(foreman_rules.EvaluateForemanOsClientRule(r1, info))

  @db_test_lib.WithDatabase
  def testDarwinClientMatchesIffOsDarwinIsSelected(
      self, db: abstract_db.Database
  ) -> None:
    r0 = jobs_pb2.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False
    )

    r1 = jobs_pb2.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True
    )

    client_id = "C.1%015x" % 11
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Darwin"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    info = db.ReadClientFullInfo(client_id)
    self.assertFalse(foreman_rules.EvaluateForemanOsClientRule(r0, info))
    self.assertTrue(foreman_rules.EvaluateForemanOsClientRule(r1, info))


class EvaluateForemanLabelClientRuleTest(absltest.TestCase):

  def _SetupClientWithLabels(
      self, db: abstract_db.Database, labels: list[str]
  ) -> objects_pb2.ClientFullInfo:
    client_id = "C.1%015x" % 12
    db.WriteClientMetadata(client_id)
    db.WriteGRRUser("GRR")
    db.AddClientLabels(client_id, "GRR", labels)

    return db.ReadClientFullInfo(client_id)

  @db_test_lib.WithDatabase
  def testEvaluatesToFalseForClientWithoutTheLabel(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(label_names=["arbitrary text"])

    # The client isn't labeled "arbitrary text"
    self.assertFalse(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToTrueForClientWithTheLabel(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(label_names=["world"])

    # The client is labeled "world"
    self.assertTrue(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToTrueInMatchAnyModeIfClientHasOneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "world"],
    )

    # The client is labeled "world"
    self.assertTrue(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToFalseInMatchAnyModeIfClientHasNoneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "arbitrary"],
    )

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertFalse(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToTrueInMatchAllModeIfClientHasAllOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "hello"],
    )

    # The client is labeled both "world" and "hello"
    self.assertTrue(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToFalseInMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "random"],
    )

    # The client isn't labeled "random"
    self.assertFalse(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToFalseInDoesntMatchAnyModeIfClientHasOneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "world"],
    )

    # The client is labeled "world"
    self.assertFalse(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToTrueInDoesntMatchAnyModeIfClientHasNoneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "arbitrary"],
    )

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertTrue(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToFalseInDoesntMatchAllModeIfClientHasAllOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ALL,
        label_names=["world", "hello"],
    )

    # The client is labeled both "world" and "hello"
    self.assertFalse(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )

  @db_test_lib.WithDatabase
  def testEvaluatesToTrueInDoesntMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self, db: abstract_db.Database
  ) -> None:
    client_info = self._SetupClientWithLabels(db, ["hello", "world"])
    r = jobs_pb2.ForemanLabelClientRule(
        match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ALL,
        label_names=["world", "random"],
    )

    # The client isn't labeled "random"
    self.assertTrue(
        foreman_rules.EvaluateForemanLabelClientRule(r, client_info)
    )


class EvaluateForemanRegexClientRuleTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testEvaluatesTheWholeAttributeToTrue(
      self, db: abstract_db.Database
  ) -> None:
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.SYSTEM,
        attribute_regex="^Linux$",
    )

    client_id = "C.1%015x" % 14
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    self.assertTrue(
        foreman_rules.EvaluateForemanRegexClientRule(
            r, db.ReadClientFullInfo(client_id)
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesAttributesSubstringToTrue(
      self, db: abstract_db.Database
  ) -> None:
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.SYSTEM,
        attribute_regex="inu",
    )

    client_id = "C.1%015x" % 15
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    # The system contains the substring inu
    self.assertTrue(
        foreman_rules.EvaluateForemanRegexClientRule(
            r, db.ReadClientFullInfo(client_id)
        )
    )

  @db_test_lib.WithDatabase
  def testEvaluatesNonSubstringToFalse(self, db: abstract_db.Database) -> None:
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.SYSTEM,
        attribute_regex="foo",
    )

    client_id = "C.1%015x" % 16
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    # The system doesn't contain foo
    self.assertFalse(
        foreman_rules.EvaluateForemanRegexClientRule(
            r, db.ReadClientFullInfo(client_id)
        )
    )

  @db_test_lib.WithDatabase
  def testUnsetFieldRaises(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 17
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Linux"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)

    r = jobs_pb2.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      foreman_rules.EvaluateForemanRegexClientRule(
          r, db.ReadClientFullInfo(client_id)
      )

  @db_test_lib.WithDatabase
  def testUsernames(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 18
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(
            users=[knowledge_base_pb2.User(username="user1")]
        ),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.USERNAMES,
        attribute_regex=r"user1",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.USERNAMES,
        attribute_regex=r"root",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testFqdn(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 19
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(
            fqdn="foo.bar.example.com"
        ),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.FQDN,
        attribute_regex=r"foo.*\.example\.com",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.FQDN,
        attribute_regex=r"localhost",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testHostIps(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 20
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        interfaces=[
            jobs_pb2.Interface(
                addresses=[
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET,
                        packed_bytes=ipaddress.IPv4Address(
                            "192.168.0.1"
                        ).packed,
                    ),
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET6,
                        packed_bytes=ipaddress.IPv6Address(
                            "2001:abcd::1"
                        ).packed,
                    ),
                ]
            )
        ],
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match first address
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.HOST_IPS,
        attribute_regex=r"\b192\.168\.0\.\d+\b",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Match second address
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.HOST_IPS,
        attribute_regex=r"\b2001:abcd::",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.HOST_IPS,
        attribute_regex=r"10",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testClientName(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 21
    db.WriteClientMetadata(client_id)
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        startup_info=jobs_pb2.StartupInfo(
            client_info=jobs_pb2.ClientInformation(
                client_name="Monitor",
            )
        ),
    )
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_NAME,
        attribute_regex=r"Monitor",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_NAME,
        attribute_regex=r"GRRMonitor",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testClientDescription(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 22
    db.WriteClientMetadata(client_id)
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        startup_info=jobs_pb2.StartupInfo(
            client_info=jobs_pb2.ClientInformation(
                client_description="GRR Description Text",
            )
        ),
    )
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_DESCRIPTION,
        attribute_regex=r"description text",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_DESCRIPTION,
        attribute_regex=r"GRRDescription",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testSystem(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 23
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        knowledge_base=knowledge_base_pb2.KnowledgeBase(os="Windows"),
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.SYSTEM,
        attribute_regex=r"Win",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.SYSTEM,
        attribute_regex=r"Linux",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testMacAddresses(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 24
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        interfaces=[
            jobs_pb2.Interface(mac_address=b"\xaa\xbb\xcc\xdd\xee\x00"),
            jobs_pb2.Interface(mac_address=b"\xbb\xcc\xdd\xee\xff\x00"),
        ],
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match first address
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.MAC_ADDRESSES,
        attribute_regex=r"\bAABBCCDDEE\d+\b",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Match second address
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.MAC_ADDRESSES,
        attribute_regex=r"\bBBCCDDEEFF\d+\b",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.MAC_ADDRESSES,
        attribute_regex=r"\b000000",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testKernelVersion(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 25
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id, kernel="5.15.0-1042-gcp"
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.KERNEL_VERSION,
        attribute_regex=r"^5\..*-gcp$",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.KERNEL_VERSION,
        attribute_regex=r"^4",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testOsVersion(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 26
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id, os_version="10.0.22621"
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.OS_VERSION,
        attribute_regex=r"^10\..*",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.OS_VERSION,
        attribute_regex=r"22.04",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testOsRelease(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 27
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id, os_release="Debian"
    )
    db.WriteClientMetadata(client_id)
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.OS_RELEASE,
        attribute_regex=r"\bDebian\b",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.OS_RELEASE,
        attribute_regex=r"\bVista\b",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testLabels(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 28
    db.WriteClientMetadata(client_id)
    db.WriteGRRUser("GRR")
    db.AddClientLabels(client_id, "GRR", ["hello", "world"])
    info = db.ReadClientFullInfo(client_id)

    # Match a user label.
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_LABELS,
        attribute_regex="ell",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # This rule doesn't match any label.
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_LABELS,
        attribute_regex="NonExistentLabel",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))

  @db_test_lib.WithDatabase
  def testClientId(self, db: abstract_db.Database) -> None:
    client_id = "C.1000000000000001"
    db.WriteClientMetadata(client_id)
    info = db.ReadClientFullInfo(client_id)

    # Match identifier
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_ID,
        attribute_regex=client_id,
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Match slice
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_ID,
        attribute_regex=r"C\.10.*",
    )
    self.assertTrue(foreman_rules.EvaluateForemanRegexClientRule(r, info))

    # Non-match
    r = jobs_pb2.ForemanRegexClientRule(
        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.CLIENT_ID,
        attribute_regex=r"abc",
    )
    self.assertFalse(foreman_rules.EvaluateForemanRegexClientRule(r, info))


class EvaluateForemanIntegerClientRuleTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testEvaluatesSizeLessThanEqualValueToFalse(
      self, db: abstract_db.Database
  ) -> None:
    now_us = 1709355863000000
    client_id = "C.1%015x" % 30
    db.WriteClientMetadata(client_id)
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        startup_info=jobs_pb2.StartupInfo(boot_time=now_us),
    )
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    r = jobs_pb2.ForemanIntegerClientRule(
        field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.LAST_BOOT_TIME,
        operator=jobs_pb2.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now_us // 1_000_000,
    )

    # The values are the same, less than should not trigger.
    self.assertFalse(foreman_rules.EvaluateForemanIntegerClientRule(r, info))

  @db_test_lib.WithDatabase
  def testEvaluatesSizeGreaterThanSmallerValueToTrue(
      self, db: abstract_db.Database
  ) -> None:
    now_us = 1709355863000000
    client_id = "C.1%015x" % 31
    db.WriteClientMetadata(client_id)
    snapshot = objects_pb2.ClientSnapshot(
        client_id=client_id,
        startup_info=jobs_pb2.StartupInfo(boot_time=now_us),
    )
    db.WriteClientSnapshot(snapshot)
    info = db.ReadClientFullInfo(client_id)

    before_boot_s = (now_us - 1) // 1_000_000

    r = jobs_pb2.ForemanIntegerClientRule(
        field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.LAST_BOOT_TIME,
        operator=jobs_pb2.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot_s,
    )

    self.assertTrue(foreman_rules.EvaluateForemanIntegerClientRule(r, info))

  @db_test_lib.WithDatabase
  def testEvaluatesRaisesWithUnsetField(self, db: abstract_db.Database) -> None:
    client_id = "C.1%015x" % 32
    db.WriteClientMetadata(client_id)
    info = db.ReadClientFullInfo(client_id)

    r = jobs_pb2.ForemanIntegerClientRule(
        operator=jobs_pb2.ForemanIntegerClientRule.Operator.EQUAL,
        value=123,
    )
    with self.assertRaises(ValueError):
      foreman_rules.EvaluateForemanIntegerClientRule(r, info)


class ValidateForemanRuleSetTest(absltest.TestCase):

  def testValidRuleSet(self):
    rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(os_linux=True),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                label=jobs_pb2.ForemanLabelClientRule(label_names=["foo"]),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.FQDN,
                    attribute_regex="foo",
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                integer=jobs_pb2.ForemanIntegerClientRule(
                    field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION,
                    operator=jobs_pb2.ForemanIntegerClientRule.Operator.EQUAL,
                    value=123,
                ),
            ),
        ]
    )
    foreman_rules.ValidateForemanRuleSet(rule_set)

  def testInvalidRegexRule(self):
    rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.UNSET,
                    attribute_regex="foo",
                ),
            ),
        ]
    )
    with self.assertRaisesRegex(ValueError, "field not set"):
      foreman_rules.ValidateForemanRuleSet(rule_set)

  def testInvalidIntegerRule(self):
    rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                integer=jobs_pb2.ForemanIntegerClientRule(
                    field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.UNSET,
                    operator=jobs_pb2.ForemanIntegerClientRule.Operator.EQUAL,
                    value=123,
                ),
            ),
        ]
    )
    with self.assertRaisesRegex(ValueError, "field not set"):
      foreman_rules.ValidateForemanRuleSet(rule_set)

  def testNoRuleTypeSet(self):
    rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(),
        ]
    )
    with self.assertRaisesRegex(ValueError, "no type set"):
      foreman_rules.ValidateForemanRuleSet(rule_set)


class ValidateConditionTest(absltest.TestCase):

  def testValidCondition(self):
    condition = jobs_pb2.ForemanCondition(
        creation_time=1000,
        expiration_time=2000,
        client_rule_set=jobs_pb2.ForemanClientRuleSet(
            rules=[
                jobs_pb2.ForemanClientRule(
                    rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                    regex=jobs_pb2.ForemanRegexClientRule(
                        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.FQDN,
                        attribute_regex="foo",
                    ),
                ),
                jobs_pb2.ForemanClientRule(
                    rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                    integer=jobs_pb2.ForemanIntegerClientRule(
                        field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION,
                        operator=jobs_pb2.ForemanIntegerClientRule.Operator.EQUAL,
                        value=123,
                    ),
                ),
            ]
        ),
    )
    foreman_rules.ValidateForemanCondition(condition)

  def testInvalidRegexRule(self):
    condition = jobs_pb2.ForemanCondition(
        creation_time=1000,
        expiration_time=2000,
        client_rule_set=jobs_pb2.ForemanClientRuleSet(
            rules=[
                jobs_pb2.ForemanClientRule(
                    rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                    regex=jobs_pb2.ForemanRegexClientRule(
                        field=jobs_pb2.ForemanRegexClientRule.ForemanStringField.UNSET,
                        attribute_regex="foo",
                    ),
                ),
            ]
        ),
    )
    with self.assertRaisesRegex(ValueError, "field not set"):
      foreman_rules.ValidateForemanCondition(condition)

  def testInvalidIntegerRule(self):
    condition = jobs_pb2.ForemanCondition(
        creation_time=1000,
        expiration_time=2000,
        client_rule_set=jobs_pb2.ForemanClientRuleSet(
            rules=[
                jobs_pb2.ForemanClientRule(
                    rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                    integer=jobs_pb2.ForemanIntegerClientRule(
                        field=jobs_pb2.ForemanIntegerClientRule.ForemanIntegerField.UNSET,
                        operator=jobs_pb2.ForemanIntegerClientRule.Operator.EQUAL,
                        value=123,
                    ),
                ),
            ]
        ),
    )
    with self.assertRaisesRegex(ValueError, "field not set"):
      foreman_rules.ValidateForemanCondition(condition)


if __name__ == "__main__":
  absltest.main()
