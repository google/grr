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

    # Start with both the client id itself, and a universal keyword, used to
    # find all clients.
    #
    # TODO(user): Remove the universal keyword once we have a better way
    # to do this, i.e., once we have a storage library which can list all
    # clients directly.

    keywords = [self._NormalizeKeyword(client_id), "."]

    def TryAppend(prefix, keyword):
      if keyword:
        keyword_string = self._NormalizeKeyword(utils.SmartStr(keyword))
        keywords.append(keyword_string)
        if prefix:
          keywords.append(prefix + ":" + keyword_string)

    def TryAppendPrefixes(prefix, keyword, delimiter):
      TryAppend(prefix, keyword)
      segments = str(keyword).split(delimiter)
      for i in range(1, len(segments)):
        TryAppend(prefix, delimiter.join(segments[0:i]))
      return len(segments)

    def TryAppendIP(ip):
      TryAppend("ip", ip)
      # IP4v?
      if TryAppendPrefixes("ip", str(ip), ".") == 4:
        return
      # IP6v?
      TryAppendPrefixes("ip", str(ip), ":")

    def TryAppendMac(mac):
      TryAppend("mac", mac)
      if len(mac) == 12:
        # If looks like a mac address without ":" symbols, also add the keyword
        # with them.
        TryAppend("mac", ":".join([mac[i:i + 2] for i in range(0, 12, 2)]))

    s = client.Schema
    TryAppend("host", client.Get(s.HOSTNAME))
    TryAppendPrefixes("host", client.Get(s.HOSTNAME), "-")
    TryAppend("fdqn", client.Get(s.FQDN))
    TryAppendPrefixes("host", client.Get(s.FQDN), ".")
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
        TryAppendMac(interface.mac_address.human_readable_address)
      for ip in interface.GetIPAddresses():
        TryAppendIP(ip)

    # We should have all mac and ip addresses already, but some test data only
    # has it attached directly, so just in case we look there also.
    if client.Get(s.MAC_ADDRESS):
      for mac in str(client.Get(s.MAC_ADDRESS)).split("\n"):
        TryAppendMac(mac)
    for ip_list in client.Get(s.HOST_IPS, []):
      for ip in str(ip_list).split("\n"):
        TryAppendIP(ip)

    client_info = client.Get(s.CLIENT_INFO)
    if client_info:
      TryAppend("client", client_info.client_name)
      if client_info.labels:
        for label in client_info.labels:
          TryAppend("label", label)

    for label in client.GetLabelsNames():
      TryAppend("label", label)

    return (client_id, keywords)

  def AddClient(self, client, **kwargs):
    """Adds a client to the index.

    Args:
      client: A VFSGRRClient record to add or update.
      **kwargs: Additional arguments to pass to the datastore.
    """

    self.AddKeywordsForName(*self.AnalyzeClient(client), **kwargs)
