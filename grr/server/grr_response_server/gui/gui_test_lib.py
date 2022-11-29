#!/usr/bin/env python
"""Helper functionality for gui testing."""

import atexit
import binascii
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
from selenium.webdriver.common import action_chains
from selenium.webdriver.common import keys
from selenium.webdriver.support import select

from grr_response_core.lib import package
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import tests_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import foreman_rules
from grr_response_server import output_plugin
from grr_response_server.databases import db
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib as ar_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

_CHROME_DRIVER_PATH = flags.DEFINE_string(
    "chrome_driver_path", None,
    "Path to the chrome driver binary. If not set, webdriver "
    "will search on PATH for the binary.")

_CHROME_BINARY_PATH = flags.DEFINE_string(
    "chrome_binary_path", None,
    "Path to the Chrome binary. If not set, webdriver will search for "
    "Chrome on PATH.")

_USE_HEADLESS_CHROME = flags.DEFINE_bool(
    "use_headless_chrome", False, "If set, run Chrome driver in "
    "headless mode. Useful when running tests in a window-manager-less "
    "environment.")

_DISABLE_CHROME_SANDBOXING = flags.DEFINE_bool(
    "disable_chrome_sandboxing", False,
    "Whether to disable chrome sandboxing (e.g when running in a Docker "
    "container).")

# A increasing sequence of times.
TIME_0 = test_lib.FIXED_TIME
TIME_1 = TIME_0 + rdfvalue.Duration.From(1, rdfvalue.DAYS)
TIME_2 = TIME_1 + rdfvalue.Duration.From(1, rdfvalue.DAYS)


def DateString(t):
  return t.Format("%Y-%m-%d")


def DateTimeString(t):
  return t.Format("%Y-%m-%d %H:%M:%S")


def CreateFileVersions(client_id):
  """Add new versions for a file."""
  content_1 = b"Hello World"
  content_2 = b"Goodbye World"
  # This file already exists in the fixture at TIME_0, we write a
  # later version.
  CreateFileVersion(
      client_id, "fs/os/c/Downloads/a.txt", content_1, timestamp=TIME_1)
  CreateFileVersion(
      client_id, "fs/os/c/Downloads/a.txt", content_2, timestamp=TIME_2)

  return (content_1, content_2)


def CreateFileVersion(client_id, path, content=b"", timestamp=None):
  """Add a new version for a file."""
  if timestamp is None:
    timestamp = rdfvalue.RDFDatetime.Now()

  with test_lib.FakeTime(timestamp):
    path_type, components = rdf_objects.ParseCategorizedPath(path)
    client_path = db.ClientPath(client_id, path_type, components)
    vfs_test_lib.CreateFile(client_path, content=content)


def CreateFolder(client_id, path, timestamp):
  """Creates a VFS folder."""
  with test_lib.FakeTime(timestamp):
    path_type, components = rdf_objects.ParseCategorizedPath(path)

    path_info = rdf_objects.PathInfo()
    path_info.path_type = path_type
    path_info.components = components
    path_info.directory = True

    data_store.REL_DB.WritePathInfos(client_id, [path_info])


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


