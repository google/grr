#!/usr/bin/env python
"""This modules contains tests for Angular components."""



from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class CollectionTableDirectiveTest(test_lib.GRRSeleniumTest):
  """Test for angular collection table.

  NOTE: this class uses CollectionTableTestRenderer defined in
  angular_components_testonly.py.
  """

  def CreateCollectionWithMessages(self, messages):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create("aff4:/tmp/collection",
                               aff4_type="RDFValueCollection",
                               mode="w", token=self.token) as fd:
        for message in messages:
          fd.Add(rdfvalue.FlowLog(log_message=message))

  def CreateCollection(self, num_items):
    messages = []
    for i in range(num_items):
      messages.append("Message %d" % i)
    self.CreateCollectionWithMessages(messages)

  def testShowsEmptyListWhenCollectionIsNotFound(self):
    self.Open("/#main=CollectionTableTestRenderer")
    self.WaitUntil(self.IsTextPresent, "No entries")

  def testPagingIsDisabledWhenNotEnoughElements(self):
    self.CreateCollection(5)

    self.Open("/#main=CollectionTableTestRenderer")
    for i in range(5):
      self.WaitUntil(self.IsTextPresent, "Message %d" % i)

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-collection-table li:contains('Prev').disabled")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-collection-table li:contains('Next').disabled")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-collection-table li:contains('1').disabled")

  def testPagingWorksCorrectlyFor2Pages(self):
    self.CreateCollection(5 * 2)

    def CheckThatPrevAndOneAreDisabled():
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('Prev').disabled")
      self.WaitUntil(
          self.IsElementPresent,
          "css=grr-collection-table li:contains('Next'):not(.disabled)")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('1').disabled")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('2'):not(.disabled)")

    def CheckThatNextAndTwoAreDisabled():
      self.WaitUntil(
          self.IsElementPresent,
          "css=grr-collection-table li:contains('Prev'):not(.disabled)")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('Next').disabled")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('1'):not(.disabled)")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-collection-table li:contains('2').disabled")

    def CheckFirstFiveMessagesAreVisible():
      for i in range(5):
        self.WaitUntil(self.IsTextPresent, "Message %d" % i)
        for i in range(5, 10):
          self.WaitUntilNot(self.IsTextPresent, "Message %d" % i)

    def CheckLastFiveMessageAreVisible():
      for i in range(5, 10):
        self.WaitUntil(self.IsTextPresent, "Message %d" % i)
        for i in range(5):
          self.WaitUntilNot(self.IsTextPresent, "Message %d" % i)

    self.Open("/#main=CollectionTableTestRenderer")
    CheckFirstFiveMessagesAreVisible()
    CheckThatPrevAndOneAreDisabled()

    self.Click("css=grr-collection-table a:contains('Next')")
    CheckLastFiveMessageAreVisible()
    CheckThatNextAndTwoAreDisabled()

    self.Click("css=grr-collection-table a:contains('Prev')")
    CheckFirstFiveMessagesAreVisible()
    CheckThatPrevAndOneAreDisabled()

    self.Click("css=grr-collection-table a:contains('2')")
    CheckLastFiveMessageAreVisible()
    CheckThatNextAndTwoAreDisabled()

    self.Click("css=grr-collection-table a:contains('1')")
    CheckFirstFiveMessagesAreVisible()
    CheckThatPrevAndOneAreDisabled()

  def testPagingWorksCorrectlyFor15Pages(self):
    self.CreateCollection(5 * 15)
    self.Open("/#main=CollectionTableTestRenderer")

    for i in range(15):
      self.Click("css=grr-collection-table a:contains('%d')" % (i + 1))

      for j in range(i * 5, i * 5 + 5):
        self.WaitUntil(self.IsTextPresent, "Message %d" % j)
      if i > 0:
        self.WaitUntilNot(self.IsTextPresent, "Message %d" % (i * 5 - 1))
      if i < 14:
        self.WaitUntilNot(self.IsTextPresent, "Message %d" % (i * 5 + 6))

  def testFilterWorksCorrectlyFor5Elements(self):
    self.CreateCollectionWithMessages(
        ["some1", "other1", "other2", "other3", "some2"])
    self.Open("/#main=CollectionTableTestRenderer")

    self.WaitUntil(self.IsTextPresent, "some1")
    self.WaitUntil(self.IsTextPresent, "some2")
    self.WaitUntil(self.IsTextPresent, "other1")
    self.WaitUntil(self.IsTextPresent, "other2")
    self.WaitUntil(self.IsTextPresent, "other3")
    self.WaitUntilNot(self.IsTextPresent, "Filtered by")

    self.Type("css=grr-collection-table input.search-query",
              "some")
    self.Click("css=grr-collection-table button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, "some1")
    self.WaitUntil(self.IsTextPresent, "some2")
    self.WaitUntilNot(self.IsTextPresent, "other1")
    self.WaitUntilNot(self.IsTextPresent, "other2")
    self.WaitUntilNot(self.IsTextPresent, "other3")
    self.WaitUntil(self.IsTextPresent, "Filtered by: some")

    self.Type("css=grr-collection-table input.search-query", "")
    self.Click("css=grr-collection-table button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, "some1")
    self.WaitUntil(self.IsTextPresent, "some2")
    self.WaitUntil(self.IsTextPresent, "other1")
    self.WaitUntil(self.IsTextPresent, "other2")
    self.WaitUntil(self.IsTextPresent, "other3")
    self.WaitUntilNot(self.IsTextPresent, "Filtered by")

  def testFilterShowsFetchMoreButtonForMoreThanOnePageOfFilteredResults(self):
    self.CreateCollectionWithMessages(
        ["some1", "some2", "some3", "some4", "some5", "some6",
         "other1", "other2", "other3", "other4"])
    self.Open("/#main=CollectionTableTestRenderer")

    self.Type("css=grr-collection-table input.search-query",
              "some")
    self.Click("css=grr-collection-table button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, "some1")
    self.WaitUntil(self.IsTextPresent, "some5")
    self.WaitUntilNot(self.IsTextPresent, "some6")

    self.Click("css=grr-collection-table button:contains('Fetch More')")
    self.WaitUntil(self.IsTextPresent, "some6")

  def testFetchAllButtonFetchesAllFilteredResults(self):
    messages = []
    for i in range(20):
      messages.append("some%d" % i)
    for i in range(100):
      messages.append("other%d" % i)

    self.CreateCollectionWithMessages(messages)
    self.Open("/#main=CollectionTableTestRenderer")

    self.Type("css=grr-collection-table input.search-query",
              "some")
    self.Click("css=grr-collection-table button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, "some0")
    self.WaitUntil(self.IsTextPresent, "some4")
    self.WaitUntilNot(self.IsTextPresent, "some5")

    self.Click("css=grr-collection-table button:contains('Fetch More')")
    self.WaitUntil(self.IsTextPresent, "some5")
    self.WaitUntil(self.IsTextPresent, "some9")
    self.WaitUntilNot(self.IsTextPresent, "some10")

    self.Click("css=grr-collection-table button:contains('Fetch More') ~ "
               "button[data-toggle=dropdown]")
    self.Click("css=grr-collection-table a:contains('Fetch All')")
    self.WaitUntil(self.IsTextPresent, "some10")
    self.WaitUntil(self.IsTextPresent, "some19")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
