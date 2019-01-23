#!/usr/bin/env python
"""One-off functions for migrating data from AFF4 to REL_DB."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from absl import app
from typing import Text

from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import server_startup


def _MigrateArtifact(artifact, overwrite):
  """Migrate one Artifact from AFF4 to REL_DB."""
  name = Text(artifact.name)

  try:
    logging.info("Migating %s", name)
    data_store.REL_DB.WriteArtifact(artifact)
    logging.info("  Wrote %s", name)
  except db.DuplicatedArtifactError:
    if overwrite:
      data_store.REL_DB.DeleteArtifact(name)
      data_store.REL_DB.WriteArtifact(artifact)
      logging.info("  Overwrote %s", name)
    else:
      logging.info("  Skipped %s, because artifact already exists.", name)


def MigrateArtifacts(overwrite=False):
  """Migrates Artifacts from AFF4 to REL_DB.

  Args:
    overwrite: If True, existing artifacts with identical names will be
      overwritten, otherwise skipped.
  """

  artifacts = artifact_registry.REGISTRY.GetArtifacts(
      reload_datastore_artifacts=True)
  logging.info("Migrating %s artifacts.", len(artifacts))

  for artifact in artifacts:
    _MigrateArtifact(artifact, overwrite)


def main(argv):
  del argv  # Unused.
  server_startup.Init()
  MigrateArtifacts()


if __name__ == "__main__":
  app.run(main)