class DisabledHttpErrorChecksContextManager(object):
  """Context manager to be returned by test's DisabledHttpErrorChecks call."""

  def __init__(self, test):
    self.test = test

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.test.ignore_http_errors = False
    self.test.driver.execute_script("window.grrInterceptedHTTPErrors_ = []")


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
    GRRSeleniumTest.base_url = ("http://localhost:%s" % port)

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
      options.add_argument("--headless")
      options.add_argument("--window-size=1400,1080")

    if _DISABLE_CHROME_SANDBOXING.value:
      options.add_argument("--no-sandbox")

    # pylint: disable=unreachable
    os.environ.pop("http_proxy", None)

    if _CHROME_DRIVER_PATH.value:
      GRRSeleniumTest.driver = webdriver.Chrome(
          _CHROME_DRIVER_PATH.value, chrome_options=options)
    else:
      GRRSeleniumTest.driver = webdriver.Chrome(chrome_options=options)

    # TODO(user): Hack! This is needed to allow downloads in headless mode.
    # Remove this code when upstream Python ChromeDriver implementation has
    # send_command implemented.
    #
    # See
    # https://stackoverflow.com/questions/45631715/downloading-with-chrome-headless-and-selenium
    # and the code in setUp().
    # pylint: disable=protected-access
    GRRSeleniumTest.driver.command_executor._commands["send_command"] = (
        "POST", "/session/$sessionId/chromium/send_command")
    # pylint: enable=protected-access
    # pylint: enable=unreachable

  _selenium_set_up_lock = threading.RLock()
  _selenium_set_up_done = False

  # Cached jQuery source to be injected into pages on Open (for selectors
  # support).
  _jquery_source = None

  @classmethod
  def setUpClass(cls):
    super(GRRSeleniumTest, cls).setUpClass()
    with GRRSeleniumTest._selenium_set_up_lock:
      if not GRRSeleniumTest._selenium_set_up_done:

        port = portpicker.pick_unused_port()
        logging.info("Picked free AdminUI port %d.", port)

        # Start up a server in another thread
        GRRSeleniumTest._server_trd = wsgiapp_testlib.ServerThread(
            port, name="SeleniumServerThread")
        GRRSeleniumTest._server_trd.StartAndWaitUntilServing()
        GRRSeleniumTest._SetUpSelenium(port)

        jquery_path = package.ResourcePath(
            "grr-response-test",
            "grr_response_test/test_data/jquery_3.1.0.min.js")
        with open(jquery_path, mode="r", encoding="utf-8") as fd:
          GRRSeleniumTest._jquery_source = fd.read()

        GRRSeleniumTest._selenium_set_up_done = True

  def InstallACLChecks(self):
    """Installs AccessControlManager and stubs out SendEmail."""
    acrwac = api_call_router_with_approval_checks

    # Clear the cache of the approvals-based router.
    acrwac.ApiCallRouterWithApprovalChecks.ClearCache()

    name = compatibility.GetName(acrwac.ApiCallRouterWithApprovalChecks)
    config_overrider = test_lib.ConfigOverrider({"API.DefaultRouter": name})
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

  def _CheckJavascriptErrors(self):
    errors = self.driver.execute_script(
        "return (() => {const e = window.grrInterceptedJSErrors_ || []; "
        "window.grrInterceptedJSErrors_ = []; return e;})();")

    msgs = []
    for e in errors:
      msg = "[javascript]: %s" % e
      logging.error(msg)
      msgs.append(msg)

    if msgs:
      self.fail("Javascript error encountered during test: %s" %
                "\n\t".join(msgs))

  def DisableHttpErrorChecks(self):
    self.ignore_http_errors = True
    return DisabledHttpErrorChecksContextManager(self)

  def GetHttpErrors(self):
    return self.driver.execute_script(
        "return (() => {const e = window.grrInterceptedHTTPErrors_ || []; "
        "window.grrInterceptedHTTPErrors_ = []; return e;})();")

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

    self.fail("condition %s%s not met, body is: %s" %
              (condition_cb.__name__, args,
               self.driver.find_element_by_tag_name("body").text))

  def _FindElements(self, selector):
    selector_type, effective_selector = selector.split("=", 1)
    if selector_type != "css":
      raise ValueError(
          "Only CSS selector is supported for querying multiple elements.")

    elems = self.driver.execute_script(
        "return $(\"" + effective_selector.replace("\"", "\\\"") + "\");")
    return [e for e in elems if e.is_displayed()]

  def _FindElement(self, selector):
    try:
      selector_type, effective_selector = selector.split("=", 1)
    except ValueError:
      effective_selector = selector
      selector_type = None

    if selector_type == "css":
      elems = self.driver.execute_script(
          "return $(\"" + effective_selector.replace("\"", "\\\"") + "\");")
      elems = [e for e in elems if e.is_displayed()]

      if not elems:
        raise exceptions.NoSuchElementException()
      else:
        return elems[0]

    elif selector_type == "link":
      links = self.driver.find_elements_by_partial_link_text(effective_selector)
      for l in links:
        if l.text.strip() == effective_selector:
          return l
      raise exceptions.NoSuchElementException()

    elif selector_type == "xpath":
      return self.driver.find_element_by_xpath(effective_selector)

    elif selector_type == "id":
      return self.driver.find_element_by_id(effective_selector)

    elif selector_type == "name":
      return self.driver.find_element_by_name(effective_selector)

    elif selector_type is None:
      if effective_selector.startswith("//"):
        return self.driver.find_element_by_xpath(effective_selector)
      else:
        return self.driver.find_element_by_id(effective_selector)
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

    jquery_present = self.driver.execute_script(
        "return window.$ !== undefined;")
    if not jquery_present:
      self.driver.execute_script(GRRSeleniumTest._jquery_source)

  @SeleniumAction
  def Refresh(self):
    self.driver.refresh()

  @SeleniumAction
  def Back(self):
    self.driver.back()

  @SeleniumAction
  def Forward(self):
    self.driver.forward()

  def WaitUntilNot(self, condition_cb, *args):

    def _Func(*args):
      return not condition_cb(*args)

    _Func.__name__ = f"<Not {condition_cb.__name__}>"
    return self.WaitUntil(_Func, *args)

  def GetPageTitle(self):
    return self.driver.title

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
    return self.AllTextsPresent([text])

  def AllTextsPresent(self, texts):
    body = self.driver.find_element_by_tag_name("body").text
    for text in texts:
      if utils.SmartUnicode(text) not in body:
        return False
    return True

  def IsVisible(self, target):
    element = self.GetElement(target)
    return element and element.is_displayed()

  def GetText(self, target):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return element.text.strip()

  def GetValue(self, target):
    return self.GetAttribute(target, "value")

  def GetAttribute(self, target, attribute):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return element.get_attribute(attribute)

  def GetClipboard(self):
    return self.GetJavaScriptValue(
        "return await navigator.clipboard.readText();")

  def IsUserNotificationPresent(self, contains_string):
    self.Click("css=#notification_button")
    self.WaitUntil(self.IsElementPresent, "css=grr-user-notification-dialog")
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=grr-user-notification-dialog:contains('Loading...')")

    notifications_text = self.GetText("css=grr-user-notification-dialog")
    self.Click("css=grr-user-notification-dialog button:contains('Close')")

    return contains_string in notifications_text

  def GetJavaScriptValue(self, js_expression):
    return self.driver.execute_script(js_expression)

  def _WaitForAjaxCompleted(self):
    self.WaitUntilEqual(
        [], self.GetJavaScriptValue,
        "return (window.$ && $('body') && $('body').injector && "
        "$('body').injector().get('$http').pendingRequests) || []")

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
            f"Send_keys did not work correctly: Got '{actual}' but expected " +
            f"'{text}'.")

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

  @SeleniumAction
  def ScrollIntoView(self, target):
    """Scrolls any container to get the target into view."""
    self._WaitForAjaxCompleted()
    element = self.WaitUntil(self.GetVisibleElement, target)
    self.driver.execute_script("arguments[0].scrollIntoView();", element)

  @SeleniumAction
  def MoveMouseTo(self, target):
    self._WaitForAjaxCompleted()
    element = self.WaitUntil(self.GetVisibleElement, target)
    action_chains.ActionChains(self.driver).move_to_element(element).perform()

  @SeleniumAction
  def ScrollToBottom(self):
    """Scrolls the main window scrollbar to the bottom.

    This might not always bring the desired element into the view, e.g.
    if the container that requires to be scrolled is not the window, but an
    element on the page. Use ScrollIntoView() in this case.
    """
    self.driver.execute_script(
        "window.scrollTo(0, document.body.scrollHeight);")

  @SeleniumAction
  def DoubleClick(self, target):
    # Selenium clicks elements by obtaining their position and then issuing a
    # click action in the middle of this area. This may lead to misclicks when
    # elements are moving. Make sure that they are stationary before issuing
    # the click action (specifically, using the bootstrap "fade" class that
    # slides dialogs in is highly discouraged in combination with
    # .DoubleClick()).

    # Since Selenium does not know when the page is ready after AJAX calls, we
    # need to wait for AJAX completion here to be sure that all event handlers
    # are attached to their respective DOM elements.
    self._WaitForAjaxCompleted()

    element = self.WaitUntil(self.GetVisibleElement, target)
    action_chains.ActionChains(self.driver).double_click(element).perform()

  @SeleniumAction
  def Select(self, target, label):
    element = self.WaitUntil(self.GetVisibleElement, target)
    select.Select(element).select_by_visible_text(label)

  def GetSelectedLabel(self, target):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return select.Select(element).first_selected_option.text.strip()

  def MatSelect(self, target, label):
    """Selects the option that displays text matching the argument.

    Args:
      target: CSS selector for the mat-select element.
      label: Text representation for the option to be selected.

    Raises:
      ValueError: An invalid selector was provided - must be CSS.
    """
    selector_type, effective_selector = target.split("=", 1)
    if selector_type != "css":
      raise ValueError("Only CSS selector is supported for material select.")
    self.WaitUntil(self.GetVisibleElement, target)
    self.driver.execute_script(f"$('{effective_selector}').click()")
    self.Click(f"css=.mat-option-text:contains('{label}')")

  def IsChecked(self, target):
    return self.WaitUntil(self.GetVisibleElement, target).is_selected()

  def GetCssCount(self, target):
    if not target.startswith("css="):
      raise ValueError("invalid target for GetCssCount: " + target)

    return len(self._FindElements(target))

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

    self.fail("condition %s(%s) not met (expected=%r, got_last_time=%r)" %
              (condition_cb, args, target, condition_value))

  def WaitUntilContains(self, target, condition_cb, *args):
    data = ""
    target = utils.SmartUnicode(target)

    for _ in range(int(self.duration / self.sleep_time)):
      try:
        data = condition_cb(*args)
        if target in data:
          return True

      # Raise in case of a test-related error (i.e. failing assertion).
      except self.failureException:
        raise
      # The element might not exist yet and selenium could raise here.
      except Exception as e:  # pylint: disable=broad-except
        logging.warning("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    self.fail("condition not met. got: {!r}, does not contain: {!r}".format(
        data, target))

  def setUp(self):
    super().setUp()

    # Used by CheckHttpErrors
    self.ignore_http_errors = False

    self.test_username = u"gui_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.test_username)

    # Make the user use the advanced gui so we can test it.
    data_store.REL_DB.WriteGRRUser(
        self.test_username, ui_mode=api_user.GUISettings.UIMode.ADVANCED)

    artifact_patcher = ar_test_lib.PatchDatastoreOnlyArtifactRegistry()
    artifact_patcher.start()
    self.addCleanup(artifact_patcher.stop)

    self.InstallACLChecks()

    if _USE_HEADLESS_CHROME.value:
      params = {
          "cmd": "Page.setDownloadBehavior",
          "params": {
              "behavior": "allow",
              "downloadPath": self.temp_dir
          }
      }
      result = self.driver.execute("send_command", params)
      if result["status"] != 0:
        raise RuntimeError("can't set Page.setDownloadBehavior: %s" % result)

  def tearDown(self):
    self.CheckBrowserErrors()
    super().tearDown()

  def WaitForNotification(self, username):
    sleep_time = 0.2
    iterations = 50
    for _ in range(iterations):
      try:
        pending_notifications = data_store.REL_DB.ReadUserNotifications(
            username, state=rdf_objects.UserNotification.State.STATE_PENDING)
        if pending_notifications:
          return
      except IOError:
        pass
      time.sleep(sleep_time)
    self.fail("Notification for user %s never sent." % username)


