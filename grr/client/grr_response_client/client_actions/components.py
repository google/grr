#!/usr/bin/env python
"""Implement client side components.

Client components are managed, versioned modules which can be loaded at runtime.
"""
import os
import sys

from grr_response_client import actions
from grr.lib.rdfvalues import client as rdf_client

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

  def Run(self, request):
    """Load the component requested.

    This method is just a stub left for compatibility with previous
    (compiled before July 2017) clients that used components architecture.

    Args:
      request: The LoadComponent request.

    Raises:
      RuntimeError: If the component is invalid.
    """
    self.SendReply(request)
