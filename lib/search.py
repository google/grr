#!/usr/bin/env python
"""Functions for searching."""
import itertools
import re

from grr.lib import aff4
from grr.lib import rdfvalue


CLIENT_SCHEMA = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
INDEX_PREFIX_MAP = {"host": CLIENT_SCHEMA.HOSTNAME,
                    "fqdn": CLIENT_SCHEMA.FQDN,
                    "mac": CLIENT_SCHEMA.MAC_ADDRESS,
                    "label": CLIENT_SCHEMA.LABELS,
                    "user": CLIENT_SCHEMA.USERNAMES,
                    "ip": CLIENT_SCHEMA.HOST_IPS}


def SearchClients(query_string, start=0, max_results=1000, token=None):
  """Take a query string and interpret it as a search, returning ClientURNs."""
  query_string = query_string.strip()
  mac_addr_re = r"^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$"
  result_iterators = []

  try:
    # If someone specified a client_id we use that.
    result_iterators.append([rdfvalue.ClientURN(query_string.strip())])
  except ValueError:
    pass

  if not result_iterators:
    # Search via the indexes.
    query_string = query_string.lower()
    client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
    index_urn = client_schema.client_index
    index = aff4.FACTORY.Create(index_urn, aff4_type="AFF4Index",
                                mode="rw", token=token)

    labels_index = aff4.FACTORY.Create(
        aff4.VFSGRRClient.labels_index_urn, aff4_type="AFF4LabelsIndex",
        mode="rw", token=token)

    indexed_attrs = []

    prefix = ""
    if ":" in query_string:
      prefix = query_string.split(":", 1)[0]
      if re.match(r"^[0-9a-f]{2}$", prefix):
        # Handle the special MAC weird case e.g. mac:DE:AD:BE:EF:AA:AA.
        prefix = ""
      if prefix:
        if prefix not in INDEX_PREFIX_MAP:
          raise IOError("Invalid prefix %s. Choose from %s" % (
              prefix, INDEX_PREFIX_MAP.keys()))

        query_string = query_string.split(":", 1)[1]

    if prefix:
      # Search a specific index.
      indexed_attrs = INDEX_PREFIX_MAP[prefix]
      if not isinstance(indexed_attrs, list):
        indexed_attrs = [INDEX_PREFIX_MAP[prefix]]
    else:
      # Search all indexes.
      indexed_attrs = [a for a in client_schema().ListAttributes() if a.index]
      indexed_attrs.append(client_schema.LABELS)

    # Fixup MAC addresses to match the MAC index format.
    match = re.search(mac_addr_re, query_string)
    if match:
      query_string = query_string.replace(":", "").replace("-", "")

    # Get the main results using wildcard matches.
    if indexed_attrs != [client_schema.LABELS]:
      # If matching start or end of string, handle that explicitly.
      wildcard_query = query_string
      if not wildcard_query.startswith("^"):
        wildcard_query = ".*%s" % wildcard_query
      if not wildcard_query.endswith("$"):
        wildcard_query = "%s.*" % wildcard_query
      search_results = index.Query(
          indexed_attrs, wildcard_query, limit=(start, max_results))
      search_results = [rdfvalue.ClientURN(r) for r in search_results]
      result_iterators.append(search_results)

    if client_schema.LABELS in indexed_attrs:
      label_matches = []
      # Labels need to be exact matches.
      label_results = itertools.chain.from_iterable(
          labels_index.FindUrnsByLabelNameRegex(query_string).itervalues())
      label_results = itertools.islice(label_results, start, max_results)

      # The above returns all labels, not all of which will be clients, we need
      # to filter for those that are clients.
      for result in label_results:
        try:
          result = rdfvalue.ClientURN(result)
          label_matches.append(result)
        except ValueError:
          pass
      result_iterators.append(label_matches)

  return itertools.chain(*result_iterators)


def GetClientURNsForHostnames(hostnames, token=None):
  """Gets all client_ids for a given list of hostnames or FQDNS.

  Args:
    hostnames: A list of hostnames / FQDNs.
    token: An ACL token.
  Returns:
    A dict with a list of all known GRR client_ids for each hostname.
  """

  client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
  index_urn = client_schema.client_index
  index = aff4.FACTORY.Create(index_urn, aff4_type="AFF4Index",
                              mode="rw", token=token)
  hostname = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls.HOSTNAME
  fqdn = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls.FQDN
  result = {}
  query_result = index.MultiQuery([hostname, fqdn], hostnames)
  for hostname, urns in query_result.iteritems():
    result[hostname] = [rdfvalue.ClientURN(urn) for urn in urns]
  return result