class GRRSeleniumHuntTest(hunt_test_lib.StandardHuntTestMixin, GRRSeleniumTest):
  """Common functionality for hunt gui tests."""

  def _CreateForemanClientRuleSet(self):
    return foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="CLIENT_NAME", attribute_regex="GRR"))
    ])

  def _CreateHuntWithDownloadedFile(self):
    hunt = self.CreateSampleHunt(
        path=os.path.join(self.base_path, "test.plist"), client_count=1)

    self.RunHunt(
        client_ids=self.client_ids,
        client_mock=action_mocks.FileFinderClientMock())

    return hunt

  def CheckState(self, state):
    self.WaitUntil(self.IsElementPresent, "css=div[state=\"%s\"]" % state)

  def CreateSampleHunt(self,
                       path=None,
                       stopped=False,
                       output_plugins=None,
                       client_limit=0,
                       client_count=10,
                       creator=None):
    self.client_ids = self.SetupClients(client_count)

    self.hunt_urn = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=compatibility.GetName(transfer.GetFile)),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path=path or "/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS,
            )),
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=output_plugins or [],
        client_rate=0,
        client_limit=client_limit,
        creator=creator or self.test_username,
        paused=stopped)

    return self.hunt_urn

  def CreateGenericHuntWithCollection(self, values=None):
    self.client_ids = self.SetupClients(1)

    CreateFileVersion(self.client_ids[0], "fs/os/c/bin/bash")

    if values is None:
      values = [
          rdfvalue.RDFURN("aff4:/sample/1"),
          rdfvalue.RDFURN("aff4:/%s/fs/os/c/bin/bash" % self.client_ids[0]),
          rdfvalue.RDFURN("aff4:/sample/3")
      ]

    hunt_urn = self.StartHunt(
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[],
        creator=self.test_username)

    self.AddResultsToHunt(hunt_urn, self.client_ids[0], values)

    return hunt_urn, self.client_ids[0]


