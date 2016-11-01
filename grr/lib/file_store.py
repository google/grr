#!/usr/bin/env python
"""A manager for storing files locally."""


import os

from grr.lib import config_lib
from grr.lib import registry
from grr.lib.rdfvalues import client


class UploadFileStore(object):
  """A class to manage writing to a file location."""

  __metaclass__ = registry.MetaclassRegistry

  def open_for_writing(self, client_id, path):
    """Facilitates writing to the specified path.

    Args:
      client_id: The client making this request.
      path: The path to write on.

    Returns:
      a file like object ready for writing.

    Raises:
      IOError: If the writing is rejected.
    """


class FileUploadFileStore(UploadFileStore):
  """An implementation of upload server based on files."""

  def open_for_writing(self, client_id, path):
    client_urn = client.ClientURN(client_id)

    root_dir = config_lib.CONFIG["FileUploadFileStore.root_dir"]
    path = os.path.join(root_dir,
                        client_urn.Add(path).Path().lstrip(os.path.sep))

    # Ensure the directory exists.
    try:
      os.makedirs(os.path.dirname(path))
    except (IOError, OSError):
      pass

    return open(path, "wb")
