#!/usr/bin/env python
"""Example Installer plugin.

This is an example plugin to illustrate how GRR installation can be customized.

In this example we want to also uninstall an old service called "old_service" as
part of the GRR installation. This could be because we decided to rename the GRR
service itself (by default GRR will update its own service name).

To include arbitrary plugins into the deployed client, you can repack the client
using the client_builder.py tool:

python grr/client/grr_response_client/client_build.py \
--config /etc/grr/grr-server.yaml --verbose \
--platform windows --arch amd64 deploy \
-p grr/client/plugins/installer_plugin.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_client import installer
import pywintypes
import win32serviceutil

import winerror


class StopOldService(installer.Installer):

  def RunOnce(self):
    """Stop and remove an old unneeded service during installation."""
    service_name = "My Old Service Name"

    try:
      win32serviceutil.StopService(service_name)
    except pywintypes.error as e:
      if e[0] not in [
          winerror.ERROR_SERVICE_NOT_ACTIVE,
          winerror.ERROR_SERVICE_DOES_NOT_EXIST
      ]:
        raise OSError("Could not stop service: {0}".format(e))

    try:
      win32serviceutil.RemoveService(service_name)
    except pywintypes.error as e:
      if e[0] != winerror.ERROR_SERVICE_DOES_NOT_EXIST:
        raise OSError("Could not remove service: {0}".format(e))
