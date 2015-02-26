#!/usr/bin/env python
"""A keyword index of client machines.

An index of client machines, associating likely identifiers to client IDs.
"""



from grr.lib import keyword_index
from grr.lib import rdfvalue
from grr.lib import utils

# The system's primary client index.
MAIN_INDEX = rdfvalue.RDFURN("aff4:/client_index")


class ClientIndex(keyword_index.AFF4KeywordIndex):
  """An index of client machines.
  """

  # We accept and return client URNs, but store client ids,
  # e.g. "C.00aaeccbb45f33a3".

  def _ClientIdFromURN(self, urn):
    return urn.Basename()

  def _URNFromClientID(self, client_id):
    return rdfvalue.ClientURN(client_id)

  def _NormalizeKeyword(self, keyword):
    return keyword.lower()

  def LookupClients(self, keywords):
    """Returns a list of client URNs associated with keywords.

    Args:
      keywords: The list of keywords to search by.

    Returns:
      A list of client URNs.
    """
    return map(self._URNFromClientID,
               self.Lookup(map(self._NormalizeKeyword, keywords)))

  def AnalyzeClient(self, client):
    """Finds the client_id and keywords for a client.

    Args:
      client: A VFSGRRClient record to find keywords for.

    Returns:
      A tuple (client_id, keywords) where client_id is the client identifier and
    keywords is a list of keywords related to client.
    """
    client_id = self._ClientIdFromURN(client.urn)
    keywords = [client_id]

    def TryAppend(prefix, keyword):
      if keyword:
        keyword_string = self._NormalizeKeyword(utils.SmartStr(keyword))
        keywords.append(keyword_string)
        if prefix:
          keywords.append(prefix + ":" + keyword_string)

    def TryAppendIP(ip):
      TryAppend("ip", ip)
      # IP4v?
      octets = str(ip).split(".")
      if len(octets) == 4:
        TryAppend("ip", octets[0])
        TryAppend("ip", ".".join(octets[0:2]))
        TryAppend("ip", ".".join(octets[0:3]))
        return
      # IP6v?
      groups = str(ip).split(":")
      if len(groups) > 1:
        TryAppend("ip", groups[0])
      if len(groups) > 2:
        TryAppend("ip", ":".join(groups[0:2]))
      if len(groups) > 3:
        TryAppend("ip", ":".join(groups[0:3]))

    s = client.Schema
    TryAppend("host", client.Get(s.HOSTNAME))
    TryAppend("fdqn", client.Get(s.FQDN))
    TryAppend("", client.Get(s.SYSTEM))
    TryAppend("", client.Get(s.UNAME))
    TryAppend("", client.Get(s.OS_RELEASE))
    TryAppend("", client.Get(s.OS_VERSION))
    TryAppend("", client.Get(s.KERNEL))
    TryAppend("", client.Get(s.ARCH))

    for user in client.Get(s.USER, []):
      TryAppend("user", user.username)
      TryAppend("", user.full_name)
      if user.full_name:
        for name in user.full_name.split():
          # full_name often includes nicknames and similar, wrapped in
          # punctuation, e.g. "Thomas 'TJ' Jones". We remove the most common
          # wrapping characters.
          TryAppend("", name.strip("\"'()"))

    for username in client.Get(s.USERNAMES, []):
      TryAppend("user", username)

    for interface in client.Get(s.LAST_INTERFACES, []):
      if interface.mac_address:
        TryAppend("mac", interface.mac_address.human_readable_address)
      for ip in interface.GetIPAddresses():
        TryAppendIP(ip)

    # We should have all mac and ip addresses already, but some test data only
    # has it attached directly, so just in case we look there also.
    if client.Get(s.MAC_ADDRESS):
      for mac in str(client.Get(s.MAC_ADDRESS)).split("\n"):
        TryAppend("mac", mac)
    for ip_list in client.Get(s.HOST_IPS, []):
      for ip in str(ip_list).split("\n"):
        TryAppendIP(ip)

    client_info = client.Get(s.CLIENT_INFO)
    if client_info:
      TryAppend("client", client_info.client_name)
      if client_info.labels:
        for label in client_info.labels:
          TryAppend("label", label)

    return (client_id, keywords)

  def AddClient(self, client):
    """Adds a client to the index.

    Args:
      client: A VFSGRRClient record to add or update.
    """
    self.AddKeywordsForName(*self.AnalyzeClient(client))
