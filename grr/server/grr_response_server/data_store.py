#!/usr/bin/env python
"""The main data store abstraction.

The data store is responsible for storing AFF4 objects permanently. This file
defines the basic interface of the data store, but there is no specific
implementation. Concrete implementations should extend the DataStore class and
provide non-abstract methods.

The data store is essentially an object store. Objects have a subject (a unique
identifying name) and a series of arbitrary attributes. Attributes also have a
name and can only store a number of well defined types.

Some data stores have internal capability to filter and search for objects based
on attribute conditions. Due to the variability of this capability in
implementations, the Filter() class is defined inside the DataStore class
itself. This allows callers to create a data store specific filter
implementation, with no prior knowledge of the concrete implementation.

In order to accommodate for the data store's basic filtering capabilities it is
important to allow the data store to store attribute values using the most
appropriate types.

The currently supported data store storage types are:
  - Integer
  - Bytes
  - String (unicode object).

This means that if one stores an attribute containing an integer, and then
retrieves this attribute, the data store guarantees that an integer is
returned (although it may be stored internally as something else).

More complex types should be encoded into bytes and stored in the data store as
bytes. The data store can then treat the type as an opaque type (and will not be
able to filter it directly).
"""

import logging
import sys
from typing import Optional

from absl import flags

from grr_response_core import config
from grr_response_server import blob_store
from grr_response_server.databases import db
from grr_response_server.databases import registry_init

flags.DEFINE_bool("list_storage", False, "List all storage subsystems present.")

# The global relational db handle.
REL_DB: Optional[db.Database] = None

# The global blobstore handle.
BLOBS: Optional[blob_store.BlobStore] = None


def _ListStorageOptions():
  for name, cls in registry_init.REGISTRY.items():
    print("%s\t\t%s" % (name, cls.__doc__))


def InitializeDataStore():
  """Initialize the data store.

  Depends on the stats module being initialized.
  """
  global REL_DB  # pylint: disable=global-statement
  global BLOBS  # pylint: disable=global-statement

  if flags.FLAGS.list_storage:
    _ListStorageOptions()
    sys.exit(0)

  # Initialize the relational DB.
  rel_db_name = config.CONFIG["Database.implementation"]
  if not rel_db_name:
    # TODO(hanuszczak): I think we should raise here instead of silently doing
    # nothing.
    return

  try:
    cls = registry_init.REGISTRY[rel_db_name]
  except KeyError:
    raise ValueError("Database %s not found." % rel_db_name)
  logging.info("Using database implementation %s", rel_db_name)
  REL_DB = db.DatabaseValidationWrapper(cls())

  # Initialize the blobstore. This has to be done after the database has been
  # already initialized as it might be possible that users want to use the data-
  # base-backed blobstore implementation.
  blobstore_name = config.CONFIG.Get("Blobstore.implementation")
  try:
    cls = blob_store.REGISTRY[blobstore_name]
  except KeyError:
    raise ValueError("No blob store %s found." % blobstore_name)
  BLOBS = blob_store.BlobStoreValidationWrapper(cls())
