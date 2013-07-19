#!/usr/bin/env python
"""Functions for searching."""
import re

from grr.lib import aff4


def SearchClients(query_string, start=0, max_results=1000, token=None):
  """Take a query string and interpret it as a search, returning clients."""
  query_string = query_string.strip()
  mac_addr_re = r"^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$"

  cid_match = re.search(r"(C\.[0-9a-f]{16})", query_string)
  if cid_match:
    # Shortcut for fully qualified Client IDs.
    client_id = cid_match.group(1)
    result_set = [aff4.FACTORY.Open("aff4:/%s" % client_id, token=token)]

  else:
    # Search via the indexes.
    query_string = query_string.lower()
    client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
    index_urn = client_schema.client_index
    index = aff4.FACTORY.Create(index_urn, "AFF4Index", mode="r",
                                token=token)
    indexed_attrs = []
    prefix_map = {"host": client_schema.HOSTNAME,
                  "fqdn": client_schema.FQDN,
                  "mac": client_schema.MAC_ADDRESS,
                  "user": client_schema.USERNAMES}

    prefix = ""
    if ":" in query_string:
      prefix = query_string.split(":", 1)[0]
      if re.match(r"^[0-9a-f]{2}$", prefix):
        # Handle the special MAC wierd case e.g. mac:DE:AD:BE:EF:AA:AA.
        prefix = ""
      if prefix:
        if prefix not in prefix_map:
          raise IOError("Invalid prefix %s. Choose from %s" % (
              prefix, prefix_map.keys()))
        else:
          query_string = query_string.split(":", 1)[1]

    if prefix:
      # Search a specific index.
      indexed_attrs = [prefix_map[prefix]]
    else:
      # Search all indexes.
      indexed_attrs = [a for a in client_schema().ListAttributes() if a.index]

    # Fixup MAC addresses to match the MAC index format.
    match = re.search(mac_addr_re, query_string)
    if match:
      query_string = query_string.replace(":", "").replace("-", "")

    result_set = index.Query(
        indexed_attrs, query_string, limit=(start, max_results))

  return result_set
