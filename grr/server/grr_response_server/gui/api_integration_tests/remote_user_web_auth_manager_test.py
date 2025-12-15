#!/usr/bin/env python
from absl import app
import requests

from grr_response_server import data_store
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import webauth
from grr_response_server.rdfvalues import mig_objects
from grr.test_lib import test_lib


class RemoteUserWebAuthManagerTest(api_integration_test_lib.ApiIntegrationTest):

  def setUp(self):
    super().setUp()
    config_overrider = test_lib.ConfigOverrider({
        "AdminUI.webauth_manager": "RemoteUserWebAuthManager",
        "AdminUI.remote_user_trusted_ips": ["127.0.0.1", "::1"],
    })
    config_overrider.Start()
    self.addCleanup(webauth.InitializeWebAuth)
    self.addCleanup(config_overrider.Stop)
    webauth.InitializeWebAuth()

  def testEnableCustomEmailAddressIsFalse_emailIsNotSet(self):
    headers = {"X-Remote-User": "foo", "X-Remote-Extra-Email": "foo@bar.org"}
    response = requests.get(self.endpoint + "/api/v2/config", headers=headers)
    self.assertEqual(response.status_code, 200)
    proto_user = data_store.REL_DB.ReadGRRUser("foo")
    rdf_user = mig_objects.ToRDFGRRUser(proto_user)
    self.assertEqual(rdf_user.username, "foo")
    self.assertFalse(rdf_user.email)

  def testEnableCustomEmailAddressIsTrue_emailIsSet(self):
    with test_lib.ConfigOverrider({"Email.enable_custom_email_address": True}):
      headers = {"X-Remote-User": "foo", "X-Remote-Extra-Email": "foo@bar.org"}
      response = requests.get(self.endpoint + "/api/v2/config", headers=headers)
      self.assertEqual(response.status_code, 200)
      proto_user = data_store.REL_DB.ReadGRRUser("foo")
      rdf_user = mig_objects.ToRDFGRRUser(proto_user)
      self.assertEqual(rdf_user.username, "foo")
      self.assertEqual(rdf_user.email, "foo@bar.org")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
