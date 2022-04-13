#!/usr/bin/env python
"""A tool that generates the OpenAPI description."""
import os

from absl import app
from absl import flags

from grr_response_server.gui import api_call_router
from grr_response_server.gui.api_plugins import metadata as metadata_plugin

flags.DEFINE_string("local_json_path", "",
                    "Path of file to save the generated JSON to.")


def main(argv):
  del argv  # Unused.

  router = api_call_router.ApiCallRouterStub()
  openapi_handler = metadata_plugin.ApiGetOpenApiDescriptionHandler(router)
  openapi_handler_result = openapi_handler.Handle(None)
  openapi_description = openapi_handler_result.openapi_description

  local_json_folder_path = os.path.dirname(flags.FLAGS.local_json_path)
  os.makedirs(local_json_folder_path, exist_ok=True)
  with open(file=flags.FLAGS.local_json_path, mode="w") as file:
    file.write(openapi_description)


if __name__ == "__main__":
  app.run(main)
