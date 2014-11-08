#!/usr/bin/env python
"""Tests for API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

import json

from grr.gui import api_renderers

from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


class SampleGetRenderer(api_renderers.ApiRenderer):

  method = "GET"
  route = "/test_sample/<path:path>"

  def Render(self, request):
    return {
        "method": "GET",
        "path": request.path,
        "foo": request.get("foo", "")
        }


class SamplePostRenderer(api_renderers.ApiRenderer):

  method = "POST"
  route = "/test_sample/<path:path>"

  def Render(self, request):
    return {
        "method": "POST",
        "path": request.path,
        "foo": request.get("foo", "")
    }


class ApiRenderersTest(test_lib.GRRBaseTest):
  """Test for generic API renderers logic."""

  def _CreateRequest(self, method, path, query_params=None):
    if not query_params:
      query_params = {}

    request = utils.DataObject()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {
        "SERVER_NAME": "foo.bar",
        "SERVER_PORT": 1234
        }
    request.user = "test"
    if method == "GET":
      request.GET = query_params
    else:
      request.POST = query_params
    request.META = {}

    return request

  def testReturnsRendererMatchingUrlAndMethod(self):
    renderer, _ = api_renderers.GetRendererForRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertTrue(isinstance(renderer, SampleGetRenderer))

    renderer, _ = api_renderers.GetRendererForRequest(
        self._CreateRequest("POST", "/test_sample/some/path"))
    self.assertTrue(isinstance(renderer, SamplePostRenderer))

  def testPathParamsAreReturnedWithMatchingRenderer(self):
    _, path_params = api_renderers.GetRendererForRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertEqual(path_params, {"path": "some/path"})

  def testRaisesIfNoRendererMatchesUrl(self):
    self.assertRaises(api_renderers.ApiRendererNotFoundError,
                      api_renderers.GetRendererForRequest,
                      self._CreateRequest("GET",
                                          "/some/missing/path"))

  def testRendersGetRendererCorrectly(self):
    response = api_renderers.RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": ""})
    self.assertEqual(response.status_code, 200)

  def testRendersPostRendererCorrectly(self):
    response = api_renderers.RenderResponse(
        self._CreateRequest("POST", "/test_sample/some/path"))
    self.assertEqual(
        json.loads(response.content),
        {"method": "POST",
         "path": "some/path",
         "foo": ""})
    self.assertEqual(response.status_code, 200)

  def testQueryParamsArePassedWithRequestObject(self):
    response = api_renderers.RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path",
                            query_params={"foo": "bar"}))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": "bar"})

  def testRouteArgumentTakesPrecedenceOverQueryParams(self):
    response = api_renderers.RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path",
                            query_params={"path": "foobar"}))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": ""})


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
