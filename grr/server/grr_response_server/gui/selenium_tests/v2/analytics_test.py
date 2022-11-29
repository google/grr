#!/usr/bin/env python
from absl import app
from selenium.webdriver.common import by

from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class AnalyticsTest(gui_test_lib.GRRSeleniumTest):
  """Tests the analytics script."""

  def _GetElementsByTagName(self, tag_name):
    # TODO: GetElement only returns visible elements, so we need
    # to query the visible root element and then manually locate all elements
    # beneath.
    html_el = self.WaitUntil(self.GetElement, "css=html")
    return html_el.find_elements(by.By.TAG_NAME, tag_name)

  def testDoesNotIncludeAnalyticsPerDefault(self):
    self.Open("/v2/")
    scripts = self._GetElementsByTagName("script")
    self.assertGreater(len(scripts), 0)

    ga_scripts = [s for s in scripts if "google" in s.get_attribute("src")]
    self.assertEmpty(ga_scripts)

  def testIncludesAnalyticsScriptIfIdIsConfigured(self):
    with test_lib.ConfigOverrider({"AdminUI.analytics_id": "test_ga_id"}):
      self.Open("/v2/")
      scripts = self._GetElementsByTagName("script")
      ga_scripts = [s for s in scripts if "google" in s.get_attribute("src")]
      self.assertLen(ga_scripts, 1)
      self.assertIn("test_ga_id", ga_scripts[0].get_attribute("src"))


if __name__ == "__main__":
  app.run(test_lib.main)
