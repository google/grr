#!/usr/bin/env python
"""Implement client side components.

Client components are managed, versioned modules which can be loaded at runtime.
"""
import importlib
import logging
import os
import site
import StringIO
import zipfile

from grr.client import actions
from grr.lib import config_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto


class LoadComponent(actions.ActionPlugin):
  """Launches an external client action through a component."""
  in_rdfvalue = rdf_client.LoadComponent
  out_rdfvalue = rdf_client.LoadComponent

  def LoadComponent(self, summary):
    """Import all the required modules as specified in the request."""
    for mod_name in summary.modules:
      logging.debug("Will import %s", mod_name)
      importlib.import_module(mod_name)

  def Run(self, request):
    """Load the component requested.

    The component defines a set of python imports which should be imported into
    the running program. The purpose of this client action is to ensure that the
    imports are available and of the correct version. We ensure this by:

    1) Attempt to import the relevant modules.

    2) If that fails checks for the presence of a component installed at the
       require path. Attempt to import the modules again.

    3) If no component is installed, we fetch and install the component from the
       server. We then attempt to use it.

    If all imports succeed we return a success status, otherwise we raise an
    exception.

    Args:
      request: The LoadComponent request.

    Raises:
      RuntimeError: If the component is invalid.
    """
    summary = request.summary
    # Just try to load the required modules.
    try:
      self.LoadComponent(summary)
      # If we succeed we just report this component is done.
      self.SendReply(request)
      return
    except ImportError:
      pass

    # Try to add an existing component path.
    component_path = utils.JoinPath(
        config_lib.CONFIG.Get("Client.component_path"),
        summary.name, summary.version)

    # Add the component path to the site packages:
    site.addsitedir(component_path)

    try:
      self.LoadComponent(summary)
      logging.info("Component %s already present.", summary.name)
      self.SendReply(request)
      return

    except ImportError:
      pass

    # Could not import component - will have to fetch it.
    logging.info("Unable to import component %s.", summary.name)

    # Derive the name of the component that we need depending on the current
    # architecture. The client build system should have burned its environment
    # into the client config file. This is the best choice because it will
    # choose the same component that was built together with the client
    # itself (on the same build environment).
    build_environment = config_lib.CONFIG.Get("Client.build_environment")
    if not build_environment:
      # Failing this we try to get something similar to the running system.
      build_environment = rdf_client.Uname.FromCurrentSystem().signature()

    url = "%s/%s" % (summary.url, build_environment)
    logging.info("Fetching component from %s", url)
    crypted_data = self.grr_worker.http_manager.OpenServerEndpoint(url).data

    # Decrypt and check signature. The cipher is created when the component is
    # uploaded and contains the key to decrypt it.
    signed_blob = rdf_crypto.SignedBlob(summary.cipher.Decrypt(crypted_data))

    # Ensure the blob is signed with the correct key.
    signed_blob.Verify(config_lib.CONFIG[
        "Client.executable_signing_public_key"])

    component = rdf_client.ClientComponent(signed_blob.data)

    # Make sure its the component we actually want.
    if (component.summary.name != summary.name or
        component.summary.version != summary.version):
      raise RuntimeError("Downloaded component is not the correct version")

    # Make intermediate directories.
    try:
      os.makedirs(component_path)
    except (OSError, IOError):
      pass

    # Unzip the component into the path.
    logging.info("Installing component to %s", component_path)
    component_zip = zipfile.ZipFile(StringIO.StringIO(component.raw_data))
    component_zip.extractall(component_path)

    # Add the component to the site packages:
    site.addsitedir(component_path)

    # If this does not work now, we just fail.
    self.LoadComponent(summary)

    # If we succeed we just report this component is done.
    self.SendReply(request)
