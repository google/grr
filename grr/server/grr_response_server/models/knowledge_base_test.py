#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import knowledge_base_pb2
from grr_response_server.models import knowledge_base as models_knowledge_base


class MergeOrAddUserTest(absltest.TestCase):

  def testEmpty(self):
    kb = knowledge_base_pb2.KnowledgeBase()

    user = knowledge_base_pb2.User()
    user.username = "foo"
    user.full_name = "Jan Fóbarski"

    models_knowledge_base.MergeOrAddUser(kb, user)

    self.assertLen(kb.users, 1)
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jan Fóbarski")

  def testNewNotEmpty(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(uid=11, username="foo", full_name="Jan Fóbarski")
    kb.users.add(uid=17, username="bar", full_name="Basia Barbarska")

    user = knowledge_base_pb2.User()
    user.uid = 42
    user.username = "quux"
    user.full_name = "Gościwid Kwudzyniak"

    models_knowledge_base.MergeOrAddUser(kb, user)

    self.assertLen(kb.users, 3)

    self.assertEqual(kb.users[0].uid, 11)
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jan Fóbarski")

    self.assertEqual(kb.users[1].uid, 17)
    self.assertEqual(kb.users[1].username, "bar")
    self.assertEqual(kb.users[1].full_name, "Basia Barbarska")

    self.assertEqual(kb.users[2].uid, 42)
    self.assertEqual(kb.users[2].username, "quux")
    self.assertEqual(kb.users[2].full_name, "Gościwid Kwudzyniak")

  def testExistingByUID(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(uid=11, username="foo", full_name="Jan Fóbarski")
    kb.users.add(uid=17, username="bar", full_name="Basia Barbarska")

    user = knowledge_base_pb2.User()
    user.uid = 11
    user.full_name = "Jasiek Fóbarski"

    models_knowledge_base.MergeOrAddUser(kb, user)

    self.assertLen(kb.users, 2)

    self.assertEqual(kb.users[0].uid, 11)
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jasiek Fóbarski")

    self.assertEqual(kb.users[1].uid, 17)
    self.assertEqual(kb.users[1].username, "bar")
    self.assertEqual(kb.users[1].full_name, "Basia Barbarska")

  def testExistingByUsername(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(uid=11, username="foo", full_name="Jan Fóbarski")
    kb.users.add(uid=17, username="bar", full_name="Basia Barbarska")

    user = knowledge_base_pb2.User()
    user.username = "foo"
    user.full_name = "Jasiek Fóbarski"

    models_knowledge_base.MergeOrAddUser(kb, user)

    self.assertLen(kb.users, 2)

    self.assertEqual(kb.users[0].uid, 11)
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jasiek Fóbarski")

    self.assertEqual(kb.users[1].uid, 17)
    self.assertEqual(kb.users[1].username, "bar")
    self.assertEqual(kb.users[1].full_name, "Basia Barbarska")

  def testExistingBySID(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(sid="S-1-5-01-37", username="foo", full_name="Jan Fóbarski")
    kb.users.add(sid="S-1-5-01-38", username="bar", full_name="Basia Barbarska")

    user = knowledge_base_pb2.User()
    user.sid = "S-1-5-01-38"
    user.full_name = "Basia Barbarska-Kwudzyniak"

    models_knowledge_base.MergeOrAddUser(kb, user)

    self.assertLen(kb.users, 2)

    self.assertEqual(kb.users[0].sid, "S-1-5-01-37")
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jan Fóbarski")

    self.assertEqual(kb.users[1].sid, "S-1-5-01-38")
    self.assertEqual(kb.users[1].username, "bar")
    self.assertEqual(kb.users[1].full_name, "Basia Barbarska-Kwudzyniak")

  def testReconcileTransitive(self):
    kb = knowledge_base_pb2.KnowledgeBase()

    user_with_sid = knowledge_base_pb2.User()
    user_with_sid.sid = "S-1-5-01-37"
    user_with_sid.full_name = "Jan Fóbarski"
    models_knowledge_base.MergeOrAddUser(kb, user_with_sid)

    user_with_username = knowledge_base_pb2.User()
    user_with_username.username = "foo"
    user_with_username.userdomain = "GOOGLE"
    models_knowledge_base.MergeOrAddUser(kb, user_with_username)

    user_with_both = knowledge_base_pb2.User()
    user_with_both.sid = "S-1-5-01-37"
    user_with_both.username = "foo"
    models_knowledge_base.MergeOrAddUser(kb, user_with_both)

    self.assertLen(kb.users, 1)
    self.assertEqual(kb.users[0].sid, "S-1-5-01-37")
    self.assertEqual(kb.users[0].username, "foo")
    self.assertEqual(kb.users[0].full_name, "Jan Fóbarski")
    self.assertEqual(kb.users[0].userdomain, "GOOGLE")


if __name__ == "__main__":
  absltest.main()
