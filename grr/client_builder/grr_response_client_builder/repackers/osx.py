#!/usr/bin/env python
"""MacOS client repackers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import zipfile


from grr_response_client_builder import build
from grr_response_client_builder import build_helpers

from grr_response_core.lib import utils


class DarwinClientRepacker(build.ClientRepacker):
  """Repackage OSX clients."""

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template."""

    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    client_config_data = build_helpers.GetClientConfig(context)
    shutil.copyfile(template_path, output_path)
    zip_file = zipfile.ZipFile(output_path, mode="a")
    zip_info = zipfile.ZipInfo(filename="config.yaml")
    zip_file.writestr(zip_info, client_config_data)
    zip_file.close()
    return output_path
