#!/usr/bin/env python
"""Keyword indexing on AFF4.

An aff4 keyword index class which associates keywords with names and makes it
possible to search for those names which match all keywords.

"""


from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue


class AFF4KeywordIndex(aff4.AFF4Object):
  """An index linking keywords to names of objects.
  """
  INDEX_PREFIX = "kw_index:"
  INDEX_PREFIX_LEN = len(INDEX_PREFIX)
  INDEX_COLUMN_FORMAT = INDEX_PREFIX + "%s"

  # The lowest and highest legal timestamps.
  FIRST_TIMESTAMP = 0
  LAST_TIMESTAMP = (2**63) - 2  # maxint64 - 1

  def _KeywordToURN(self, keyword):
    return self.urn.Add(keyword)

  def Lookup(self, keywords, **kwargs):
    """Finds objects associated with keywords.

    Find the names related to all keywords.

    Args:
      keywords: A collection of keywords that we are interested in.
      **kwargs: Additional arguments to be passed to the underlying call to
        ReadPostingLists
    Returns:
      A set of potentially relevant names.

    """

    posting_lists = self.ReadPostingLists(keywords, **kwargs)

    results = posting_lists.values()
    relevant_set = results[0]

    for hits in results:
      relevant_set &= hits

      if not relevant_set:
        return relevant_set

    return relevant_set

  def ReadPostingLists(self,
                       keywords,
                       start_time=FIRST_TIMESTAMP,
                       end_time=LAST_TIMESTAMP,
                       last_seen_map=None):
    """Finds all objects associated with any of the keywords.

    Args:
      keywords: A collection of keywords that we are interested in.
      start_time: Only considers keywords added at or after this point in time.
      end_time: Only considers keywords at or before this point in time.
      last_seen_map: If present, is treated as a dict and populated to map pairs
        (keyword, name) to the timestamp of the latest connection found.
    Returns:
      A dict mapping each keyword to a set of relevant names.

    """
    keyword_urns = {self._KeywordToURN(k): k for k in keywords}
    result = {}
    for kw in keywords:
      result[kw] = set()

    for keyword_urn, value in data_store.DB.MultiResolvePrefix(
        keyword_urns.keys(),
        self.INDEX_PREFIX,
        timestamp=(start_time, end_time + 1),
        token=self.token):
      for column, _, ts in value:
        kw = keyword_urns[keyword_urn]
        name = column[self.INDEX_PREFIX_LEN:]
        result[kw].add(name)
        if last_seen_map is not None:
          last_seen_map[(kw, name)] = max(last_seen_map.get((kw, name), -1), ts)

    return result

  def AddKeywordsForName(self,
                         name,
                         keywords,
                         sync=True,
                         timestamp=None,
                         **kwargs):
    """Associates keywords with name.

    Records that keywords are associated with name.

    Args:
      name: A name which should be associated with some keywords.
      keywords: A collection of keywords to associate with name.
      sync: Sync to data store immediately.
      timestamp: timestamp to use for the underlying datastore write
      **kwargs: Additional arguments to pass to the datastore.
    """
    if timestamp is None:
      timestamp = rdfvalue.RDFDatetime().Now().AsMicroSecondsFromEpoch()
    if sync:
      with data_store.DB.GetMutationPool(token=self.token) as mutation_pool:
        for keyword in set(keywords):
          mutation_pool.Set(
              self._KeywordToURN(keyword),
              self.INDEX_COLUMN_FORMAT % name,
              "",
              timestamp=timestamp,
              **kwargs)
    else:
      for keyword in set(keywords):
        data_store.DB.Set(
            self._KeywordToURN(keyword),
            self.INDEX_COLUMN_FORMAT % name,
            "",
            token=self.token,
            sync=False,
            timestamp=timestamp,
            **kwargs)

  def RemoveKeywordsForName(self, name, keywords, sync=True):
    """Removes keywords for a name.

    Args:
      name: A name which should not be associated with some keywords anymore.
      keywords: A collection of keywords.
      sync: Sync to data store immediately.
    """
    if sync:
      with data_store.DB.GetMutationPool(token=self.token) as mutation_pool:
        for keyword in set(keywords):
          mutation_pool.DeleteAttributes(
              self._KeywordToURN(keyword), [self.INDEX_COLUMN_FORMAT % name])
    else:
      for keyword in set(keywords):
        data_store.DB.DeleteAttributes(
            self._KeywordToURN(keyword), [self.INDEX_COLUMN_FORMAT % name],
            token=self.token,
            sync=False)
