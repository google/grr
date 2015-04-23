#!/usr/bin/env python
"""Keyword indexing on AFF4.

An aff4 keyword index class which associates keywords with names and makes it
possible to search for those names which match all keywords.

"""



from grr.lib import aff4
from grr.lib import data_store


class AFF4KeywordIndex(aff4.AFF4Object):
  """An index linking keywords to names of objects.
  """
  INDEX_PREFIX = "kw_index:"
  INDEX_PREFIX_LEN = len(INDEX_PREFIX)
  INDEX_COLUMN_FORMAT = INDEX_PREFIX + "%s"
  INDEX_COLUMN_REGEXP = INDEX_PREFIX + ".*"

  # The lowest and highest legal timestamps.
  FIRST_TIMESTAMP = 0
  LAST_TIMESTAMP = (2 ** 63) - 2  # maxint64 - 1

  def _KeywordToURN(self, keyword):
    return self.urn.Add(keyword)

  def Lookup(self, keywords, start_time=FIRST_TIMESTAMP,
             end_time=LAST_TIMESTAMP):
    """Finds objects associated with keywords.

    Find the names related to all keywords.

    Args:
      keywords: A collection of keywords that we are interested in.
      start_time: Only considers keywords added at or after this point in time.
      end_time: Only considers keywords at or before this point in time.
    Returns:
      A set of potentially relevant names.

    """

    keyword_urns = map(self._KeywordToURN, keywords)
    relevant_set = None
    keywords_found = 0

    for _, value in data_store.DB.MultiResolveRegex(
        keyword_urns, self.INDEX_COLUMN_REGEXP,
        timestamp=(start_time, end_time+1), token=self.token):
      kw_relevant = set()
      for column, _, _ in value:
        kw_relevant.add(column[self.INDEX_PREFIX_LEN:])

      if relevant_set is None:
        relevant_set = kw_relevant
      else:
        relevant_set &= kw_relevant

      if not relevant_set:
        return set()
      keywords_found += 1

    if keywords_found < len(keywords):
      return set()

    return relevant_set

  def AddKeywordsForName(self, name, keywords, sync=True, **kwargs):
    """Associates keywords with name.

    Records that keywords are associated with name.

    Args:
      name: A name which should be associated with some keywords.
      keywords: A collection of keywords to associate with name.
      **kwargs: Additional arguments to pass to the datastore.
    """
    for keyword in set(keywords):
      data_store.DB.Set(
          self._KeywordToURN(keyword),
          self.INDEX_COLUMN_FORMAT % name, "",
          token=self.token, sync=False, **kwargs)
    if sync:
      data_store.DB.Flush()
