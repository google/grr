#!/usr/bin/env python
"""Helper functionality for gui testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import atexit
import functools
import logging
import os
import threading
import time


from builtins import range  # pylint: disable=redefined-builtin
from future.moves.urllib import parse as urlparse
import portpicker
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common import action_chains
from selenium.webdriver.common import keys
from selenium.webdriver.support import select

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import tests_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import flow_base
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import output_plugin
from grr_response_server.aff4_objects import standard as aff4_standard
from grr_response_server.aff4_objects import users
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib as ar_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

flags.DEFINE_string(
    "chrome_driver_path", None,
    "Path to the chrome driver binary. If not set, webdriver "
    "will search on PATH for the binary.")

flags.DEFINE_bool(
    "use_headless_chrome", False, "If set, run Chrome driver in "
    "headless mode. Useful when running tests in a window-manager-less "
    "environment.")

flags.DEFINE_bool(
    "disable_chrome_sandboxing", False,
    "Whether to disable chrome sandboxing (e.g when running in a Docker "
    "container).")

# A increasing sequence of times.
TIME_0 = test_lib.FIXED_TIME
TIME_1 = TIME_0 + rdfvalue.Duration("1d")
TIME_2 = TIME_1 + rdfvalue.Duration("1d")


def DateString(t):
  return t.Format("%Y-%m-%d")


def DateTimeString(t):
  return t.Format("%Y-%m-%d %H:%M:%S")


def CreateFileVersions(client_id, token):
  """Add new versions for a file."""
  content_1 = b"Hello World"
  content_2 = b"Goodbye World"
  # This file already exists in the fixture at TIME_0, we write a
  # later version.
  CreateFileVersion(
      client_id,
      "fs/os/c/Downloads/a.txt",
      content_1,
      timestamp=TIME_1,
      token=token)
  CreateFileVersion(
      client_id,
      "fs/os/c/Downloads/a.txt",
      content_2,
      timestamp=TIME_2,
      token=token)

  return (content_1, content_2)


def CreateFileVersion(client_id, path, content=b"", timestamp=None, token=None):
  """Add a new version for a file."""
  if timestamp is None:
    timestamp = rdfvalue.RDFDatetime.Now()

  with test_lib.FakeTime(timestamp):
    path_type, components = rdf_objects.ParseCategorizedPath(path)
    client_path = db.ClientPath(client_id.Basename(), path_type, components)
    vfs_test_lib.CreateFile(client_path, content=content, token=token)


def CreateFolder(client_id, path, timestamp, token=None):
  """Creates a VFS folder."""
  with test_lib.FakeTime(timestamp):
    with aff4.FACTORY.Create(
        client_id.Add(path),
        aff4_type=aff4_standard.VFSDirectory,
        mode="w",
        token=token) as _:
      pass

    if data_store.RelationalDBWriteEnabled():
      path_type, components = rdf_objects.ParseCategorizedPath(path)

      path_info = rdf_objects.PathInfo()
      path_info.path_type = path_type
      path_info.components = components
      path_info.directory = True

      data_store.REL_DB.WritePathInfos(client_id.Basename(), [path_info])


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
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

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


    # pylint: disable=unreachable
    os.environ.pop("http_proxy", None)
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")

    if flags.FLAGS.use_headless_chrome:
      options.add_argument("--headless")
      options.add_argument("--window-size=1400,1080")

    if flags.FLAGS.disable_chrome_sandboxing:
      options.add_argument("--no-sandbox")

    if flags.FLAGS.chrome_driver_path:
      GRRSeleniumTest.driver = webdriver.Chrome(
          flags.FLAGS.chrome_driver_path, chrome_options=options)
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

        GRRSeleniumTest._selenium_set_up_done = True

  def InstallACLChecks(self):
    """Installs AccessControlManager and stubs out SendEmail."""
    acrwac = api_call_router_with_approval_checks

    # Clear the cache of the approvals-based router.
    acrwac.ApiCallRouterWithApprovalChecks.ClearCache()

    if self.config_override:
      return

    name = acrwac.ApiCallRouterWithApprovalChecks.__name__
    self.config_override = test_lib.ConfigOverrider({"API.DefaultRouter": name})
    self.config_override.Start()
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def UninstallACLChecks(self):
    """Deinstall previously installed ACL checks."""
    if not self.config_override:
      return

    self.config_override.Stop()
    self.config_override = None

    # Make sure ApiAuthManager is initialized with update configuration
    # setting (i.e. without overrides).
    api_auth_manager.APIACLInit.InitApiAuthManager()

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
      self.fail(
          "Javascript error encountered during test: %s" % "\n\t".join(msgs))

  def DisableHttpErrorChecks(self):
    self.ignore_http_errors = True
    return DisabledHttpErrorChecksContextManager(self)

  def _CheckHttpErrors(self):
    if self.ignore_http_errors:
      return

    errors = self.driver.execute_script(
        "return (() => {const e = window.grrInterceptedHTTPErrors_ || []; "
        "window.grrInterceptedHTTPErrors_ = []; return e;})();")

    msgs = []
    for e in errors:
      msg = "[http]: %s" % e
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
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      self.CheckBrowserErrors()
      time.sleep(self.sleep_time)

    self.fail("condition not met, body is: %s" %
              self.driver.find_element_by_tag_name("body").text)

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
    self.WaitUntil(lambda: not condition_cb(*args))

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
      if text != self.GetValue(target):
        raise exceptions.WebDriverException("Send_keys did not work correctly.")

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
    element.click()

  @SeleniumAction
  def MoveMouseTo(self, target):
    self._WaitForAjaxCompleted()
    element = self.WaitUntil(self.GetVisibleElement, target)
    action_chains.ActionChains(self.driver).move_to_element(element).perform()

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
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    self.fail("condition %s(%s) not met (expected=%s, got_last_time=%s)" %
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
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    self.fail(
        "condition not met. got: %r, does not contain: %s" % (data, target))

  def setUp(self):
    super(GRRSeleniumTest, self).setUp()

    # Used by InstallACLChecks/UninstallACLChecks
    self.config_override = None
    # Used by CheckHttpErrors
    self.ignore_http_errors = False

    self.token.username = u"gui_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    # Make the user use the advanced gui so we can test it.
    if data_store.RelationalDBReadEnabled():
      data_store.REL_DB.WriteGRRUser(
          self.token.username, ui_mode=users.GUISettings.UIMode.ADVANCED)
    else:
      with aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users/%s" % self.token.username),
          aff4_type=users.GRRUser,
          mode="w",
          token=self.token) as user_fd:
        user_fd.Set(user_fd.Schema.GUI_SETTINGS(mode="ADVANCED"))

    self._artifact_patcher = ar_test_lib.PatchDatastoreOnlyArtifactRegistry()
    self._artifact_patcher.start()

    self.InstallACLChecks()

    if flags.FLAGS.use_headless_chrome:
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
    self._artifact_patcher.stop()
    self.CheckBrowserErrors()
    super(GRRSeleniumTest, self).tearDown()

  def WaitForNotification(self, username):
    sleep_time = 0.2
    iterations = 50
    for _ in range(iterations):
      try:
        if data_store.RelationalDBReadEnabled():
          pending_notifications = data_store.REL_DB.ReadUserNotifications(
              username, state=rdf_objects.UserNotification.State.STATE_PENDING)
          if pending_notifications:
            return
        else:
          urn = "aff4:/users/%s" % username
          fd = aff4.FACTORY.Open(urn, users.GRRUser, mode="r", token=self.token)
          pending_notifications = fd.Get(fd.Schema.PENDING_NOTIFICATIONS)
          if pending_notifications:
            return
      except IOError:
        pass
      time.sleep(sleep_time)
    self.fail("Notification for user %s never sent." % username)


class GRRSeleniumHuntTest(GRRSeleniumTest, hunt_test_lib.StandardHuntTestMixin):
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

    action_mock = action_mocks.FileFinderClientMock()
    hunt_test_lib.TestHuntHelper(action_mock, self.client_ids, False,
                                 self.token)

    return hunt

  def CheckState(self, state):
    self.WaitUntil(self.IsElementPresent, "css=div[state=\"%s\"]" % state)

  def CreateSampleHunt(self,
                       path=None,
                       stopped=False,
                       output_plugins=None,
                       client_limit=0,
                       client_count=10,
                       token=None):
    token = token or self.token
    self.client_ids = self.SetupClients(client_count)

    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path=path or "/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS,
            )),
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=output_plugins or [],
        client_rate=0,
        client_limit=client_limit,
        token=token) as hunt:
      if not stopped:
        hunt.Run()

    foreman_obj = foreman.GetForeman(token=token)
    for client_id in self.client_ids:
      foreman_obj.AssignTasksToClient(client_id.Basename())

    self.hunt_urn = hunt.urn
    return aff4.FACTORY.Open(
        hunt.urn, mode="rw", token=token, age=aff4.ALL_TIMES)

  def CreateGenericHuntWithCollection(self, values=None):
    self.client_ids = self.SetupClients(10)

    CreateFileVersion(self.client_ids[0], "fs/os/c/bin/bash", token=self.token)

    if values is None:
      values = [
          rdfvalue.RDFURN("aff4:/sample/1"),
          rdfvalue.RDFURN(
              "aff4:/%s/fs/os/c/bin/bash" % self.client_ids[0].Basename()),
          rdfvalue.RDFURN("aff4:/sample/3")
      ]

    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[],
        token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.Start()

      collection = hunt.ResultCollection()
      with data_store.DB.GetMutationPool() as pool:
        for value in values:
          collection.Add(
              rdf_flows.GrrMessage(payload=value, source=self.client_ids[0]),
              mutation_pool=pool)

      return hunt.urn


class SearchClientTestBase(GRRSeleniumTest):

  def CreateSampleHunt(self, description, token=None):
    return implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        description=description,
        token=token)


class RecursiveTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.RecursiveTestFlowArgs


@flow_base.DualDBFlow
class RecursiveTestFlowMixin(object):
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


@flow_base.DualDBFlow
class FlowWithOneLogStatementMixin(object):
  """Flow that logs a single statement."""

  def Start(self):
    self.Log("I do log.")


@flow_base.DualDBFlow
class FlowWithOneStatEntryResultMixin(object):
  """Test flow that calls SendReply once with a StatEntry value."""

  def Start(self):
    self.SendReply(
        rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path="/some/unique/path",
                pathtype=rdf_paths.PathSpec.PathType.OS)))


@flow_base.DualDBFlow
class FlowWithOneNetworkConnectionResultMixin(object):
  """Test flow that calls SendReply once with a NetworkConnection value."""

  def Start(self):
    self.SendReply(rdf_client_network.NetworkConnection(pid=42))


@flow_base.DualDBFlow
class FlowWithOneHashEntryResultMixin(object):
  """Test flow that calls SendReply once with a HashEntry value."""

  def Start(self):
    hash_result = rdf_crypto.Hash(
        sha256=("9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578"
                "e4f06017acdb5").decode("hex"),
        sha1="6dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        md5="8b0a15eefe63fd41f8dc9dee01c5cf9a".decode("hex"))
    self.SendReply(hash_result)


class DummyOutputPlugin(output_plugin.OutputPlugin):
  """Output plugin that does nothing."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, state, responses):
    pass
