#!/usr/bin/env python
# Lint as: python3
"""A keyword index of client machines.

An index of client machines, associating likely identifiers to client IDs.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import operator
from typing import Text


from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import precondition
from grr_response_server import data_store


def GetClientIDsForHostnames(hostnames):
  """Gets all client_ids for a given list of hostnames or FQDNS.

  Args:
    hostnames: A list of hostnames / FQDNs.

  Returns:
    A dict with a list of all known GRR client_ids for each hostname.
  """

  index = ClientIndex()

  keywords = set()
  for hostname in hostnames:
    if hostname.startswith("host:"):
      keywords.add(hostname)
    else:
      keywords.add("host:%s" % hostname)
  results = index.ReadClientPostingLists(keywords)

  result = {}
  for keyword, hits in results.items():
    result[keyword[len("host:"):]] = hits
  return result


class ClientIndex(object):
  """An index of client machines."""

  START_TIME_PREFIX = "start_date:"
  START_TIME_PREFIX_LEN = len(START_TIME_PREFIX)

  def _NormalizeKeyword(self, keyword):
    return Text(keyword).lower()

  def _AnalyzeKeywords(self, keywords):
    """Extracts a start time from a list of keywords if present."""
    start_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        180, rdfvalue.DAYS)
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
    if isinstance(keywords, str):
      raise ValueError(
          "Keywords should be an iterable, not a string (got %s)." % keywords)

    start_time, filtered_keywords = self._AnalyzeKeywords(keywords)

    keyword_map = data_store.REL_DB.ListClientsForKeywords(
        list(map(self._NormalizeKeyword, filtered_keywords)),
        start_time=start_time)

    relevant_set = functools.reduce(operator.and_, map(set,
                                                       keyword_map.values()))
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
      precondition.AssertType(prefix, Text)
      precondition.AssertType(keyword, Text)
      if keyword:
        keyword_string = self._NormalizeKeyword(keyword)
        keywords.add(keyword_string)
        if prefix:
          keywords.add(prefix + ":" + keyword_string)

    def TryAppendPrefixes(prefix, keyword, delimiter):
      TryAppend(prefix, keyword)
      segments = keyword.split(delimiter)
      for i in range(1, len(segments)):
        TryAppend(prefix, delimiter.join(segments[0:i]))
      return len(segments)

    def TryAppendIP(ip):
      TryAppend("ip", ip)
      # IP4v?
      if TryAppendPrefixes("ip", Text(ip), ".") == 4:
        return
      # IP6v?
      TryAppendPrefixes("ip", Text(ip), ":")

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
      TryAppend("client", Text(client_info.client_version))
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
    precondition.AssertIterableType(labels, Text)
    keywords = set()
    for label in labels:
      keyword_string = self._NormalizeKeyword(label)
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
      keyword = self._NormalizeKeyword(label)
      # This might actually delete a keyword with the same name as the label (if
      # there is one).
      data_store.REL_DB.RemoveClientKeyword(client_id, keyword)
      data_store.REL_DB.RemoveClientKeyword(client_id, "label:%s" % keyword)
