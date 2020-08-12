import os
from werkzeug.wrappers import Request, Response
from werkzeug.wrappers.json import JSONMixin
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple


class JSONRequest(JSONMixin, Request):
  pass


class JSONResponse(JSONMixin, Response):
  pass


class Grrafana(object):

  def __init__(self, config):
    self.url_map = Map([
    Rule('/', endpoint='root', methods=["GET"]),
    Rule('/search', endpoint='search', methods=["POST"]),
    Rule('/query', endpoint='query', methods=["POST"]),
    Rule('/annotations', endpoint='annotations', methods=["POST"])
    ])

  def dispatch_request(self, request):
    adapter = self.url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return getattr(self, 'on_' + endpoint)(request, **values)
    except HTTPException as e:
      return e

  def wsgi_app(self, environ, start_response):
    request = JSONRequest(environ)
    response = self.dispatch_request(request)
    return response(environ, start_response)

  def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)

  def on_root(self, request):
    return JSONResponse()

  def on_search(self, request):
    pass

  def on_query(self, request):
    pass

  def on_annotations(self, request):
    pass


def create_app():
  app = Grrafana({})
  return app

if __name__ == '__main__':
  app = create_app()
  run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
