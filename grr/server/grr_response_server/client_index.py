#!/usr/bin/env python
"""A keyword index of client machines.

An index of client machines, associating likely identifiers to client IDs.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import map  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues
from future.utils import string_types

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import keyword_index
from grr_response_server.aff4_objects import aff4_grr


def CreateClientIndex(token=None):
  return aff4.FACTORY.Create(
      rdfvalue.RDFURN("aff4:/client_index"),
      aff4_type=AFF4ClientIndex,
      mode="rw",
      object_exists=True,
      token=token)


class AFF4ClientIndex(keyword_index.AFF4KeywordIndex):
  """An index of client machines."""

  START_TIME_PREFIX = "start_date:"
  START_TIME_PREFIX_LEN = len(START_TIME_PREFIX)
  END_TIME_PREFIX = "end_date:"
  END_TIME_PREFIX_LEN = len(END_TIME_PREFIX)

  # We accept and return client URNs, but store client ids,
  # e.g. "C.00aaeccbb45f33a3".

  def _ClientIdFromURN(self, urn):
    return urn.Basename()

  def _NormalizeKeyword(self, keyword):
    return keyword.lower()

  def _AnalyzeKeywords(self, keywords):
    start_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("180d")
    end_time = rdfvalue.RDFDatetime(self.LAST_TIMESTAMP)
    filtered_keywords = []
    unversioned_keywords = []

    for k in keywords:
      if k.startswith(self.START_TIME_PREFIX):
        try:
          start_time = rdfvalue.RDFDatetime.FromHumanReadable(
              k[self.START_TIME_PREFIX_LEN:])
        except ValueError:
          pass
      elif k.startswith(self.END_TIME_PREFIX):
        try:
          end_time = rdfvalue.RDFDatetime.FromHumanReadable(
              k[self.END_TIME_PREFIX_LEN:], eoy=True)
        except (TypeError, ValueError):
          pass
      elif k[0] == "+":
        kw = k[1:]
        filtered_keywords.append(kw)
        unversioned_keywords.append(kw)
      else:
        filtered_keywords.append(k)

    if not filtered_keywords:
      filtered_keywords.append(".")

    return start_time, end_time, filtered_keywords, unversioned_keywords

  def LookupClients(self, keywords):
    """Returns a list of client URNs associated with keywords.

    Args:
      keywords: The list of keywords to search by.

    Returns:
      A list of client URNs.

    Raises:
      ValueError: A string (single keyword) was passed instead of an iterable.
    """
    if isinstance(keywords, string_types):
      raise ValueError(
          "Keywords should be an iterable, not a string (got %s)." % keywords)

    start_time, end_time, filtered_keywords, unversioned_keywords = (
        self._AnalyzeKeywords(keywords))

    last_seen_map = None
    if unversioned_keywords:
      last_seen_map = {}

    # TODO(user): Make keyword index datetime aware so that
    # AsMicrosecondsSinceEpoch is unnecessary.

    raw_results = self.Lookup(
        list(map(self._NormalizeKeyword, filtered_keywords)),
        start_time=start_time.AsMicrosecondsSinceEpoch(),
        end_time=end_time.AsMicrosecondsSinceEpoch(),
        last_seen_map=last_seen_map)
    if not raw_results:
      return []

    if unversioned_keywords:
      universal_last_seen_raw = {}
      self.ReadPostingLists(
          list(map(self._NormalizeKeyword, raw_results)),
          start_time=start_time.AsMicrosecondsSinceEpoch(),
          end_time=end_time.AsMicrosecondsSinceEpoch(),
          last_seen_map=universal_last_seen_raw)

      universal_last_seen = {}
      for (_, client_id), ts in iteritems(universal_last_seen_raw):
        universal_last_seen[client_id] = ts

      old_results = set()
      for keyword in unversioned_keywords:
        for result in raw_results:
          if last_seen_map[(keyword, result)] < universal_last_seen[result]:
            old_results.add(result)
      raw_results -= old_results

    return [rdf_client.ClientURN(result) for result in raw_results]

  def ReadClientPostingLists(self, keywords):
    """Looks up all clients associated with any of the given keywords.

    Args:
      keywords: A list of keywords we are interested in.
    Returns:
      A dict mapping each keyword to a list of matching clients.
    """

    start_time, end_time, filtered_keywords, _ = self._AnalyzeKeywords(keywords)

    # TODO(user): Make keyword index datetime aware so that
    # AsMicrosecondsSinceEpoch is unecessary.
    return self.ReadPostingLists(
        filtered_keywords,
        start_time=start_time.AsMicrosecondsSinceEpoch(),
        end_time=end_time.AsMicrosecondsSinceEpoch())

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
      segments = utils.SmartStr(keyword).split(delimiter)
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
    TryAppend("host", client.Get(s.FQDN))
    TryAppendPrefixes("host", client.Get(s.FQDN), ".")
    TryAppend("", client.Get(s.SYSTEM))
    TryAppend("", client.Get(s.UNAME))
    TryAppend("", client.Get(s.OS_RELEASE))
    TryAppend("", client.Get(s.OS_VERSION))
    TryAppend("", client.Get(s.KERNEL))
    TryAppend("", client.Get(s.ARCH))

    kb = client.Get(s.KNOWLEDGE_BASE)
    if kb:
      for user in kb.users:
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

    for interface in client.Get(s.INTERFACES, []):
      if interface.mac_address:
        TryAppendMac(interface.mac_address.human_readable_address)
      for ip in interface.GetIPAddresses():
        TryAppendIP(ip)

    # We should have all mac and ip addresses already, but some test data only
    # has it attached directly, so just in case we look there also.
    if client.Get(s.MAC_ADDRESS):
      for mac in str(client.Get(s.MAC_ADDRESS)).split("\n"):
        TryAppendMac(mac)
    ip_list = client.Get(s.HOST_IPS, "")
    for ip in str(ip_list).split("\n"):
      TryAppendIP(ip)

    client_info = client.Get(s.CLIENT_INFO)
    if client_info:
      TryAppend("client", client_info.client_name)
      TryAppend("client", client_info.client_version)
      if client_info.labels:
        for label in client_info.labels:
          TryAppend("label", label)

    for label in client.GetLabelsNames():
      TryAppend("label", label)

    return client_id, keywords

  def AddClient(self, client):
    """Adds a client to the index.

    Args:
      client: A VFSGRRClient record to add or update.
    """

    client_id, keywords = self.AnalyzeClient(client)
    self.AddKeywordsForName(client_id, keywords)

  def RemoveClientLabels(self, client):
    """Removes all labels for a given client object.

    Args:
      client: A VFSGRRClient record.
    """
    keywords = []
    for label in client.GetLabelsNames():
      keyword = self._NormalizeKeyword(utils.SmartStr(label))
      # This might actually delete a keyword with the same name as the label (if
      # there is one). Usually the client keywords will be rebuilt after the
      # deletion of the old labels though, so this can only destroy historic
      # index data; normal search functionality will not be affected.
      keywords.append(keyword)
      keywords.append("label:%s" % keyword)

    self.RemoveKeywordsForName(self._ClientIdFromURN(client.urn), keywords)


def GetClientURNsForHostnames(hostnames, token=None):
  """Gets all client_ids for a given list of hostnames or FQDNS.

  Args:
    hostnames: A list of hostnames / FQDNs.
    token: An ACL token.
  Returns:
    A dict with a list of all known GRR client_ids for each hostname.
  """

  if data_store.RelationalDBReadEnabled():
    index = ClientIndex()
  else:
    index = CreateClientIndex(token=token)

  keywords = set()
  for hostname in hostnames:
    if hostname.startswith("host:"):
      keywords.add(hostname)
    else:
      keywords.add("host:%s" % hostname)
  results = index.ReadClientPostingLists(keywords)

  result = {}
  for keyword, hits in iteritems(results):
    result[keyword[len("host:"):]] = hits
  return result


def GetMostRecentClient(client_list, token=None):
  """Return most recent client from list of clients."""
  last = rdfvalue.RDFDatetime(0)
  client_urn = None
  for client in aff4.FACTORY.MultiOpen(client_list, token=token):
    client_last = client.Get(client.Schema.LAST)
    if client_last > last:
      last = client_last
      client_urn = client.urn
  return client_urn


class ClientIndex(object):
  """An index of client machines."""

  START_TIME_PREFIX = "start_date:"
  START_TIME_PREFIX_LEN = len(START_TIME_PREFIX)

  def _NormalizeKeyword(self, keyword):
    return keyword.lower()

  def _AnalyzeKeywords(self, keywords):
    """Extracts a start time from a list of keywords if present."""
    start_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("180d")
    filtered_keywords = []

    for k in keywords:
      if k.startswith(self.START_TIME_PREFIX):
        try:
          start_time = rdfvalue.RDFDatetime.FromHumanReadable(
              k[self.START_TIME_PREFIX_LEN:])
        except ValueError:
          pass
      else:
        filtered_keywords.append(k)

    if not filtered_keywords:
      filtered_keywords.append(".")

    return start_time, filtered_keywords

  def LookupClients(self, keywords):
    """Returns a list of client URNs associated with keywords.

    Args:
      keywords: The list of keywords to search by.

    Returns:
      A list of client URNs.

    Raises:
      ValueError: A string (single keyword) was passed instead of an iterable.
    """
    if isinstance(keywords, string_types):
      raise ValueError(
          "Keywords should be an iterable, not a string (got %s)." % keywords)

    start_time, filtered_keywords = self._AnalyzeKeywords(keywords)

    keyword_map = data_store.REL_DB.ListClientsForKeywords(
        list(map(self._NormalizeKeyword, filtered_keywords)),
        start_time=start_time)

    results = itervalues(keyword_map)
    relevant_set = set(next(results))

    for hits in results:
      relevant_set &= set(hits)

      if not relevant_set:
        return []

    return sorted(relevant_set)

  def ReadClientPostingLists(self, keywords):
    """Looks up all clients associated with any of the given keywords.

    Args:
      keywords: A list of keywords we are interested in.
    Returns:
      A dict mapping each keyword to a list of matching clients.
    """

    start_time, filtered_keywords = self._AnalyzeKeywords(keywords)

    return data_store.REL_DB.ListClientsForKeywords(
        filtered_keywords, start_time=start_time)

  def AnalyzeClient(self, client):
    """Finds the client_id and keywords for a client.

    Args:
      client: A Client object record to find keywords for.

    Returns:
      A list of keywords related to client.
    """

    # Start with a universal keyword, used to find all clients.
    #
    # TODO(user): Remove the universal keyword once we have a better way
    # to do this, i.e., once we have a storage library which can list all
    # clients directly.

    keywords = set(["."])

    def TryAppend(prefix, keyword):
      if keyword:
        keyword_string = self._NormalizeKeyword(utils.SmartStr(keyword))
        keywords.add(keyword_string)
        if prefix:
          keywords.add(prefix + ":" + keyword_string)

    def TryAppendPrefixes(prefix, keyword, delimiter):
      TryAppend(prefix, keyword)
      segments = utils.SmartStr(keyword).split(delimiter)
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

    TryAppend("host", client.knowledge_base.fqdn)
    host = client.knowledge_base.fqdn.split(".", 1)[0]
    TryAppendPrefixes("host", host, "-")
    TryAppendPrefixes("host", client.knowledge_base.fqdn, ".")
    TryAppend("", client.knowledge_base.os)
    TryAppend("", client.Uname())
    TryAppend("", client.os_release)
    TryAppend("", client.os_version)
    TryAppend("", client.kernel)
    TryAppend("", client.arch)

    kb = client.knowledge_base
    if kb:
      for user in kb.users:
        TryAppend("user", user.username)
        TryAppend("", user.full_name)
        if user.full_name:
          for name in user.full_name.split():
            # full_name often includes nicknames and similar, wrapped in
            # punctuation, e.g. "Thomas 'TJ' Jones". We remove the most common
            # wrapping characters.
            TryAppend("", name.strip("\"'()"))

    for ip in client.GetIPAddresses():
      TryAppendIP(ip)
    for mac in client.GetMacAddresses():
      TryAppendMac(mac)

    client_info = client.startup_info.client_info
    if client_info:
      TryAppend("client", client_info.client_name)
      TryAppend("client", client_info.client_version)
      if client_info.labels:
        for label in client_info.labels:
          TryAppend("label", label)

    return keywords

  def AddClient(self, client):
    """Adds a client to the index.

    Args:
      client: A Client object record.
    """
    keywords = self.AnalyzeClient(client)
    keywords.add(self._NormalizeKeyword(client.client_id))

    data_store.REL_DB.AddClientKeywords(client.client_id, keywords)

  def AddClientLabels(self, client_id, labels):
    keywords = set()
    for label in labels:
      keyword_string = self._NormalizeKeyword(utils.SmartStr(label))
      keywords.add(keyword_string)
      keywords.add("label:" + keyword_string)

    data_store.REL_DB.AddClientKeywords(client_id, keywords)

  def RemoveAllClientLabels(self, client_id):
    """Removes all labels for a given client.

    Args:
      client_id: The client_id.
    """
    labels_to_remove = set(
        [l.name for l in data_store.REL_DB.ReadClientLabels(client_id)])
    self.RemoveClientLabels(client_id, labels_to_remove)

  def RemoveClientLabels(self, client_id, labels):
    """Removes all labels for a given client.

    Args:
      client_id: The client_id.
      labels: A list of labels to remove.
    """
    for label in labels:
      keyword = self._NormalizeKeyword(utils.SmartStr(label))
      # This might actually delete a keyword with the same name as the label (if
      # there is one).
      data_store.REL_DB.RemoveClientKeyword(client_id, keyword)
      data_store.REL_DB.RemoveClientKeyword(client_id, "label:%s" % keyword)


def BulkLabel(label, hostnames, owner=None, token=None, client_index=None):
  """Assign a label to a group of clients based on hostname.

  Sets a label as an identifier to a group of clients. Removes the label from
  other clients.

  This can be used to automate labeling clients based on externally derived
  attributes, for example machines assigned to particular users, or machines
  fulfilling particular roles.

  Args:
    label: The label to apply.
    hostnames: The collection of hostnames that should have the label.
    owner: The owner for the newly created labels. Defaults to token.username.
    token: The authentication token.
    client_index: An optional client index to use. If not provided, use the
      default client index.
  """
  if client_index is None:
    client_index = CreateClientIndex(token=token)

  fqdns = set()
  for hostname in hostnames:
    fqdns.add(hostname.lower())

  labelled_urns = client_index.LookupClients(["+label:%s" % label])

  # If a labelled client fqdn isn't in the set of target fqdns remove the label.
  # Labelled clients with a target fqdn need no action and are removed from the
  # set of target fqdns.
  for client in aff4.FACTORY.MultiOpen(
      labelled_urns, token=token, aff4_type=aff4_grr.VFSGRRClient, mode="rw"):
    fqdn = utils.SmartStr(client.Get("FQDN")).lower()
    if fqdn not in fqdns:
      client_index.RemoveClientLabels(client)
      client.RemoveLabel(label, owner=owner)
      client.Flush()
      client_index.AddClient(client)
    else:
      fqdns.discard(fqdn)

  # The residual set of fqdns needs labelling.
  # Get the latest URN for these clients and open them to add the label.
  urns = []
  keywords = ["+host:%s" % fqdn for fqdn in fqdns]
  for client_list in client_index.ReadClientPostingLists(keywords).itervalues():
    for client_id in client_list:
      urns.append(rdfvalue.RDFURN(client_id))

  for client in aff4.FACTORY.MultiOpen(
      urns, token=token, aff4_type=aff4_grr.VFSGRRClient, mode="rw"):
    client.AddLabel(label, owner=owner)
    client.Flush()
    client_index.AddClient(client)
