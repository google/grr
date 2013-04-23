#!/usr/bin/env python
"""Functions for searching."""
import re

from grr.lib import aff4


def SearchClients(query_string, start=0, max_results=1000, token=None):
  """Take a query string and interpret it as a search, returning clients."""
  match = re.search(r"(C\.[0-9a-f]{16})", query_string)
  if match:
    client_id = match.group(1)
    result_set = [aff4.FACTORY.Open("aff4:/%s" % client_id, token=token)]

  # More complex searches are done through the data_store.Query()
  elif ":" in query_string:
    result_set = QueryClientsWithDataStore(query_string, start=start,
                                           length=max_results, token=token)
  # Default to searching host names through the index which is much faster.
  else:
    client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
    index_urn = client_schema.client_index
    index = aff4.FACTORY.Create(index_urn, "AFF4Index", mode="r",
                                token=token)
    # Make sure we search any indexed value.
    indexed_attrs = []
    for attr in client_schema().ListAttributes():
      if attr.index:
        indexed_attrs.append(attr)
    result_set = index.Query(
        indexed_attrs, query_string.lower(), limit=(start, max_results))

  return result_set


# TODO(user): Deprecate this function. It is too slow to be used. Only allow
#               indexed fields to be queried.
def QueryClientsWithDataStore(query_string, start, length, token=None):
  """Query clients using the data store Query mechanism."""
  for (pattern,
       replacement) in [(r"host:([^\ ]+)", "Host contains '\\1'"),
                        (r"id:([^\ ]+)", "( subject contains '\\1' and "
                         "type = VFSGRRClient )"),
                        (r"version:([^\ ]+)", "Version contains '\\1'"),
                        (r"mac:([^\ ]+)", "MAC contains '\\1'"),
                        (r"user:([^\ ]+)", "Usernames contains '\\1'")]:
    query_string = re.sub(pattern, replacement, query_string)

  root = aff4.FACTORY.Create(aff4.ROOT_URN, "AFF4Volume", "r",
                             token=token)
  return root.Query(query_string, limit=(start, length))
