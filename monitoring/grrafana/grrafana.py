import os
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple

class Grrafana(object):

  def __init__(self, config):
    pass

  def dispatch_request(self, request):
    return Response('Hello World!')

  def wsgi_app(self, environ, start_response):
    request = Request(environ)
    response = self.dispatch_request(request)
    return response(environ, start_response)

  def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)


def create_app():
  app = Grrafana({})
  return app

if __name__ == '__main__':
  app = create_app()
  run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
