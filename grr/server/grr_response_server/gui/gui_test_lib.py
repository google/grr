#!/usr/bin/env python
"""Helper functionality for gui testing."""

import atexit
import functools
import logging
import os
import threading
import time
from urllib import parse as urlparse

from absl import flags
import portpicker
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common import by
from selenium.webdriver.common import keys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import user_pb2
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import artifact_test_lib as ar_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

_CHROME_DRIVER_PATH = flags.DEFINE_string(
    "chrome_driver_path",
    None,
    "Path to the chrome driver binary. If not set, webdriver "
    "will search on PATH for the binary.",
)

_CHROME_BINARY_PATH = flags.DEFINE_string(
    "chrome_binary_path",
    None,
    "Path to the Chrome binary. If not set, webdriver will search for "
    "Chrome on PATH.",
)

_USE_HEADLESS_CHROME = flags.DEFINE_bool(
    "use_headless_chrome",
    False,
    "If set, run Chrome driver in "
    "headless mode. Useful when running tests in a window-manager-less "
    "environment.",
)

_DISABLE_CHROME_SANDBOXING = flags.DEFINE_bool(
    "disable_chrome_sandboxing",
    False,
    "Whether to disable chrome sandboxing (e.g when running in a Docker "
    "container).",
)


def CreateFileVersion(client_id, path, content=b"", timestamp=None):
  """Add a new version for a file."""
  if timestamp is None:
    timestamp = rdfvalue.RDFDatetime.Now()

  with test_lib.FakeTime(timestamp):
    path_type, components = rdf_objects.ParseCategorizedPath(path)
    client_path = db.ClientPath(client_id, path_type, components)
    vfs_test_lib.CreateFile(client_path, content=content)


def SeleniumAction(f):
  """Decorator to do multiple attempts in case of WebDriverException."""

  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    delay = 0.2
    num_attempts = 15
    cur_attempt = 0
    while True:
      try:
        return f(*args, **kwargs)
      except exceptions.WebDriverException as e:
        logging.warning("Selenium raised %s", utils.SmartUnicode(e))

        cur_attempt += 1
        if cur_attempt == num_attempts:
          raise

        time.sleep(delay)

  return Decorator


