#!/usr/bin/env python
"""Utils for flow related tasks."""


def GetUserInfo(knowledge_base, user):
  r"""Get a User protobuf for a specific user.

  Args:
    knowledge_base: An rdf_client.KnowledgeBase object.
    user: Username as string. May contain domain like DOMAIN\user.

  Returns:
    A User rdfvalue or None
  """
  if "\\" in user:
    domain, user = user.split("\\", 1)
    users = [
        u for u in knowledge_base.users
        if u.username == user and u.userdomain == domain
    ]
  else:
    users = [u for u in knowledge_base.users if u.username == user]

  if not users:
    return
  else:
    return users[0]