class SearchClientTestBase(hunt_test_lib.StandardHuntTestMixin,
                           GRRSeleniumTest):

  def CreateSampleHunt(self, description, creator=None):
    return self.StartHunt(description=description, paused=True, creator=creator)


class RecursiveTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.RecursiveTestFlowArgs


class RecursiveTestFlow(flow_base.FlowBase):
  """A test flow which starts some subflows."""
  args_type = RecursiveTestFlowArgs

  # If a flow doesn't have a category, it can't be started/terminated by a
  # non-supervisor user when FullAccessControlManager is used.
  category = "/Test/"

  def Start(self):
    if self.args.depth < 2:
      for i in range(2):
        self.Log("Subflow call %d", i)
        self.CallFlow(
            compatibility.GetName(self.__class__),
            depth=self.args.depth + 1,
            next_state="End")


class FlowWithOneLogStatement(flow_base.FlowBase):
  """Flow that logs a single statement."""

  def Start(self):
    self.Log("I do log.")


class FlowWithOneStatEntryResult(flow_base.FlowBase):
  """Test flow that calls SendReply once with a StatEntry value."""

  def Start(self):
    self.SendReply(
        rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path="/some/unique/path",
                pathtype=rdf_paths.PathSpec.PathType.OS)))


class FlowWithOneNetworkConnectionResult(flow_base.FlowBase):
  """Test flow that calls SendReply once with a NetworkConnection value."""

  def Start(self):
    self.SendReply(rdf_client_network.NetworkConnection(pid=42))


class FlowWithOneHashEntryResult(flow_base.FlowBase):
  """Test flow that calls SendReply once with a HashEntry value."""

  def Start(self):
    hash_result = rdf_crypto.Hash(
        sha256=binascii.unhexlify(
            "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"),
        sha1=binascii.unhexlify("6dd6bee591dfcb6d75eb705405302c3eab65e21a"),
        md5=binascii.unhexlify("8b0a15eefe63fd41f8dc9dee01c5cf9a"))
    self.SendReply(hash_result)


class DummyOutputPlugin(output_plugin.OutputPlugin):
  """Output plugin that does nothing."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, state, responses):
    pass
