#!/usr/bin/env python
"""Module with data models and helpers related to knowledge base."""

from grr_response_proto import knowledge_base_pb2


# TODO: Should this be named just `MergeUser`? The "or add" is kind
# of obvious and only adds unnecessary visual clutter to code.
def MergeOrAddUser(
    kb: knowledge_base_pb2.KnowledgeBase,
    user: knowledge_base_pb2.User,
) -> None:
  """Merges a user into existing users or add new if it doesn't exist.

  Args:
    kb: Knowledge base object to modify.
    user: User to merge or add into the knowledgebase.
  """
  kb_user_idxes = []  # Indices to knowledgebase users matching the given user.

  for kb_user_idx, kb_user in enumerate(kb.users):
    if any([
        user.sid and user.sid == kb_user.sid,
        # The original `MergeOrAddUsers` explicitly acknowledges its limitations
        # when it comes to handling users with UID 0.
        #
        # However, this seems not to be a problem in practice: we only ever get
        # UID information on Linux. But on Linux, UID of 0 is reserved for the
        # root user [1] and we collect information only about "normal" users.
        #
        # pylint: disable=line-too-long
        # [1]: https://superuser.com/questions/626843/does-the-root-account-always-have-uid-gid-0
        # pylint: enable=line-too-long
        user.uid and user.uid == kb_user.uid,
        user.username and user.username == kb_user.username,
    ]):
      kb_user_idxes.append(kb_user_idx)

  if not kb_user_idxes:
    # Nothing matched, we create a new user.
    kb.users.add().CopyFrom(user)
  else:
    # We have non-zero matches. We merge everything into the first matching user
    # (there can be more than one in which case the new user allowed us to merge
    # some existing users). Note that we merge from first to last (including the
    # newest) as if we made the merges all along.
    for kb_user_idx in kb_user_idxes[1:]:
      kb.users[kb_user_idxes[0]].MergeFrom(kb.users[kb_user_idx])
    kb.users[kb_user_idxes[0]].MergeFrom(user)

    # Finally, once everything is merged, we delete duplicated users. Note that
    # we cannot do it during the loop above not to mess up the indices.
    for kb_user_idx in kb_user_idxes[1:]:
      del kb.users[kb_user_idx]
