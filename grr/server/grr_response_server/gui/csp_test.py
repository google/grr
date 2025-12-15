#!/usr/bin/env python
from wsgiref import headers as wsgi

from absl import app
from absl.testing import parameterized

from grr_response_server.gui import csp
from grr.test_lib import test_lib


def StubApplication(unused_env, start_response):
  return start_response


test_policy = {
    "upgrade-insecure-requests": "",
    "default-src": ["'self'"],
    "base-uri": ["'none'"],
    "object-src": ["'none'"],
    "img-src": ["'self'", "https:", "data:"],
}


class CspTest(parameterized.TestCase, test_lib.GRRBaseTest):
  """Tests for Csp."""

  def testGetCspHeaderKey(self):
    enforced_result = csp.GetCspHeaderKey(False)
    report_only_result = csp.GetCspHeaderKey(True)
    self.assertEqual(csp.HEADER_KEY_ENFORCE, enforced_result)
    self.assertEqual(csp.HEADER_KEY_REPORT_ONLY, report_only_result)

  def testBuildPolicy(self):
    expected_directives = [
        "upgrade-insecure-requests",
        "default-src 'self'",
        "base-uri 'none'",
        "object-src 'none'",
        "img-src 'self' https: data:",
    ]

    result = csp.BuildPolicy(test_policy)
    result_directives = [x.strip() for x in result.split(";")]
    self.assertCountEqual(expected_directives, result_directives)

  @parameterized.named_parameters(
      dict(
          testcase_name="Disable CSP",
          csp_enabled=False,
          csp_report_only=False,
          tt_enabled=False,
          tt_report_only=False,
          expected_headers=[],
      ),
      dict(
          testcase_name=(
              "Enable enforced Trusted Types, with an existing CSP header"
          ),
          csp_enabled=False,
          csp_report_only=True,
          tt_enabled=True,
          tt_report_only=False,
          existing_headers=[(csp.HEADER_KEY_ENFORCE, "existing policy")],
          expected_headers=[
              (csp.HEADER_KEY_ENFORCE, "existing policy"),
              (csp.HEADER_KEY_ENFORCE, "require-trusted-types-for 'script'"),
          ],
      ),
      dict(
          testcase_name="Enable enforced CSP, with custom policy",
          csp_enabled=True,
          csp_policy='{"frame-ancestors": ["\'self\'"], "foo": ["bar"]}',
          csp_report_only=False,
          tt_enabled=False,
          expected_headers=[
              (csp.HEADER_KEY_ENFORCE, "frame-ancestors 'self'; foo bar")
          ],
      ),
      dict(
          testcase_name=(
              "Enable enforced CSP & trusted types, with custom policy"
          ),
          csp_enabled=True,
          csp_policy='{"frame-ancestors": ["\'self\'"], "foo": ["bar"]}',
          csp_report_only=False,
          tt_enabled=True,
          tt_report_only=False,
          expected_headers=[
              (csp.HEADER_KEY_ENFORCE, "frame-ancestors 'self'; foo bar"),
              (csp.HEADER_KEY_ENFORCE, "require-trusted-types-for 'script'"),
          ],
      ),
      dict(
          testcase_name=(
              "Enable report-only CSP, no trusted types, with report URL"
          ),
          csp_enabled=True,
          csp_report_only=True,
          tt_enabled=False,
          report_uri="test",
          expected_headers=[(csp.HEADER_KEY_REPORT_ONLY, "report-uri test")],
      ),
      dict(
          testcase_name="Enable report-only trusted types",
          csp_enabled=False,
          csp_report_only=False,
          tt_enabled=True,
          tt_report_only=True,
          expected_headers=[
              (csp.HEADER_KEY_REPORT_ONLY, "require-trusted-types-for 'script'")
          ],
      ),
      dict(
          testcase_name="Enable report-only trusted types with report URL",
          csp_enabled=False,
          csp_report_only=False,
          tt_enabled=True,
          tt_report_only=True,
          report_uri="test",
          expected_headers=[(
              csp.HEADER_KEY_REPORT_ONLY,
              "require-trusted-types-for 'script'; report-uri test",
          )],
      ),
      dict(
          testcase_name="Set headers for URLs in the include list",
          csp_enabled=True,
          csp_report_only=False,
          csp_policy='{"frame-ancestors": ["\'self\'"], "foo": ["bar"]}',
          tt_enabled=True,
          tt_report_only=True,
          url_path="/v2/page.html",
          include_prefixes=["/v2"],
          expected_headers=[
              (csp.HEADER_KEY_ENFORCE, "frame-ancestors 'self'; foo bar"),
              (
                  csp.HEADER_KEY_REPORT_ONLY,
                  "require-trusted-types-for 'script'",
              ),
          ],
      ),
      dict(
          testcase_name="Don't set headers for URLs not in the include list",
          csp_enabled=True,
          tt_enabled=True,
          url_path="/v1/page.html",
          include_prefixes=["/v2"],
          expected_headers=[],
      ),
      dict(
          testcase_name="Don't set headers for URLs in the exclude list",
          csp_enabled=True,
          tt_enabled=True,
          url_path="/v1/page.html",
          exclude_prefixes=["/v1"],
          expected_headers=[],
      ),
      dict(
          testcase_name="Handle specifying both an include and exclude list",
          csp_enabled=True,
          tt_enabled=True,
          url_path="/v2/not-this-one.html",
          include_prefixes=["/v2"],
          exclude_prefixes=["/v2/not-this-one.html"],
          expected_headers=[],
      ),
      dict(
          testcase_name="Handle duplicate headers as a list",
          csp_enabled=False,
          tt_enabled=True,
          existing_headers=[
              ("Set-Cookie", "foo=bar"),
              ("Set-Cookie", "bin=baz"),
          ],
          expected_headers=[
              ("Set-Cookie", "foo=bar"),
              ("Set-Cookie", "bin=baz"),
              (
                  csp.HEADER_KEY_REPORT_ONLY,
                  "require-trusted-types-for 'script'",
              ),
          ],
      ),
      dict(
          testcase_name="Handle duplicate headers as wsgi headers",
          csp_enabled=False,
          tt_enabled=True,
          existing_headers=wsgi.Headers(
              [("Set-Cookie", "foo=bar"), ("Set-Cookie", "bin=baz")]
          ),
          expected_headers=[
              ("Set-Cookie", "foo=bar"),
              ("Set-Cookie", "bin=baz"),
              (
                  csp.HEADER_KEY_REPORT_ONLY,
                  "require-trusted-types-for 'script'",
              ),
          ],
      ),
      dict(
          testcase_name="Handle headers as a dict",
          csp_enabled=False,
          tt_enabled=True,
          existing_headers={"Set-Cookie": "foo=bar"},
          expected_headers=[
              ("Set-Cookie", "foo=bar"),
              (
                  csp.HEADER_KEY_REPORT_ONLY,
                  "require-trusted-types-for 'script'",
              ),
          ],
      ),
      dict(
          testcase_name="Raise an exception if multiple report URIs are given",
          csp_enabled=True,
          tt_enabled=False,
          csp_policy='{"report-uri": ["test"], "foo": ["bar"]}',
          report_uri="test",
          expected_exception=RuntimeError,
      ),
  )
  def testCspMiddleware(
      self,
      csp_enabled=False,
      csp_policy="{}",
      csp_report_only=True,
      tt_enabled=False,
      tt_report_only=True,
      report_uri="",
      include_prefixes=(),
      exclude_prefixes=(),
      url_path="",
      existing_headers=(),
      expected_headers=(),
      expected_exception=None,
  ):
    """Test if CSP headers are correctly set."""
    expected_output = "Response successfully processed"
    environ_stub = {"PATH_INFO": url_path}

    def ApplicationStub(unused_environ, start_response):
      return start_response(200, existing_headers or [])

    def StartResponseMock(unused_status, headers, unused_exc_info=None):
      """This mock is called at the end of CspStartResponse."""
      self.assertEqual(headers, expected_headers)
      return expected_output

    with test_lib.ConfigOverrider({
        "AdminUI.csp_enabled": csp_enabled,
        "AdminUI.csp_policy": csp_policy,
        "AdminUI.csp_report_only": csp_report_only,
        "AdminUI.trusted_types_enabled": tt_enabled,
        "AdminUI.trusted_types_report_only": tt_report_only,
        "AdminUI.csp_report_uri": report_uri,
        "AdminUI.csp_include_url_prefixes": include_prefixes,
        "AdminUI.csp_exclude_url_prefixes": exclude_prefixes,
    }):
      if expected_exception:
        with self.assertRaises(expected_exception):
          csp.CspMiddleware(ApplicationStub)
      else:
        test_app = csp.CspMiddleware(ApplicationStub)
        output = test_app(environ_stub, StartResponseMock)

        self.assertEqual(expected_output, output)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
