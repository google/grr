#!/usr/bin/env python
"""Implement client side components.

Client components are managed, versioned modules which can be loaded at runtime.
"""
import importlib
import logging
import os
import StringIO
import sys
import zipfile

from grr.client import actions
from grr.lib import config_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto

LOADED_COMPONENTS = {}


class Site(object):
  """A copy of the relevant functions of the site Python package.

  PyInstaller removes site.py and replaces it with its own version for
  some reason so if we want to use site.addsitedir(), we need to
  provide it ourselves. This code is basically based on

  https://github.com/python-git/python/blob/715a6e5035bb21ac49382772076ec4c630d6e960/Lib/site.py
  """

  def MakePath(self, *paths):
    dir_ = os.path.abspath(os.path.join(*paths))
    return dir_, os.path.normcase(dir_)

  def InitPathinfo(self):
    """Return a set containing all existing directory entries from sys.path."""
    d = set()
    for dir_ in sys.path:
      try:
        if os.path.isdir(dir_):
          dir_, dircase = self.MakePath(dir_)
          d.add(dircase)
      except TypeError:
        continue
    return d

  def AddSiteDir(self, sitedir):
    """Add 'sitedir' argument to sys.path if missing."""

    known_paths = self.InitPathinfo()
    sitedir, sitedircase = self.MakePath(sitedir)

    if sitedircase not in known_paths and os.path.exists(sitedir):
      sys.path.append(sitedir)
    try:
      names = os.listdir(sitedir)
    except os.error:
      return
    dotpth = os.extsep + "pth"
    names = [name for name in names if name.endswith(dotpth)]
    for name in sorted(names):
      self.AddPackage(sitedir, name, known_paths)

  def AddPackage(self, sitedir, name, known_paths):
    """Process a .pth file within the site-packages directory."""

    if known_paths is None:
      self.InitPathinfo()

    fullname = os.path.join(sitedir, name)
    try:
      f = open(fullname, "rU")
    except IOError:
      return
    with f:
      for line in f:
        if line.startswith("#"):
          continue
        if line.startswith(("import ", "import\t")):
          exec line  # pylint: disable=exec-used
          continue
        line = line.rstrip()
        dir_, dircase = self.MakePath(sitedir, line)
        if dircase not in known_paths and os.path.exists(dir_):
          sys.path.append(dir_)
          known_paths.add(dircase)


class LoadComponent(actions.ActionPlugin):
  """Launches an external client action through a component."""
  in_rdfvalue = rdf_client.LoadComponent
  out_rdfvalues = [rdf_client.LoadComponent]

  def LoadComponent(self, summary):
    """Import all the required modules as specified in the request."""
    if (summary.name in LOADED_COMPONENTS and
        summary.version != LOADED_COMPONENTS[summary.name]):
      logging.error("Component %s is already loaded at version %s. Exiting!",
                    summary.name, LOADED_COMPONENTS[summary.name])
      os._exit(0)  # pylint: disable=protected-access

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
        config_lib.CONFIG.Get("Client.component_path"), summary.name,
        summary.version)

    # Add the component path to the site packages:
    site = Site()
    site.AddSiteDir(component_path)
    LOADED_COMPONENTS[summary.name] = summary.version

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
    http_result = self.grr_worker.http_manager.OpenServerEndpoint(url)
    if http_result.code != 200:
      raise RuntimeError("Error %d while downloading component %s." %
                         (http_result.code, url))
    crypted_data = http_result.data

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
    site.AddSiteDir(component_path)
    LOADED_COMPONENTS[component.summary.name] = component.summary.version

    # If this does not work now, we just fail.
    self.LoadComponent(summary)

    # If we succeed we just report this component is done.
    self.SendReply(request)
