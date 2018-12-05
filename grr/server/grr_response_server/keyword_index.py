#!/usr/bin/env python
"""Keyword indexing on AFF4.

An aff4 keyword index class which associates keywords with names and makes it
possible to search for those names which match all keywords.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import itervalues

from grr_response_server import aff4
from grr_response_server import data_store


# TODO(amoser): This class is deprecated, remove at some point.
class AFF4KeywordIndex(aff4.AFF4Object):
  """An index linking keywords to names of objects.
  """
  # The lowest and highest legal timestamps.
  FIRST_TIMESTAMP = 0
  LAST_TIMESTAMP = (2**63) - 2  # maxint64 - 1

  def Lookup(self,
             keywords,
             start_time=FIRST_TIMESTAMP,
             end_time=LAST_TIMESTAMP,
             last_seen_map=None):
    """Finds objects associated with keywords.

    Find the names related to all keywords.

    Args:
      keywords: A collection of keywords that we are interested in.
      start_time: Only considers keywords added at or after this point in time.
      end_time: Only considers keywords at or before this point in time.
      last_seen_map: If present, is treated as a dict and populated to map pairs
        (keyword, name) to the timestamp of the latest connection found.
    Returns:
      A set of potentially relevant names.

    """
    posting_lists = self.ReadPostingLists(
        keywords,
        start_time=start_time,
        end_time=end_time,
        last_seen_map=last_seen_map)

    results = list(itervalues(posting_lists))
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
    return data_store.DB.IndexReadPostingLists(
        self.urn, keywords, start_time, end_time, last_seen_map=last_seen_map)

  def AddKeywordsForName(self, name, keywords):
    """Associates keywords with name.

    Records that keywords are associated with name.

    Args:
      name: A name which should be associated with some keywords.
      keywords: A collection of keywords to associate with name.
    """
    data_store.DB.IndexAddKeywordsForName(self.urn, name, keywords)

  def RemoveKeywordsForName(self, name, keywords):
    """Removes keywords for a name.

    Args:
      name: A name which should not be associated with some keywords anymore.
      keywords: A collection of keywords.
    """
    data_store.DB.IndexRemoveKeywordsForName(self.urn, name, keywords)
