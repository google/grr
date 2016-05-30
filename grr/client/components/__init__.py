#!/usr/bin/env python
"""Components are optionally imported on the client."""
import os
import traceback

import logging
from grr.lib import config_lib
from grr.lib import registry

# Keep track on how we are imported in case we need to report the error.
IMPORT_TB = "".join(traceback.format_stack())


class ComponentInit(registry.InitHook):
  """This is a safety feature.

  We need to make sure that ensures that this component can not be imported into
  the virgin client. If this code ends up baked into the client, it will be
  impossible to update this component in the future.

  Therefore we make sure that we are not running in the client context - if we
  are this is a bug mostly likely caused by a stray import.
  """

  def RunOnce(self):
    if "Client Context" in config_lib.CONFIG.context:
      logging.exception(
          "Client component is included in client build! This is a bug!")
      logging.error(IMPORT_TB)
      os._exit(-1)  # pylint: disable=protected-access
