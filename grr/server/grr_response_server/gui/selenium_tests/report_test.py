#!/usr/bin/env python
from absl import app
from selenium.webdriver.common import keys

from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def AddFakeAuditLog(user=None, router_method_name=None):
  data_store.REL_DB.WriteAPIAuditEntry(
      rdf_objects.APIAuditEntry(
          username=user,
          router_method_name=router_method_name,
      )
  )


class TestDateTimeInput(gui_test_lib.GRRSeleniumTest):
  """Tests datetime-form-directive."""

  def testInputAllowsInvalidText(self):
    # Make "test" user an admin.
    self.CreateAdminUser("test")

    # Open any page that shows the datetime-form-directive.
    self.Open("/legacy#/stats/HuntApprovalsReportPlugin")

    datetime_input = self.WaitUntil(
        self.GetVisibleElement, "css=grr-form-datetime input"
    )
    value = datetime_input.get_attribute("value")
    self.assertRegex(value, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
    self.assertStartsWith(value, "20")

    datetime_input.send_keys(keys.Keys.BACKSPACE)
    self.WaitUntilNot(self.IsTextPresent, value)
    self.assertEqual(value[:-1], datetime_input.get_attribute("value"))


if __name__ == "__main__":
  app.run(test_lib.main)