class GRRSeleniumTest(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):
  """Baseclass for selenium UI tests."""

  # Default duration (in seconds) for WaitUntil.
  duration = 5

  # Time to wait between polls for WaitUntil.
  sleep_time = 0.2

  # This is the global selenium handle.
  driver = None

  # Base url of the Admin UI
  base_url = None

  @staticmethod
  def _TearDownSelenium():
    """Tear down Selenium session."""
    try:
      if GRRSeleniumTest.driver:
        GRRSeleniumTest.driver.quit()
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(e)

  @staticmethod
  def _SetUpSelenium(port):
    """Set up Selenium session."""
    atexit.register(GRRSeleniumTest._TearDownSelenium)
    GRRSeleniumTest.base_url = "http://localhost:%s" % port

    options = webdriver.ChromeOptions()
    prefs = {
        "profile.content_settings.exceptions.clipboard": {
            f"{GRRSeleniumTest.base_url},*": {
                "setting": 1,
            },
        },
    }
    options.add_experimental_option("prefs", prefs)

    if _CHROME_BINARY_PATH.value:
      options.binary_location = _CHROME_BINARY_PATH.value

    options.add_argument("--disable-notifications")

    if _USE_HEADLESS_CHROME.value:
      options.add_argument("--headless=new")
      options.add_argument("--window-size=1400,1080")

    if _DISABLE_CHROME_SANDBOXING.value:
      options.add_argument("--no-sandbox")

    # pylint: disable=unreachable
    os.environ.pop("http_proxy", None)

    if _CHROME_DRIVER_PATH.value:
      GRRSeleniumTest.driver = webdriver.Chrome(
          service=webdriver.ChromeService(
              executable_path=_CHROME_DRIVER_PATH.value
          ),
          options=options,
      )
    else:
      GRRSeleniumTest.driver = webdriver.Chrome(options=options)

    # pylint: enable=unreachable

  _selenium_set_up_lock = threading.RLock()
  _selenium_set_up_done = False

  @classmethod
  def setUpClass(cls):
    super(GRRSeleniumTest, cls).setUpClass()
    with GRRSeleniumTest._selenium_set_up_lock:
      if not GRRSeleniumTest._selenium_set_up_done:

        port = portpicker.pick_unused_port()
        logging.info("Picked free AdminUI port %d.", port)

        # Start up a server in another thread
        GRRSeleniumTest._server_trd = wsgiapp_testlib.ServerThread(
            port, name="SeleniumServerThread"
        )
        GRRSeleniumTest._server_trd.StartAndWaitUntilServing()
        GRRSeleniumTest._SetUpSelenium(port)

        GRRSeleniumTest._selenium_set_up_done = True

  def InstallACLChecks(self):
    """Installs AccessControlManager and stubs out SendEmail."""
    acrwac = api_call_router_with_approval_checks

    # Clear the cache of the approvals-based router.
    acrwac.ApiCallRouterWithApprovalChecks.ClearCache()

    name = acrwac.ApiCallRouterWithApprovalChecks.__name__
    config_overrider = test_lib.ConfigOverrider({"API.DefaultRouter": name})
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

  def _CheckJavascriptErrors(self):
    errors = self.driver.execute_script(
        "return (() => {const e = window.grrInterceptedJSErrors_ || []; "
        "window.grrInterceptedJSErrors_ = []; return e;})();"
    )

    msgs = []
    for e in errors:
      msg = "[javascript]: %s" % e
      logging.error(msg)
      msgs.append(msg)

    if msgs:
      self.fail(
          "Javascript error encountered during test: %s" % "\n\t".join(msgs)
      )

  def GetHttpErrors(self):
    return self.driver.execute_script(
        "return (() => {const e = window.grrInterceptedHTTPErrors_ || []; "
        "window.grrInterceptedHTTPErrors_ = []; return e;})();"
    )

  def _CheckHttpErrors(self):
    if self.ignore_http_errors:
      return

    msgs = []
    for e in self.GetHttpErrors():
      try:
        msg = e["data"]["traceBack"]
      except (TypeError, KeyError):
        msg = "[http]: {!r}".format(e)

      logging.error(msg)
      msgs.append(msg)

    if msgs:
      self.fail("HTTP request failed during test: %s" % "\n\t".join(msgs))

  def CheckBrowserErrors(self):
    self._CheckJavascriptErrors()
    self._CheckHttpErrors()

  def WaitUntil(self, condition_cb, *args):
    self.CheckBrowserErrors()

    for _ in range(int(self.duration / self.sleep_time)):
      try:
        res = condition_cb(*args)
        if res:
          return res

      # Raise in case of a test-related error (i.e. failing assertion).
      except self.failureException:
        raise
      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=broad-except
        logging.warning("Selenium raised %s", utils.SmartUnicode(e))

      self.CheckBrowserErrors()
      time.sleep(self.sleep_time)

    self.fail(
        "condition %s%s not met, body is: %s"
        % (
            condition_cb.__name__,
            args,
            self.driver.find_element(by.By.TAG_NAME, "body").text,
        )
    )

  def _FindElement(self, selector):
    try:
      selector_type, effective_selector = selector.split("=", 1)
    except ValueError:
      effective_selector = selector
      selector_type = None

    if selector_type == "css":
      return self.driver.find_element(by.By.CSS_SELECTOR, effective_selector)

    elif selector_type == "link":
      links = self.driver.find_element(
          by.By.PARTIAL_LINK_TEXT, effective_selector
      )
      for l in links:
        if l.text.strip() == effective_selector:
          return l
      raise exceptions.NoSuchElementException()

    elif selector_type == "xpath":
      return self.driver.find_element(by.By.XPATH, effective_selector)

    elif selector_type == "id":
      return self.driver.find_element(by.By.ID, effective_selector)

    elif selector_type == "name":
      return self.driver.find_element(by.By.NAME, effective_selector)

    elif selector_type is None:
      if effective_selector.startswith("//"):
        return self.driver.find_element(by.By.XPATH, effective_selector)
      else:
        return self.driver.find_element(by.By.ID, effective_selector)
    else:
      raise ValueError("unknown selector type %s" % selector_type)

  @SeleniumAction
  def Open(self, url):
    # In GRR Selenium tests calling Open() implies page refresh.
    # We make sure that browser/webdriver is not confused by the fact that
    # only the fragment part of the URL (after the '#' symbol) changes.
    # It's important to not confuse WebDriver since it tends to get stuck
    # when confused.
    self.driver.get("data:.")
    self.driver.get(self.base_url + url)

    # Wait until page has been loaded.
    self.WaitUntil(self.GetElement, "xpath=//body")

  @SeleniumAction
  def WaitUntilNot(self, condition_cb, *args):

    def _Func(*args):
      return not condition_cb(*args)

    _Func.__name__ = f"<Not {condition_cb.__name__}>"
    return self.WaitUntil(_Func, *args)

  def IsElementPresent(self, target):
    try:
      self._FindElement(target)
      return True
    except exceptions.NoSuchElementException:
      return False

  def GetCurrentUrlPath(self):
    url = urlparse.urlparse(self.driver.current_url)

    result = url.path
    if url.fragment:
      result += "#" + url.fragment

    return result

  def GetCurrentUrlQuery(self) -> str:
    url = urlparse.urlparse(self.driver.current_url)

    return url.query

  def GetElement(self, target):
    try:
      return self._FindElement(target)
    except exceptions.NoSuchElementException:
      return None

  def GetVisibleElement(self, target):
    try:
      element = self._FindElement(target)
      if element.is_displayed():
        return element
    except exceptions.NoSuchElementException:
      pass

    return None

  def IsTextPresent(self, text):
    body = self.driver.find_element(by.By.TAG_NAME, "body").text
    return utils.SmartUnicode(text) in body

  def GetValue(self, target):
    return self.GetAttribute(target, "value")

  def GetAttribute(self, target, attribute):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return element.get_attribute(attribute)

  def GetJavaScriptValue(self, js_expression):
    return self.driver.execute_script(js_expression)

  def _WaitForAjaxCompleted(self):
    self.WaitUntilEqual(
        [],
        self.GetJavaScriptValue,
        "return (window.$ && $('body') && $('body').injector && "
        "$('body').injector().get('$http').pendingRequests) || []",
    )

  @SeleniumAction
  def Type(self, target, text, end_with_enter=False):
    element = self.WaitUntil(self.GetVisibleElement, target)
    element.clear()
    element.send_keys(text)
    if end_with_enter:
      element.send_keys(keys.Keys.ENTER)

    # We experienced that Selenium sometimes swallows the last character of the
    # text sent. Raising an exception here will just retry in that case.
    if not end_with_enter:
      actual = self.GetValue(target)
      if text != actual:
        raise exceptions.WebDriverException(
            f"Send_keys did not work correctly: Got '{actual}' but expected "
            + f"'{text}'."
        )

  @SeleniumAction
  def Click(self, target):
    # Selenium clicks elements by obtaining their position and then issuing a
    # click action in the middle of this area. This may lead to misclicks when
    # elements are moving. Make sure that they are stationary before issuing
    # the click action (specifically, using the bootstrap "fade" class that
    # slides dialogs in is highly discouraged in combination with .Click()).

    # Since Selenium does not know when the page is ready after AJAX calls, we
    # need to wait for AJAX completion here to be sure that all event handlers
    # are attached to their respective DOM elements.
    self._WaitForAjaxCompleted()

    element = self.WaitUntil(self.GetVisibleElement, target)

    try:
      element.click()
    except exceptions.ElementNotInteractableException:
      self.driver.execute_script("arguments[0].scrollIntoView();", element)
      element.click()

  def WaitUntilEqual(self, target, condition_cb, *args):
    condition_value = None
    for _ in range(int(self.duration / self.sleep_time)):
      try:
        condition_value = condition_cb(*args)
        if condition_value == target:
          return True

      # Raise in case of a test-related error (i.e. failing assertion).
      except self.failureException:
        raise
      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=broad-except
        logging.warning("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    self.fail(
        "condition %s(%s) not met (expected=%r, got_last_time=%r)"
        % (condition_cb, args, target, condition_value)
    )

  def setUp(self):
    super().setUp()

    # Used by CheckHttpErrors
    self.ignore_http_errors = False

    self.test_username = "gui_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.test_username)

    # Make the user use the advanced gui so we can test it.
    data_store.REL_DB.WriteGRRUser(
        self.test_username, ui_mode=user_pb2.GUISettings.UIMode.DEBUG
    )

    artifact_patcher = ar_test_lib.PatchDatastoreOnlyArtifactRegistry()
    artifact_patcher.start()
    self.addCleanup(artifact_patcher.stop)

    self.InstallACLChecks()

    if _USE_HEADLESS_CHROME.value:
      self.driver.execute_cdp_cmd(
          "Page.setDownloadBehavior",
          {"behavior": "allow", "downloadPath": self.temp_dir},
      )

  def tearDown(self):
    self.CheckBrowserErrors()
    super().tearDown()


class GRRSeleniumHuntTest(hunt_test_lib.StandardHuntTestMixin, GRRSeleniumTest):
  """Common functionality for hunt gui tests."""

  pass
