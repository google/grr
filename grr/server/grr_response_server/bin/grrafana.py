import os
import json
from werkzeug.wrappers import Request, Response
from werkzeug.wrappers.json import JSONMixin
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple
from google.protobuf.json_format import MessageToDict

from absl import app
from absl import flags

from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import server_startup
from grr_response_core import config
from grr_response_core.config import contexts


flags.DEFINE_bool(
  "version",
  default=False,
  allow_override=True,
  help="Print the GRR console version number and exit immediately.")


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
    if not request.json["type"]:
      # Grafana issued request on Variables > New/Edit page.
      response = json.dumps(MessageToDict(fetch_client_ids())["targets"])
    else:
      # Request issued on Panel > Queries page.
      response = fetch_available_metrics()
    return JSONResponse(response=response, mimetype="application/json")

  def on_query(self, request):
    from time import time
    from random import randint
    # print(request.json)
    response = dict()
    response["target"] = "hi"
    response["datapoints"] = [[randint(1, 10), (int(time()) - i) * 1000] for i in range(100)]
    response = [response]
    response = json.dumps(response)
    return JSONResponse(response=response, mimetype="application/json")

  def on_annotations(self, request):
    pass

def fetch_available_metrics():
  raw_data = fleetspeak_utils.GetAvailableMetricsFromFleetspeak()
  targets_list = MessageToDict(raw_data)["targets"]
  targets_list.remove('client_id')
  return json.dumps(targets_list)

def main(argv):
  del argv
  if flags.FLAGS.version:
    print("GRRafana server {}".format(config_server.VERSION["packageversion"]))
    return
  config.CONFIG.AddContext(contexts.GRRAFANA_CONTEXT, "Context applied when running GRRafana server.")
  server_startup.Init()
  fleetspeak_connector.Init()
  run_simple('127.0.0.1', 5000, Grrafana({}), use_debugger=True, use_reloader=True)


if __name__ == '__main__':
  app.run(main)